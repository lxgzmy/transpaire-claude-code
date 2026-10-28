r"""Regression for fill_hia.py against both staged HIA templates. Stdlib only.

    python regress_hia.py

Run after any fill_hia.py change, alongside regress_inclusions.py and
regress_prelim.py. Uses SYNTHETIC values only (no client data): for each
region it asserts that

  1. --check resolves every anchor on that region's staged template
     (a miss means the template or the anchor set changed - stop and look),
  2. a fill writes a docx whose document.xml still parses,
  3. every synthetic value actually appears in the filled text,
  4. every replaced prefill/placeholder is gone (the $25.00 LD figure, and
     the $000,000.00-style price placeholders when figures are supplied),
  4b. approved amendments (CD-10, issue #61): the interest rate changes and
     NSW Clause 14 is struck through from heading to the next clause (its
     contents line and Clause 15 untouched) when the request line carries
     its own approval and is in the request text; a wrong old value, a wrong
     title, no marker or a line the request does not carry is refused and
     the template wording stays,
  4a. NSW: the Progress Payments Schedule rows carry the stage amounts worked
     from the contract price, keyed DataBuild figures win and a difference is
     flagged; QLD (27 Oct 2026 review, reversing issue #73's "never worked
     out"): item 2 and every Schedule 2 Part B row are worked from the
     request price - the figures the executed 26059 contract's HIA form
     gave - figures a person gives are typed as given and the rest worked
     from their contract price, figures that disagree are still typed, each
     disagreement flagged, and with no price and no figures the placeholders
     stay, flagged,
  5. in both regions: each cell-mode value sits in the empty value cell
     beside its label (asserted row-by-row on the filled tables - the
     page-spill fix depends on values never landing in the narrow label
     cells), and the e-sign anchor strings survive the fill (QLD:
     /bs1/\builder_sig, /i1/\signer1_sig, four /na/ at source; NSW: the
     two witness /na/), and
  6. QLD (27 Oct 2026 review): item 11's STREET ADDRESS carries the job's
     estate in brackets after the street, and the owner's signature NAME is
     typed at a tab stop at the builder's prefilled name's x and size - an
     x read off the template's own column section, so a revised template
     fails here instead of misaligning the names.

Both staged templates are the team's own Word builds plus a sanctioned
interim repair each: NSW = the 21 Aug 2026 build + the v1.1 TABLES interim
(3 Sep 2026 - the build-contract review sheet's layout fixes: cover, item 3
owners, the land and the signature NAME lines take typed values without
wrap-crushing, and Special Conditions clause 1 cites Item 2); QLD = the
team's v2 (1 Sep 2026, issue #8) + the v2.1 LAND TABLES interim (3 Sep
2026). The staged templates live in runtime\ (this machine's checkout), so
the test SKIPS with a notice on a clone that has no staged templates - it
can only pass or fail where they exist.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGED = HERE.parents[2] / "runtime" / "contract-admin" / "outputs" / "_hia-word-templates"

SYNTH = {
    "NSW": {
        "template": STAGED / "NSW BUILD CONTRACT v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {
            "owners": "Testfirst TESTSURNAME & Second TESTOWNER",
            "job_no": "99991", "lot_no": "901",
            "site_hia": "(9) Sample Street, SAMPLEVILLE NSW 2999",
            "owner_1": "Testfirst TESTSURNAME", "owner_2": "Second TESTOWNER",
            "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "NSW", "owner_postcode": "2998",
            "owner_mobile": "0400 000 001", "owner_email": "regress@example.invalid",
            # review item 8: the second owner's contacts join the first "; "
            "owner_2_mobile": "0400 000 003",
            "owner_2_email": "second@example.invalid",
            "dp_no": "1234567", "land_street": "(9) Sample Street",
            "land_suburb": "SAMPLEVILLE", "land_postcode": "2999",
            "liq_damages": "$77.00", "builders_rep": "Regress REPNAME",
            "guarantor_name": "Guaran TESTGUARANTOR",
            "guarantor_address": "9 Guarantee Grove",
            "guarantor_suburb": "EXAMPLETON", "guarantor_state": "NSW",
            "guarantor_postcode": "2997",
            # keyed DataBuild figures win over the calculation (CD-5.4, #62)
            "price_excl_gst": "$636,363.64", "gst_amount": "$63,636.36",
            "price_incl_gst": "$700,000.00", "deposit": "$70,000.00",
        },
        # prefills/placeholders that must NOT survive the fill
        "gone": ["$25.00", "$000,000.00", "$00,00.00", "$00,000.00"],
        # the stage amounts worked from the keyed contract price
        "progress": [("10%", "$70,000.00"), ("10%", "$70,000.00"), ("25%", "$175,000.00"),
                     ("25%", "$175,000.00"), ("20%", "$140,000.00"), ("10%", "$70,000.00"),
                     ("100%", "$700,000.00")],
        "no_flags": ["FLAG:"],
        # v1.1's structural contract: cell-mode values land in the value
        # cell beside their label, never inside the narrow label cell (the
        # 28 Aug review's wrap-crush findings); the joined contact strings
        # pin the "; " convention for multi-owner mobiles/emails
        "cell_rows": [
            ["OWNERS:", "Testfirst TESTSURNAME & Second TESTOWNER"],
            ["JOB:", "99991"],
            ["LOT:", "901"],
            ["SITE:", "(9) Sample Street, SAMPLEVILLE NSW 2999"],
            ["", "NAME", "Testfirst TESTSURNAME & Second TESTOWNER"],
            ["", "ADDRESS", "9 Example Road"],
            ["", "SUBURB", "EXAMPLETON", "STATE", "NSW", "POSTCODE", "2998"],
            ["", "HOME", "MOBILE 0400 000 001; 0400 000 003"],
            ["", "EMAIL", "regress@example.invalid; second@example.invalid"],
            ["LOT", "901", "DP NO", "1234567"],
            ["CERTIFICATE OF TITLE"],
            ["STREET ADDRESS:", "(9) Sample Street"],
            # Attachment A acknowledgement boxes: name in the value cell
            # beside "Name (print):" (review items 15-16), box N = owner N
            ["Name (print):", "Testfirst TESTSURNAME"],
            ["Name (print):", "Second TESTOWNER"],
        ],
        # the two witness /na/ e-sign codes must survive the fill
        "anchors": {"/na/": 2},
    },
    "QLD": {
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {
            "owners": "Testfirst TESTSURNAME & Second TESTOWNER",
            "job_no": "99992", "lot_no": "902",
            # no site_hia: on QLD the cover SITE is built from the land keys below
            "owner_1": "Testfirst TESTSURNAME", "owner_2": "Second TESTOWNER",
            "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "QLD", "owner_postcode": "4998",
            "owner_mobile": "0400 000 002", "owner_email": "regress@example.invalid",
            "sp_rp": "SP999999", "land_street": "Sample Street", "estate": "Sample Estate",
            "land_suburb": "SAMPLEVILLE", "land_state": "QLD", "land_postcode": "4999",
            "liq_damages": "$88.00",
            "guarantor_name": "Guaran TESTGUARANTOR",
            "guarantor_address": "9 Guarantee Grove",
            "guarantor_suburb": "EXAMPLETON", "guarantor_state": "QLD",
            "guarantor_postcode": "4997",
            # figures a person gives, item 2 only here; Part B is worked
            # from their contract price. QC2 has no item 2 deposit
            "price_excl_gst": "$636,363.64", "gst_amount": "$63,636.36",
            "price_incl_gst": "$700,000.00",
        },
        "gone": ["$ 25.00", "$ 000,000.00", "$ 0.00"],
        "part_b": [("5.00%", "$35,000.00"), ("15.00%", "$105,000.00"), ("20.00%", "$140,000.00"),
                   ("25.00%", "$175,000.00"), ("20.00%", "$140,000.00"), ("15.00%", "$105,000.00"),
                   ("100.00%", "$700,000.00")],
        "no_flags": ["FLAG:"],
        # the owner's signature NAME at the builder's name's x and size
        "sig_name": "Testfirst TESTSURNAME & Second TESTOWNER",
        # the cover SITE on two lines, its label level with the first line
        "two_line_row": "SITE:",
        # v2's structural contract: each cell-mode value must land in the
        # value cell beside its label, never inside the label's narrow cell
        # (rows checked by membership in the filled document's tables)
        "cell_rows": [
            ["OWNERS:", "Testfirst TESTSURNAME & Second TESTOWNER"],
            ["JOB:", "99992"],
            ["LOT:", "902"],
            # the team's HIA form: the street and estate, then the place on the next line
            ["SITE:", "Sample Street, (Sample Estate) SAMPLEVILLE QLD 4999"],
            ["NAME", "Testfirst TESTSURNAME & Second TESTOWNER"],
            ["ADDRESS", "9 Example Road"],
            ["SUBURB", "EXAMPLETON", "STATE", "QLD", "POSTCODE", "4998"],
            ["FAX", "", "MOBILE", "0400 000 002"],
            ["EMAIL", "regress@example.invalid"],
            ["NAME", "Guaran TESTGUARANTOR"],
            ["ADDRESS", "9 Guarantee Grove"],
            ["SUBURB", "EXAMPLETON", "STATE", "QLD", "POSTCODE", "4997"],
            ["BUILDER IS", "TRANSPIRE CONSTRUCTIONS PTY LTD"],
            ["OWNER IS", "Testfirst TESTSURNAME & Second TESTOWNER"],
            # the land rows, tables since the v2.1 LAND TABLES interim
            # (3 Sep 2026 - the last narrow area, the residual spill's home)
            ["LOT", "902", "SP/RP", "SP999999"],
            # the estate after the street, as the team writes it (27-28 Oct 2026 review)
            ["STREET ADDRESS:", "Sample Street, (Sample Estate)"],
        ],
        # e-sign anchor codes are at source in v2 and must survive a fill
        # (counted on space-stripped text: Word may split a code across runs)
        "anchors": {"/bs1/\\builder_sig": 1, "/i1/\\signer1_sig": 1, "/na/": 4},
    },
    # issue #62: NSW item 2 and the schedule from the request price alone
    "NSW price only": {
        "region": "NSW",
        "template": STAGED / "NSW BUILD CONTRACT v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "456,789.00", "liq_damages": "77"},
        # as worked out; the liq damages keyed without its $ types with it
        "expect": ["$415,262.73", "$41,526.27", "$456,789.00", "$45,678.90", "$77.00"],
        "gone": ["$25.00", "$000,000.00", "$00,00.00", "$00,000.00"],
        "progress": [("10%", "$45,678.90"), ("10%", "$45,678.90"), ("25%", "$114,197.25"),
                     ("25%", "$114,197.25"), ("20%", "$91,357.80"), ("10%", "$45,678.90"),
                     ("100%", "$456,789.00")],
        "flags": ["contract figures (CD-5.4, issue #62): from the request price $456,789.00"],
        "no_flags": ["FLAG:"],
    },
    # a keyed DataBuild price that differs from the request price wins, flagged
    "NSW DataBuild differs": {
        "region": "NSW",
        "template": STAGED / "NSW BUILD CONTRACT v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "500,000.00", "price_incl_gst": "$510,000.00"},
        "expect": ["$510,000.00", "$46,363.64", "$463,636.36", "$51,000.00"],
        "gone": ["$000,000.00", "$00,00.00", "$00,000.00"],
        "progress": [("10%", "$51,000.00"), ("10%", "$51,000.00"), ("25%", "$127,500.00"),
                     ("25%", "$127,500.00"), ("20%", "$102,000.00"), ("10%", "$51,000.00"),
                     ("100%", "$510,000.00")],
        "flags": ["FLAG: the keyed DataBuild contract price $510,000.00 differs from the request "
                  "price $500,000.00 - the DataBuild figure is used"],
    },
    # issue #61: approved amendments - the interest rate and Clause 14 struck
    "NSW amendments": {
        "region": "NSW",
        "template": STAGED / "NSW BUILD CONTRACT v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "amendments": [
                       {"id": "A1", "kind": "schedule", "field": "interest_rate", "from": "15%", "to": "12%",
                        "request_line": "Item 4. Change late payment interest rate from 15% to 12% - Approved"},
                       {"id": "A2", "kind": "strike_clause", "clause": 14, "title": "Hidden Site Conditions",
                        "request_line": "Item 3. Delete Clause 14. Hidden Site Conditions \u2013 Approved by Test"}],
                   "amendments_for_person": ["Item 6. Add a special condition - a person writes it"]},
        "request": ("Item 3. Delete Clause 14. Hidden Site Conditions \u2013 Approved by Test\n"
                    "Item 4. Change late payment interest rate from 15% to 12% - Approved \n"),
        "expect": ["12%"], "gone": ["15%"],
        "struck": 14,
        "flags": ["AMENDMENT A1 APPLIED: interest_rate: 15% -> 12%",
                  "AMENDMENT A2 APPLIED: Clause 14 struck through",
                  "AMENDMENT WITH A PERSON: Item 6. Add a special condition"],
    },
    # each one refused: the wrong old rate, the wrong clause title, no marker,
    # and a marked line the request does not carry - the template stays
    "NSW amendments refused": {
        "region": "NSW",
        "template": STAGED / "NSW BUILD CONTRACT v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "amendments": [
                       {"id": "B1", "kind": "schedule", "field": "interest_rate", "from": "18%", "to": "12%",
                        "request_line": "Change late payment interest rate from 18% to 12% - Approved"},
                       {"id": "B2", "kind": "strike_clause", "clause": 14, "title": "Other Costs",
                        "request_line": "Delete Clause 14. Other Costs - Approved"},
                       {"id": "B3", "kind": "strike_clause", "clause": 15,
                        "request_line": "Delete Clause 15 please"},
                       {"id": "B4", "kind": "schedule", "field": "interest_rate", "from": "15%", "to": "10%",
                        "request_line": "Change interest to 10% - Approved by Test"}]},
        "request": ("Change late payment interest rate from 18% to 12% - Approved\n"
                    "Delete Clause 14. Other Costs - Approved\nDelete Clause 15 please\n"),
        "expect": ["15%"], "gone": ["12%"],
        "struck": None,
        "flags": ["AMENDMENT B1 REFUSED: the contract reads 15%; the request changes it from 18%",
                  "AMENDMENT B2 REFUSED: Clause 14 is",
                  "AMENDMENT B3 REFUSED: the request line carries no approval marker of its own",
                  "AMENDMENT B4 REFUSED: the request line is not in the request text word for word"],
    },
    # QLD: the interest rate changes; a clause strike is not set up there
    "QLD amendments": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "amendments": [
                       {"id": "Q1", "kind": "schedule", "field": "interest_rate", "from": "15%", "to": "12%",
                        "request_line": "Change the interest rate from 15% to 12% - Approved"},
                       {"id": "Q2", "kind": "strike_clause", "clause": 14,
                        "request_line": "Delete Clause 14 - Approved"}]},
        "request": "Change the interest rate from 15% to 12% - Approved\nDelete Clause 14 - Approved\n",
        "expect": ["12%"], "gone": ["15%"],
        "struck": None,
        "flags": ["AMENDMENT Q1 APPLIED: interest_rate: 15% -> 12%",
                  "AMENDMENT Q2 REFUSED: striking a clause is not set up for the QLD contract yet"],
    },
    # 27 Oct 2026 review: QLD item 2 and Part B from the request price alone,
    # the way the team's HIA form works them out (reverses issue #73's blank)
    "QLD price only": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "456,789.00"},
        "expect": ["$415,262.73", "$41,526.27", "$456,789.00"],
        "gone": ["$ 000,000.00", "$ 0.00"],
        "part_b": [("5.00%", "$22,839.45"), ("15.00%", "$68,518.35"), ("20.00%", "$91,357.80"),
                   ("25.00%", "$114,197.25"), ("20.00%", "$91,357.80"), ("15.00%", "$68,518.35"),
                   ("100.00%", "$456,789.00")],
        "flags": ["contract figures (QLD, CD-5.4): from the request price $456,789.00"],
        "no_flags": ["FLAG:"],
    },
    # no price and no figures: item 2 and Part B keep their placeholders, flagged
    "QLD no price": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME"},
        "expect": [],
        "gone": [],
        "kept": ["$ 000,000.00", "$ 0.00"],
        "flags": ["FLAG: no contract price in the job JSON - item 2 and Part B are left blank for a person"],
    },
    # issue #73: the figures a person gives (here as read off a DataBuild
    # screenshot) fill item 2 and every Part B row; the TOTAL is the contract
    # price given; consistent figures raise no flag
    "QLD figures given": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "456,789.00", "figures_source": "DataBuild screenshot, read back",
                   "price_excl_gst": "415,262.73", "gst_amount": "41,526.27",
                   "price_incl_gst": "$456,789.00", "deposit": "22,839.45",
                   "progress_1": "68,518.35", "progress_2": "91,357.80", "progress_3": "114,197.25",
                   "progress_4": "91,357.80", "progress_5": "68,518.35"},
        "expect": ["$415,262.73", "$41,526.27", "$456,789.00"],
        "gone": ["$ 000,000.00", "$ 0.00"],
        "part_b": [("5.00%", "$22,839.45"), ("15.00%", "$68,518.35"), ("20.00%", "$91,357.80"),
                   ("25.00%", "$114,197.25"), ("20.00%", "$91,357.80"), ("15.00%", "$68,518.35"),
                   ("100.00%", "$456,789.00")],
        "flags": ["contract figures (QLD): given (DataBuild screenshot, read back), typed as given: "
                  "excl. GST, GST, contract price, DEPOSIT, BASE, FRAME, ENCLOSED, FIXING, "
                  "PRACTICAL COMPLETION"],
        "no_flags": ["FLAG:"],
    },
    # issue #73: figures that disagree are still typed as given - every check
    # is a warning, never a stop and never a correction. The row not given
    # (PRACTICAL COMPLETION) is worked from the contract price given
    "QLD figures off": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "456,789.00",
                   "price_excl_gst": "415,262.73", "gst_amount": "41,000.00",
                   "price_incl_gst": "460,000.00", "deposit": "46,000.00",
                   "progress_1": "69,000.00", "progress_2": "92,000.00",
                   "progress_3": "115,000.00", "progress_4": "92,000.00"},
        "expect": ["$41,000.00", "$460,000.00"],
        "gone": [],
        "part_b": [("5.00%", "$46,000.00"), ("15.00%", "$69,000.00"), ("20.00%", "$92,000.00"),
                   ("25.00%", "$115,000.00"), ("20.00%", "$92,000.00"), ("15.00%", "$69,000.00"),
                   ("100.00%", "$460,000.00")],
        "flags": ["FLAG: item 2 does not add up",
                  "FLAG: the GST $41,000.00 is not 1/11 of the contract price ($41,818.18)",
                  "FLAG: the contract price given, $460,000.00, differs from the request price $456,789.00",
                  "FLAG: Part B's rows add up to $483,000.00, not the TOTAL $460,000.00",
                  "FLAG: the deposit $46,000.00 is over 5% of the contract price ($23,000.00)"],
        "no_flags": ["DEPOSIT $46,000.00 is not 5%", "part-filled"],
    },
}


def docx_text(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    ET.fromstring(xml)  # assertion 2: the XML still parses
    return re.sub(" +", " ", " ".join(
        html.unescape(m.group(1))
        for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)))


def table_rows(path):
    """Every table row as its list of cell texts (whitespace-normalised) -
    the structural view that shows whether a cell-mode value landed in the
    value cell beside its label or wrap-crushed the label's own cell."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    rows = []
    for tr in re.finditer(r"<w:tr\b.*?</w:tr>", xml, re.S):
        rows.append([
            re.sub(r"\s+", " ", "".join(
                " " if m.group(0) == "<w:br/>" else html.unescape(m.group(1)) for m in re.finditer(
                    r"<w:t(?: [^>]*)?>(.*?)</w:t>|<w:br/>", tc.group(0), re.S))).strip()
            for tc in re.finditer(r"<w:tc\b.*?</w:tc>", tr.group(0), re.S)])
    return rows


