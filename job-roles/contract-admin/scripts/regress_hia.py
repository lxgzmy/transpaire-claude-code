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
     flagged; QLD keeps its placeholders when only a price is given (issue
     #62 - NSW first), and
  5. in both regions: each cell-mode value sits in the empty value cell
     beside its label (asserted row-by-row on the filled tables - the
     page-spill fix depends on values never landing in the narrow label
     cells), and the e-sign anchor strings survive the fill (QLD:
     /bs1/\builder_sig, /i1/\signer1_sig, four /na/ at source; NSW: the
     two witness /na/).

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
            "site_hia": "Sample Street, SAMPLEVILLE QLD 4999",
            "owner_1": "Testfirst TESTSURNAME", "owner_2": "Second TESTOWNER",
            "owner_address": "9 Example Road",
            "owner_suburb": "EXAMPLETON", "owner_state": "QLD", "owner_postcode": "4998",
            "owner_mobile": "0400 000 002", "owner_email": "regress@example.invalid",
            "sp_rp": "SP999999", "land_street": "Sample Street",
            "land_suburb": "SAMPLEVILLE", "land_state": "QLD", "land_postcode": "4999",
            "liq_damages": "$88.00",
            "guarantor_name": "Guaran TESTGUARANTOR",
            "guarantor_address": "9 Guarantee Grove",
            "guarantor_suburb": "EXAMPLETON", "guarantor_state": "QLD",
            "guarantor_postcode": "4997",
            # CD-5.4: figures only ever arrive pre-keyed from DataBuild; QC2
            # has no schedule deposit item, so no deposit key here
            "price_excl_gst": "$636,363.64", "gst_amount": "$63,636.36",
            "price_incl_gst": "$700,000.00",
        },
        "gone": ["$ 25.00", "$ 000,000.00"],
        # v2's structural contract: each cell-mode value must land in the
        # value cell beside its label, never inside the label's narrow cell
        # (rows checked by membership in the filled document's tables)
        "cell_rows": [
            ["OWNERS:", "Testfirst TESTSURNAME & Second TESTOWNER"],
            ["JOB:", "99992"],
            ["LOT:", "902"],
            ["SITE:", "Sample Street, SAMPLEVILLE QLD 4999"],
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
            ["STREET ADDRESS:", "Sample Street"],
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
    # QLD is not calculated yet (NSW first): a price alone leaves item 2 blank
    "QLD price only": {
        "region": "QLD",
        "template": STAGED / "QLD BUILD CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        "values": {"owners": "Testfirst TESTSURNAME", "owner_1": "Testfirst TESTSURNAME",
                   "price": "456,789.00"},
        "expect": [],
        "gone": [],
        "kept": ["$ 000,000.00"],
        "no_flags": ["contract figures"],
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
                html.unescape(m.group(1)) for m in re.finditer(
                    r"<w:t(?: [^>]*)?>(.*?)</w:t>", tc.group(0), re.S))).strip()
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
    extra = (f", {len(want_rows)} cell rows + {len(spec.get('anchors', {}))} "
             f"anchor codes verified" if want_rows else "")
    print(f"  {name}: PASS ({len(expect)} values filled, XML valid, "
          f"{len(spec['gone'])} prefill(s) replaced{extra}"
          + (", progress schedule verified" if "progress" in spec else "") + ")")
    return True


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
    v, lines, f = figs({"price": "514,700.00", "liq_damages": "100.00"}, "QLD")
    if lines or f or "gst_amount" in v or v["liq_damages"] != "$100.00":
        fails.append(f"QLD: {lines} {f} {v}")
    print("  contract figures (#62): " + ("PASS" if not fails else "FAIL - " + "; ".join(fails)))
    return not fails


def main():
    print("regress_hia: fill_hia.py vs the staged HIA templates (synthetic values)")
    results = [legacy_key_split(), contract_figures_unit()]
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
