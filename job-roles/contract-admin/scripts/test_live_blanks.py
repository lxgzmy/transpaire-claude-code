"""Every live inclusions blank on the drive fills completely, with its boxes and signature lines right.

    python test_live_blanks.py

Lists the blanks from the live template folders, so a blank added or revised on
the drive is checked by the next run, fills each with a synthetic one-owner and
two-owner job, and fails on:

  - a field the filler finds no anchor for (blank 8's "Lot No.:" labels went
    unfilled until 31 Oct 2026)
  - an owners box not holding the owners, or an address outside its box
    (gate_inclusions.check_site_box - SEQ blank 1 and Owner Occupier, #100)
  - a signature line whose Date: misses its stop (check_signature_lines)
  - a blank other than 7 taken for the storey lists

and on the two blanks with shapes of their own:

  - blank 8: each page-1 value at the spacing the five completed jobs on it
    agree on (24162, 25001, 25004, 25016, 25019)
  - blank 7: storeys 1 and 2 keep their list and heading and drop the other
    list and the "DELETE AS REQUIRED" note; no storeys is refused

XML level, no Word (draft_contract.py runs the layout pass). Exit 0 = pass.
"""
import os
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))
import edit_inclusions as ed  # noqa: E402
import fill_inclusions as fi  # noqa: E402
import gate_inclusions as gi  # noqa: E402

CONTRACTS = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS")
SEQ = CONTRACTS / "REGION - SEQ" / "INCLUSIONS"
OUT = HERE.parents[2] / "runtime" / "contract-admin" / "reports" / "_test_live_blanks"
ONE = {"lot_no": "9101", "street": "Sample Road", "suburb": "SAMPLETOWN QLD", "estate": "Sample Estate",
       "house_type": "Sample 230", "house_size": "230.00 m\u00b2", "facade": "Sample Fa\u00e7ade",
       "garage_side": "Right Hand Side", "price": "450,000.00", "owner_1": "Alex SAMPLE", "owner_2": "",
       "owners": "Alex SAMPLE", "site_address": "9101, Sample Road (Sample Estate), SAMPLETOWN QLD 4000",
       "builders_rep": "Sample REP"}
TWO = {**ONE, "owner_2": "Sam SAMPLE", "owners": "Alex SAMPLE & Sam SAMPLE"}
# blank 8's page-1 spacing on its five completed jobs (total spaces between label and value)
BLANK8_SPACING = {"Lot No.:": 3, "HOUSE TYPE:": 6, "STREET:": 3, "HOUSE SIZE:": 7, "SUBURB:": 1,
                  "HOUSE FA\u00c7ADE:": 1, "ESTATE:": 3, "GARAGE SIDE:": 5, "PRICE:": 6}
TEXT = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)


def live_blanks():
    found = [*(SEQ / "INVESTOR & FIRST HOME OWNER").glob("[0-9]*.docx"), *(SEQ / "OWNER OCCUPIER").glob("*.docx"),
             *(CONTRACTS / "REGION - SYDNEY" / "INCLUSIONS").glob("[0-9]. Sydney*.docx"),
             *(CONTRACTS / "REGION - GUNNEDAH, NSW").glob("*INTEGRITY*.docx")]
    return sorted(p for p in found if not p.name.startswith("~$"))


def filled(blank, job):
    fam_name, fam = fi.pick_family(str(blank))
    report = []
    xml = fi.fill(fi.read_xml(blank), job, report, fam)
    xml, _ = fi.drop_instruction_paras(xml, fam_name)
    xml, _ = fi.signature_tabs(xml, job, fam)
    return fam_name, xml, report


def save(name, blank, xml):
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}.docx"
    fi.write_docx(blank, out, xml)
    return str(out)


def owners_boxes(xml, owners):
    """Text of each copy of the box under every ACKNOWLEDGEMENTS & SIGNATURE heading."""
    got = []
    for m in re.finditer(re.escape(fi.xml_escape("ACKNOWLEDGEMENTS & SIGNATURE")), xml):
        got += [fi.run_text(xml[s:e]).strip() for s, e in fi.box_after(xml, m.end())]
    return got and all(t == owners for t in got), got


def page1_spacing(xml):
    tbl = xml[xml.find("<w:tbl>"):xml.find("</w:tbl>")]
    cells = ["".join(TEXT.findall(c)) for c in re.findall(r"<w:tc>.*?</w:tc>", tbl, re.S)]
    got = {}
    for c in cells:
        for label in BLANK8_SPACING:
            if c.startswith(label):
                rest = c[len(label):]
                got[label] = len(rest) - len(rest.lstrip(" "))
    return got


def main():
    failures = []

    def check(ok, what):
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    blanks = live_blanks()
    check(len(blanks) >= 11, f"{len(blanks)} live blanks listed")
    for blank in blanks:
        short = blank.name[:44]
        for tag, job in (("one owner", ONE), ("two owners", TWO)):
            fam, xml, report = filled(blank, job)
            missed = [e["anchor"][:24] for e in report if not e.get("skipped") and not e["hits"]]
            check(not missed, f"{short} [{tag}]: every field filled {missed or ''}")
            ok, got = owners_boxes(xml, job["owners"])
            check(ok, f"{short} [{tag}]: owners in each owners box {'' if ok else got}")
            path = save(f"{blank.stem[:12].strip()}_{tag[:3]}", blank, xml)
            lines = []
            check(gi.check_site_box(path, lines), f"{short} [{tag}]: {lines[-1][:90]}")
            if fi.FAMILIES[fam].get("tabs"):
                lines = []
                check(gi.check_signature_lines(path, lines, fam), f"{short} [{tag}]: {lines[-1][:90]}")
        if fam in ed.FAMILY_RULES and not blank.name.startswith("7."):
            check(ed.storey_choice(ed.Columns(xml)) is None, f"{short}: no storey lists")

    b8 = next((b for b in blanks if b.name.startswith("8.") and b.parent.name.startswith("INVESTOR")), None)
    if b8:
        got = page1_spacing(filled(b8, ONE)[1])
        check(got == BLANK8_SPACING, f"blank 8: page-1 values at the completed jobs' spacing {got}")
    else:
        check(False, "blank 8 not found on the drive")

    b7 = next((b for b in blanks if b.name.startswith("7.") and b.parent.name.startswith("INVESTOR")), None)
    if b7:
        xml = filled(b7, ONE)[1]
        check(ed.storey_choice(ed.Columns(xml)) is not None, "blank 7: storey lists found")
        for storeys, keep, drop in ((1, "SINGLE STOREY", "DOUBLE STOREY"), (2, "DOUBLE STOREY", "SINGLE STOREY")):
            cols, log, flags = ed.Columns(xml), [], []
            ed.edit_storeys(cols, storeys, log, flags)
            right = [ed.norm(ed.ptext(p)) for p in cols.right]
            left = [ed.norm(ed.ptext(p)) for p in cols.left]
            check(keep in right and drop not in right and ed.STOREY_NOTE not in left and len(flags) == 1,
                  f"blank 7, storeys {storeys}: {keep} kept, {drop} list and the note gone, flagged")
        try:
            ed.edit_storeys(ed.Columns(xml), None, [], [])
            check(False, "blank 7, no storeys: refused")
        except SystemExit as e:
            check("STOREYS NEEDED" in str(e), "blank 7, no storeys: refused (STOREYS NEEDED)")
    else:
        check(False, "blank 7 not found on the drive")

    print(f"\n{'PASS' if not failures else 'FAIL'} - {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