def run(name, spec, tmp):
    template, values = spec["template"], spec["values"]
    region = spec.get("region", name)
    if not template.exists():
        print(f"  {name}: SKIP - no staged template at {template}")
        return None
    slug = re.sub(r"\W+", "_", name)
    job = Path(tmp) / f"job_{slug}.json"
    job.write_text(json.dumps(values), encoding="utf-8")
    # the request text the run saves beside the job JSON (amendment checks)
    email = Path(tmp) / "email_original.txt"
    email.unlink(missing_ok=True)
    if "request" in spec:
        email.write_text(spec["request"], encoding="utf-8")
    out = Path(tmp) / f"filled_{slug}.docx"

    check = subprocess.run([sys.executable, str(HERE / "fill_hia.py"), "--template",
                            str(template), "--job", str(job), "--check",
                            "--region", region],
                           capture_output=True, text=True, encoding="utf-8")
    if check.returncode != 0 or "ANCHOR MISSING" in check.stdout:
        print(f"  {region}: FAIL - anchor check\n{check.stdout}{check.stderr}")
        return False

    fill = subprocess.run([sys.executable, str(HERE / "fill_hia.py"), "--template",
                           str(template), "--job", str(job), "--out", str(out),
                           "--region", region],
                          capture_output=True, text=True, encoding="utf-8")
    if fill.returncode != 0 or not out.exists():
        print(f"  {region}: FAIL - fill\n{fill.stdout}{fill.stderr}")
        return False

    text = docx_text(out)
    # each value as typed, or the case's own list of strings the fill must
    # produce (an amount types as "$nnn,nnn.nn"; the bare request price is
    # not itself printed in the build contract)
    expect = spec.get("expect", [v for k, v in values.items() if v and k != "price"])
    missing = [v for v in expect if re.sub(" +", " ", v) not in text]
    if missing:
        print(f"  {region}: FAIL - value(s) not in the filled text: {missing}")
        return False
    survived = [g for g in spec["gone"] if g in text]
    if survived:
        print(f"  {region}: FAIL - prefill(s)/placeholder(s) survived a fill that "
              f"should have replaced them: {survived}")
        return False
    lost = [k for k in spec.get("kept", []) if k not in text]
    if lost:
        print(f"  {name}: FAIL - placeholder(s) that must stay were filled: {lost}")
        return False
    if "progress" in spec:
        rows = [(r[2], r[3]) for r in table_rows(out)
                if len(r) == 4 and re.fullmatch(r"\d+%", r[2])]
        if rows != spec["progress"]:
            print(f"  {name}: FAIL - progress schedule rows {rows}, expected {spec['progress']}")
            return False
    if "part_b" in spec:
        rows = [(r[1], r[2]) for r in table_rows(out)
                if len(r) == 3 and re.fullmatch(r"\d+\.\d{2}%", r[1])]
        if rows != spec["part_b"]:
            print(f"  {name}: FAIL - Part B rows {rows}, expected {spec['part_b']}")
            return False
    if "struck" in spec:
        why = struck_check(out, spec["struck"])
        if why:
            print(f"  {name}: FAIL - {why}")
            return False
    report = check.stdout + fill.stdout
    no_flag = [f for f in spec.get("flags", []) if f not in report]
    bad_flag = [f for f in spec.get("no_flags", []) if f in report]
    if no_flag or bad_flag:
        print(f"  {name}: FAIL - report lines missing {no_flag} / unexpected {bad_flag}\n{fill.stdout}")
        return False
    want_rows = spec.get("cell_rows", [])
    if want_rows:
        got_rows = table_rows(out)
        miss = [r for r in want_rows if r not in got_rows]
        if miss:
            print(f"  {region}: FAIL - cell-mode value(s) not in the value cell "
                  f"beside their label: {miss}")
            return False
    flat = text.replace(" ", "")
    bad = {a: flat.count(a) for a, n in spec.get("anchors", {}).items()
           if flat.count(a) != n}
    if bad:
        print(f"  {region}: FAIL - e-sign anchor count wrong after fill "
              f"(anchor: found): {bad}")
        return False
    if "sig_name" in spec:
        why = sig_name_check(out, spec["sig_name"])
        if why:
            print(f"  {name}: FAIL - signature NAME: {why}")
            return False
    if "two_line_row" in spec:
        xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
        k = xml.find(f">{spec['two_line_row']}<")
        row = xml[xml.rfind("<w:tr ", 0, k):xml.find("</w:tr>", k)] if k >= 0 else ""
        if "<w:br/>" not in row or row.count('<w:vAlign w:val="top"/>') != 2 or 'w:vAlign w:val="center"' in row:
            print(f"  {name}: FAIL - the {spec['two_line_row']} row is not two lines with both cells top-aligned")
            return False
    extra = (f", {len(want_rows)} cell rows + {len(spec.get('anchors', {}))} "
             f"anchor codes verified" if want_rows else "")
    print(f"  {name}: PASS ({len(expect)} values filled, XML valid, "
          f"{len(spec['gone'])} prefill(s) replaced{extra}"
          + (", progress schedule verified" if "progress" in spec else "")
          + (", Part B verified" if "part_b" in spec else "")
          + (", owner NAME lined up with the builder's" if "sig_name" in spec else "") + ")")
    return True


