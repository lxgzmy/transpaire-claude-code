#!/usr/bin/env python3
"""Parse a weekly BA report export (.xlsx) into a row model.

The report layout is documented in ``reference/osc-field-map.md``: header on
row 1, one row per job, columns A-K. Column G ("Submit all RFI Items") holds
a date serial when the job's RFI response is complete, or a "PENDING ..."
item list while in flight; E can also hold text (e.g. "AWAITING RFI").

Usage:
  python ba_report_parse.py REPORT.xlsx            # summary to stdout
  python ba_report_parse.py REPORT.xlsx --json OUT # full row model as JSON

Read-only. Output JSON goes to the runtime folders only.
"""
import json
import re
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min

# Report column -> row-model key (see reference/osc-field-map.md)
COLUMNS = {
    "A": "job_no",
    "B": "marketer",
    "C": "address",
    "D": "submit_for_ba",
    "E": "received_rfi",
    "F": "received_covenant",
    "G": "submit_all_rfi_items",
    "H": "ba_received",
    "I": "deposit_paid",
    "J": "nominate_site_start",
    "K": "site_start_physical",
}
DATE_KEYS = [v for k, v in COLUMNS.items() if k >= "D"]

EPOCH = date(1899, 12, 30)  # Excel serial epoch (1900 date system)


def serial_to_iso(value):
    try:
        return (EPOCH + timedelta(days=int(float(value)))).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def parse_items(g_text):
    """Split a 'PENDING A (REVIEW), B, C (W/O X)' cell into items.

    Returns [{name, state}] where state is the trailing parenthetical (or
    slash-suffix) hint if present, else "".
    """
    text = (g_text or "").strip()
    text = re.sub(r"^PENDING\s*", "", text, flags=re.I)
    items = []
    for raw in re.split(r",", text):
        part = " ".join(raw.split())
        if not part:
            continue
        m = re.search(r"\(([^)]*)\)\s*$", part)
        state = m.group(1).strip() if m else ""
        name = re.sub(r"\s*\([^)]*\)\s*$", "", part).strip()
        if name:
            items.append({"name": name, "state": state})
    return items


def parse_report(path):
    """Return {source, rows: [...]} for one report workbook."""
    z = zipfile.ZipFile(path)
    shared = xlsx_min.load_shared(z)
    sheets = xlsx_min.sheet_parts(z)
    raw_rows = xlsx_min.read_rows(z, sheets[0][1], shared)
    rows = []
    for rnum, cells in raw_rows:
        job_no = (cells.get("A") or "").strip()
        if not job_no or job_no.lower().startswith("job"):
            continue  # header / blank
        row = {"row": int(rnum)}
        for col, key in COLUMNS.items():
            row[key] = cells.get(col, "").strip() if isinstance(cells.get(col), str) else cells.get(col)
        for key in DATE_KEYS:
            val = row.get(key)
            iso = serial_to_iso(val) if val not in (None, "") else None
            row[key] = {"raw": val, "date": iso}
        g = row["submit_all_rfi_items"]
        g["pending"] = g["date"] is None and bool(g["raw"])
        g["items"] = parse_items(str(g["raw"])) if g["pending"] else []
        row["complete"] = row["ba_received"]["date"] is not None
        rows.append(row)
    return {"source": str(path), "rows": rows}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    out = None
    if "--json" in argv:
        out = argv[argv.index("--json") + 1]
    model = parse_report(path)
    if out:
        Path(out).write_text(json.dumps(model, indent=2), encoding="utf-8")
        print(f"{len(model['rows'])} rows -> {out}")
    else:
        pending = [r for r in model["rows"] if r["submit_all_rfi_items"]["pending"]]
        print(f"{path}: {len(model['rows'])} job rows, {len(pending)} with outstanding items")
        for r in pending:
            names = ", ".join(i["name"] for i in r["submit_all_rfi_items"]["items"])
            print(f"  {r['job_no']}: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
