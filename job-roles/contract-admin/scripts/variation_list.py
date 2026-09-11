"""Read the Standard Variation Costs workbook (the house wording for upgrades). Stdlib only.

    python variation_list.py --region NSW --categories
    python variation_list.py --region NSW --list [--category "Ceiling Height"]
    python variation_list.py --region NSW --search "2700 ceiling ground floor"
    python variation_list.py --region NSW --normalise "Provide 2700mm nominal ceiling height ... in lieu of standard.\\nNote: Price includes ..."

The workbook is `Standard Variation Costs 2025 (up to 220m2).xlsm` under
Z:\\ESTIMATING\\6. Sales Estimating\\3. Variations\\STANDARD VARIATION\\. Its
"NSW Variation List" and "QLD Variation List" sheets hold, in column A, the
category headings (one word or two, no price) and the item descriptions
("Provide ..."), with the single / double storey prices in B and C. It is
read live each run - nothing is cached - and the sheet's own version date is
printed, so a stale copy of the wording can never be mistaken for current.

Reviewer rules (NSW inclusions feedback sheet 9.9, rows 9 and 10) applied by
normalise():
  - drop the leading "Provide"
  - drop "in lieu of ..." to the end of that sentence
  - drop any "Note:" line that is about price ("Price includes ...", "Pricing is
    per ...", "Nil Cost Variation")
  - keep every other note, one line each, no blank line inside the item

search() is ASSISTIVE ONLY. It scores rows by keyword overlap so the person
running the skill can see candidates; choosing the row for a request, and any
custom wording where no row exists, is a judgment that stays with a person
(instruction, 10 Sep 2026) - the run reports the chosen row with a confidence
flag for confirmation, it never picks silently.
"""
import argparse
import datetime as dt
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

WORKBOOK = Path(r"Z:\ESTIMATING\6. Sales Estimating\3. Variations\STANDARD VARIATION"
                r"\Standard Variation Costs 2025 (up to 220m2).xlsm")
SHEETS = {"NSW": "NSW Variation List", "QLD": "QLD Variation List"}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

# A "Note:" line that only talks about money is left out of the contract wording.
PRICE_NOTE = re.compile(r"^\s*Note:\s*(price|pricing|nil cost|cost)", re.I)


def _shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
            for si in root.findall("m:si", NS)]


def _sheet_path(z, name):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
    for s in wb.find("m:sheets", NS):
        if s.get("name") == name:
            target = relmap[s.get(RID)]
            return target[1:] if target.startswith("/") else "xl/" + target
    raise SystemExit(f"ERROR: sheet {name!r} not in {z.filename}")


def _cells(z, path, shared):
    """{(row, col_letter): value} for one sheet."""
    root = ET.fromstring(z.read(path))
    out = {}
    for c in root.iter("{%s}c" % NS["m"]):
        ref, t = c.get("r"), c.get("t")
        v = c.find("m:v", NS)
        if t == "s" and v is not None:
            val = shared[int(v.text)]
        elif t == "inlineStr":
            val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
        else:
            val = v.text if v is not None else ""
        if val is None or val == "":
            continue
        m = re.match(r"([A-Z]+)(\d+)", ref)
        out[(int(m.group(2)), m.group(1))] = val
    return out


def _excel_date(serial):
    try:
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(float(serial)))).isoformat()
    except (TypeError, ValueError):
        return str(serial)


def load(region, workbook=WORKBOOK):
    """{'version_date', 'sheet', 'categories': [...], 'rows': [{category, row, text, single, double}]}"""
    region = region.upper()
    if region not in SHEETS:
        raise SystemExit(f"ERROR: region must be one of {', '.join(SHEETS)} (got {region!r})")
    if not Path(workbook).exists():
        raise SystemExit(f"ERROR: Standard Variation workbook not found: {workbook}")
    with zipfile.ZipFile(workbook) as z:
        shared = _shared_strings(z)
        cells = _cells(z, _sheet_path(z, SHEETS[region]), shared)
    version = _excel_date(cells.get((2, "C"), ""))
    rows, categories, current = [], [], None
    for r in sorted({k[0] for k in cells}):
        a = cells.get((r, "A"))
        if not a or r <= 3:
            continue
        text = a.strip()
        b, c = cells.get((r, "B"), ""), cells.get((r, "C"), "")
        if not text.lower().startswith("provide") and "\n" not in text and len(text) <= 45:
            current = text  # a category heading: short, no "Provide", no price
            if current not in categories and current != "Select Heading":
                categories.append(current)
            continue
        rows.append({"category": current, "row": r, "text": text,
                     "single": b, "double": c})
    return {"version_date": version, "sheet": SHEETS[region], "workbook": str(workbook),
            "categories": categories, "rows": rows}


def normalise(text):
    """House wording for the contract from a sheet description (rows 9.5 / 9.6)."""
    lines = [l.strip() for l in str(text).replace("\r", "").split("\n")]
    out = []
    for i, line in enumerate(lines):
        if not line:
            continue
        if PRICE_NOTE.match(line):
            continue
        if i == 0 or not line.lower().startswith("note"):
            line = re.sub(r"^provide\s+", "", line, flags=re.I)
            # "in lieu of ..." runs to the end of its sentence (or line)
            line = re.sub(r"\s*,?\s*in lieu of [^.\n]*\.?", "", line, flags=re.I).strip()
            if line and not line.endswith((".", ")")):
                line += "."
            if line:
                line = line[0].upper() + line[1:]
        if line:
            out.append(line)
    return "\n".join(out)


_STOP = {"the", "to", "a", "of", "and", "in", "or", "with", "for", "on", "&", "provide", "-"}


def search(data, query, limit=5):
    """Keyword-overlap candidates for a request line. Assistive only - see module doc."""
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in _STOP]
    scored = []
    for row in data["rows"]:
        hay = f"{row['category']} {row['text']}".lower()
        hits = sum(1 for w in words if w in hay)
        if hits:
            scored.append((hits / max(len(words), 1), row))
    scored.sort(key=lambda s: -s[0])
    return scored[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True, help="NSW or QLD - picks the sheet")
    ap.add_argument("--workbook", default=str(WORKBOOK))
    ap.add_argument("--categories", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--category")
    ap.add_argument("--search")
    ap.add_argument("--normalise")
    args = ap.parse_args()

    if args.normalise:
        print(normalise(args.normalise.replace("\\n", "\n")))
        return 0
    data = load(args.region, args.workbook)
    print(f"sheet    : {data['sheet']}   version date: {data['version_date']}")
    print(f"workbook : {data['workbook']}")
    if args.categories:
        for i, c in enumerate(data["categories"], 1):
            n = sum(1 for r in data["rows"] if r["category"] == c)
            print(f"  {i:2d}. {c}  ({n} item{'s' if n != 1 else ''})")
    if args.list:
        for r in data["rows"]:
            if args.category and r["category"] != args.category:
                continue
            print(f"\n[{r['category']}] row {r['row']}  single {r['single']}  double {r['double']}")
            print("  sheet : " + r["text"].replace("\n", "\n          "))
            print("  house : " + normalise(r["text"]).replace("\n", "\n          "))
    if args.search:
        print(f"\ncandidates for: {args.search!r}  (assistive - a person confirms the row)")
        for score, r in search(data, args.search):
            print(f"\n  {score:4.2f}  [{r['category']}] row {r['row']}")
            print("        " + normalise(r["text"]).replace("\n", "\n        "))
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