def sig_tab_mode():
    """fill_hia's QLD owner signature NAME mode: ("tab_at", x in twips, size);
    (None, None, None) when it has none."""
    sys.path.insert(0, str(HERE))
    import fill_hia
    return next((f[2] for _, fields in fill_hia.REGIONS["QLD"]["groups"] for f in fields
                 if isinstance(f[2], tuple) and f[2][0] == "tab_at"), (None, None, None))


def sig_name_check(path, name):
    """"" when the owner's name is a tab-led run at fill_hia's QLD tab stop and
    size, on the one paragraph that carries that tab stop."""
    _, pos, size = sig_tab_mode()
    if pos is None:
        return "fill_hia types the owner's name with no tab stop of its own"
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    stop = f'<w:tab w:val="left" w:pos="{pos}"/>'
    paras = [p for p in re.findall(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", xml, re.S) if stop in p]
    if len(paras) != 1:
        return f"{len(paras)} paragraph(s) carry the {pos} tw tab stop - expected the owner NAME line alone"
    run = re.search(r"<w:r><w:rPr>(.*?)</w:rPr><w:tab/><w:t[^>]*>(.*?)</w:t></w:r>", paras[0], re.S)
    if not run or html.unescape(run.group(2)) != name or f'<w:sz w:val="{size}"/>' not in run.group(1):
        return f"the owner's name is not a tab-led {size / 2:g} pt run on that line"
    return ""


def builder_name_geometry():
    """The QLD build's builder NAME (prefilled Michael CRONK) sits in a
    two-column section after a column break: its x from the margin is the
    first column's width + the gap + the name paragraph's own indent, at its
    style's size. fill_hia's owner NAME tab stop and size must be exactly
    those, or the two names stop lining up (27 Oct 2026 review)."""
    template = SYNTH["QLD"]["template"]
    if not template.exists():
        print(f"  QLD builder NAME geometry: SKIP - no staged template at {template}")
        return None
    z = zipfile.ZipFile(template)
    xml = z.read("word/document.xml").decode("utf-8")
    k = xml.find("<w:t>Michael</w:t>")
    p = xml[xml.rfind("<w:p ", 0, k):xml.find("</w:p>", k)] if k >= 0 else ""
    style = re.search(r'<w:pStyle w:val="(\w+)"/>', p)
    ind = re.search(r'<w:ind w:left="(\d+)"/>', p)
    cols = re.search(r'<w:cols w:num="2"[^>]*><w:col w:w="(\d+)" w:space="(\d+)"/>', xml[k:]) if k >= 0 else None
    st = z.read("word/styles.xml").decode("utf-8")
    sdef = style and re.search(rf'<w:style [^>]*w:styleId="{style.group(1)}".*?</w:style>', st, re.S)
    size = sdef and re.search(r'<w:sz w:val="(\d+)"/>', sdef.group(0))
    if not (p and '<w:br w:type="column"/>' in p and ind and cols and size):
        print("  QLD builder NAME geometry: FAIL - the builder's name is no longer a column-break "
              "paragraph with its own indent and style size in a two-column section")
        return False
    x = int(cols.group(1)) + int(cols.group(2)) + int(ind.group(1))
    _, pos, want = sig_tab_mode()
    ok = (x, int(size.group(1))) == (pos, want)
    print(f"  QLD builder NAME geometry: " + (f"PASS ({x} tw from the margin, {want / 2:g} pt)" if ok else
          f"FAIL - the builder's name sits at {x} tw, {int(size.group(1)) / 2:g} pt; fill_hia types the "
          f"owner's at {pos} tw, size {want}"))
    return ok


def struck_check(path, n):
    """"" when Clause n is struck from its heading to the next clause heading
    and nothing else in the document is (n None: nothing struck at all)."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    paras = [(m.start(), m.group(0)) for m in re.finditer(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", xml, re.S)]
    heads = [s for s, p in paras if '<w:pStyle w:val="Heading1"/>' in p]
    if n is None:
        return "" if "<w:strike" not in xml else "a strike-through where no amendment applied"
    def text(p):
        return "".join(re.findall(r"<w:t(?: [^>]*)?>(.*?)</w:t>", p, re.S))
    start = next((s for s, p in paras if s in heads and re.match(rf"\s*Clause\s+{n}\.", text(p))), None)
    if start is None:
        return f"Clause {n} heading not found"
    end = min(h for h in heads if h > start)
    printing = [r for r in re.findall(r"<w:r\b[^>]*>.*?</w:r>", xml[start:end], re.S) if re.search(r"<w:t[ >]", r)]
    if not printing or not all("<w:strike/>" in r for r in printing):
        return f"Clause {n}: {sum('<w:strike/>' not in r for r in printing)} printing run(s) not struck"
    outside = xml[:start].count("<w:strike") + xml[end:].count("<w:strike")
    if outside:
        return f"{outside} strike-through(s) outside Clause {n} (contents line or Clause {n + 1} touched)"
    return ""


def legacy_key_split():
    """Older NSW job JSONs carry 'SUBURB POSTCODE' as one land_suburb_pc value;
    the filler must split it for the team-build template's separate labels."""
    sys.path.insert(0, str(HERE))
    import fill_hia
    d = fill_hia.derive_values(
        {"land_suburb_pc": "SAMPLEVILLE 2999", "owners": "A", "owner_1": "A"}, "NSW")
    ok = d.get("land_suburb") == "SAMPLEVILLE" and d.get("land_postcode") == "2999"
    print(f"  legacy land_suburb_pc split: {'PASS' if ok else 'FAIL - ' + repr(d)}")
    return ok


def contract_figures_unit():
    """Issue #62 arithmetic without a template: the rounding balance, the
    deposit cap, a lower requested deposit, an unusable price, QLD untouched."""
    sys.path.insert(0, str(HERE))
    import fill_hia
    fails = []

    def figs(values, region="NSW"):
        lines, flags = fill_hia.contract_figures(values, region)
        return values, lines, flags

    v, _, f = figs({"price": "456,789.15"})
    stages = [v[f"progress_{n}"] for n in range(1, 7)]
    if (v["gst_amount"], v["price_excl_gst"], v["deposit"]) != ("$41,526.29", "$415,262.86", "$45,678.91"):
        fails.append(f"odd-cent price item 2: {v['gst_amount']} {v['price_excl_gst']} {v['deposit']}")
    if stages != ["$45,678.91", "$45,678.92", "$114,197.29", "$114,197.29", "$91,357.83", "$45,678.91"]:
        fails.append(f"odd-cent price stages: {stages}")
    if sum(fill_hia.parse_money(s) for s in stages) != fill_hia.parse_money("456,789.15") or f:
        fails.append(f"odd-cent price: stages do not total the price, or flags {f}")
    v, _, f = figs({"price": "514,700.00", "deposit_request": "5%"})
    if v["deposit"] != "$25,735.00" or v["progress_1"] != "$51,470.00" or not any("below 10%" in x for x in f):
        fails.append(f"lower deposit: {v['deposit']} / stage 1 {v['progress_1']} / {f}")
    v, _, f = figs({"price": "514,700.00", "deposit_request": "$60,000"})
    if v["deposit"] != "$51,470.00" or not any("over the 10% cap" in x for x in f):
        fails.append(f"deposit over the cap: {v['deposit']} / {f}")
    v, lines, f = figs({"price": "TBC"})
    if lines or v.get("deposit") or not any("left blank for a person" in x for x in f):
        fails.append(f"unusable price: {lines} {v} {f}")
    # QLD (27 Oct 2026 review): worked from the request price - these are
    # the figures the HIA form gave on the executed 26059 contract
    qld = ("price_excl_gst", "gst_amount", "price_incl_gst", "deposit", "progress_1", "progress_2",
           "progress_3", "progress_4", "progress_5", "progress_total")
    v, lines, f = figs({"price": "467,200.00", "liq_damages": "100.00"}, "QLD")
    if [v.get(k) for k in qld] != ["$424,727.27", "$42,472.73", "$467,200.00", "$23,360.00", "$70,080.00",
                                   "$93,440.00", "$116,800.00", "$93,440.00", "$70,080.00", "$467,200.00"] \
            or f or v["liq_damages"] != "$100.00":
        fails.append(f"QLD from the request price: {[v.get(k) for k in qld]} {f}")
    # an odd-cent price: the deposit rounds down (never over 5%), practical
    # completion takes the balance, so Part B totals the price to the cent
    v, lines, f = figs({"price": "456,789.15"}, "QLD")
    rows = [fill_hia.parse_money(v.get(k)) for k in qld[3:9]]
    if v.get("deposit") != "$22,839.45" or v.get("progress_5") != "$68,518.38" or None in rows \
            or sum(rows) != fill_hia.parse_money("456,789.15") or f:
        fails.append(f"QLD odd-cent price: {[v.get(k) for k in qld]} {f}")
    # no price and no figures: nothing typed, flagged
    v, lines, f = figs({"price": "TBC"}, "QLD")
    if lines or "gst_amount" in v or not any("left blank for a person" in x for x in f):
        fails.append(f"QLD unusable price: {lines} {v} {f}")
    # figures given are typed as given and the rest are worked from their
    # contract price; consistent figures raise no flag
    v, lines, f = figs({"price_incl_gst": "300,000.00", "gst_amount": "27,272.73",
                        "deposit": "15,000", "progress_1": "45,000.00"}, "QLD")
    if (v.get("price_excl_gst"), v.get("progress_2"), v.get("progress_5"), v.get("progress_total")) \
            != ("$272,727.27", "$60,000.00", "$45,000.00", "$300,000.00") or f \
            or not any("typed as given: GST, contract price, DEPOSIT, BASE" in x for x in lines):
        fails.append(f"QLD part-given: {v} {f}")
    # a price under $20,000 is not held to the 5% deposit
    v, lines, f = figs({"price_incl_gst": "11,000.00", "deposit": "1,100.00"}, "QLD")
    if any("over 5%" in x for x in f) or not any("DEPOSIT $1,100.00 is not 5%" in x for x in f):
        fails.append(f"QLD small price: {f}")
    # the estate goes in brackets after the street on QLD item 11, once
    # "Street, (Estate)" whether the JSON gives the street bare, with the estate
    # already bracketed (with or without the comma) or mentioning it otherwise;
    # NSW untouched. The QLD cover SITE: that street, then the place below it.
    land = {"land_suburb": "SAMPLEVILLE", "land_state": "QLD", "land_postcode": "4999"}
    streets = [fill_hia.derive_values({"land_street": s, "estate": "Sample Estate", **land}, "QLD")["land_street"]
               for s in ("Sample Street", "Sample Street (Sample Estate)", "Sample Street, (sample estate)",
                         "Sample Street, Sample Estate")]
    nsw = fill_hia.derive_values({"land_street": "Sample Street", "estate": "Sample Estate",
                                  "site_hia": "Sample Street, SAMPLEVILLE", **land}, "NSW")
    cover = fill_hia.derive_values({"land_street": "Sample Street", "estate": "Sample Estate",
                                    "site_hia": "anything", **land}, "QLD")["site_hia"]
    if streets != ["Sample Street, (Sample Estate)"] * 3 + ["Sample Street, Sample Estate"] \
            or (nsw["land_street"], nsw["site_hia"]) != ("Sample Street", "Sample Street, SAMPLEVILLE") \
            or cover != "Sample Street, (Sample Estate)\nSAMPLEVILLE QLD 4999":
        fails.append(f"QLD estate/cover: {streets} / NSW {nsw['land_street']!r} {nsw['site_hia']!r} / {cover!r}")
    print("  contract figures (#62): " + ("PASS" if not fails else "FAIL - " + "; ".join(fails)))
    return not fails


def main():
    print("regress_hia: fill_hia.py vs the staged HIA templates (synthetic values)")
    results = [legacy_key_split(), contract_figures_unit(), builder_name_geometry()]
    with tempfile.TemporaryDirectory(dir=STAGED.parent if STAGED.parent.is_dir() else None) as tmp:
        for region, spec in SYNTH.items():
            results.append(run(region, spec, tmp))
    if any(r is False for r in results):
        return 1
    if all(r is None for r in results):
        print("  every region skipped - no staged templates on this checkout")
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
