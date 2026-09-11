#!/usr/bin/env python3
"""Parse a weekly BA report (.xlsx) into a row model.

The report layout is documented in ``reference/osc-field-map.md`` and
``fixtures/ba-report-layout.md``: header on row 1, one row per job, columns
A-K from the OSC Executive Reporter export. Column G ("Submit all RFI Items")
holds a date serial when the job's RFI response is complete, or a
"PENDING ..." item list while in flight (optionally followed by a
"RESOLVED ..." line naming items closed during the last cycle); E can also
hold text (e.g. "AWAITING RFI").

Since v0.2 the AI draft (and the officer's corrected copy of it) may carry
four extra per-item columns L-O — Assigned to, Date submitted, Date resolved,
Days outstanding — one line per item in the same order as G. They are read
back only when the line counts line up with G; otherwise the row is marked
``item_cols_misaligned`` and the drafter ignores them.

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

# v0.2 per-item columns (kept apart from COLUMNS so DATE_KEYS ignores them).
ITEM_COLUMNS = {
    "L": "assigned_to",
    "M": "date_submitted",
    "N": "date_resolved",
    "O": "days_outstanding",
}
ITEM_HEADERS = ["Assigned to", "Date submitted", "Date resolved", "Days outstanding"]

EPOCH = date(1899, 12, 30)  # Excel serial epoch (1900 date system)


def serial_to_iso(value):
    try:
        return (EPOCH + timedelta(days=int(float(value)))).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def text_to_iso(value):
    """ISO date from 'dd/mm/yyyy', 'yyyy-mm-dd', or an Excel serial string."""
    if value in (None, ""):
        return None
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    if re.match(r"^\d+(\.0+)?$", s):
        return serial_to_iso(s)
    return None


def split_pending_resolved(g_text):
    """Split G text into (pending_text, resolved_text)."""
    text = (g_text or "").strip()
    m = re.search(r"(?:^|\n)\s*RESOLVED\b\s*(.*)$", text, flags=re.I | re.S)
    if not m:
        return text, ""
    return text[:m.start()].strip(), m.group(1).strip()


def parse_items(g_text):
    """Split a 'PENDING A (REVIEW), B, C (W/O X)' cell into items.

    Returns [{name, state}] where state is the trailing parenthetical (or
    slash-suffix) hint if present, else "".
    """
    text = (g_text or "").strip()
    text = re.sub(r"^(PENDING|RESOLVED)\s*", "", text, flags=re.I)
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


def _lines(value):
    if value in (None, ""):
        return None
    return [ln.strip() for ln in str(value).split("\n")]


def attach_item_columns(g, cells):
    """Zip L-O lines onto g['items'] + g['resolved'] when counts line up."""
    present = {col: _lines(cells.get(col)) for col in ITEM_COLUMNS}
    if not any(present.values()):
        g["item_cols_present"] = False
        return
    g["item_cols_present"] = True
    all_items = g["items"] + g["resolved"]
    n = len(all_items)
    for col, lines in present.items():
        if lines is not None and len(lines) != n:
            g["item_cols_misaligned"] = True
            return
    g["item_cols_misaligned"] = False
    for i, item in enumerate(all_items):
        for col, key in ITEM_COLUMNS.items():
            lines = present[col]
            val = lines[i] if lines is not None else ""
            if key in ("date_submitted", "date_resolved"):
                item[key] = text_to_iso(val)
            elif key == "days_outstanding":
                m = re.match(r"^(\d+)", val)
                item[key] = int(m.group(1)) if m else None
            else:
                item[key] = re.sub(r"^\W+", "", val).strip() or None  # strip ⚠ marker


def parse_report(path):
    """Return {source, rows: [...], header_warnings: [...]} for one workbook."""
    z = zipfile.ZipFile(path)
    shared = xlsx_min.load_shared(z)
    sheets = xlsx_min.sheet_parts(z)
    raw_rows = xlsx_min.read_rows(z, sheets[0][1], shared)
    rows = []
    warnings = []
    for rnum, cells in raw_rows:
        job_no = (cells.get("A") or "").strip()
        if not job_no or job_no.lower().startswith("job"):
            if job_no.lower().startswith("job"):
                l1 = (cells.get("L") or "").strip()
                if l1 and not l1.lower().startswith("assigned"):
                    warnings.append(f"row {rnum}: column L header is {l1!r}, expected 'Assigned to' — "
                                    "L-O layout may have moved; per-item values not trusted")
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
        pending_text, resolved_text = split_pending_resolved(str(g["raw"])) if g["pending"] else ("", "")
        g["items"] = parse_items(pending_text) if g["pending"] else []
        g["resolved"] = parse_items(resolved_text) if resolved_text else []
        for r in g["resolved"]:
            r["date_resolved"] = text_to_iso(r["state"])
        if warnings:
            g["item_cols_present"] = False
        else:
            attach_item_columns(g, cells)
        row["complete"] = row["ba_received"]["date"] is not None
        rows.append(row)
    return {"source": str(path), "rows": rows, "header_warnings": warnings}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    out = None
    if "--json" in argv:
        out = argv[argv.index("--json") + 1]
    model = parse_report(path)
    for w in model["header_warnings"]:
        print(f"WARNING {w}")
    if out:
        Path(out).write_text(json.dumps(model, indent=2), encoding="utf-8")
        print(f"{len(model['rows'])} rows -> {out}")
    else:
        pending = [r for r in model["rows"] if r["submit_all_rfi_items"]["pending"]]
        print(f"{path}: {len(model['rows'])} job rows, {len(pending)} with outstanding items")
        for r in pending:
            g = r["submit_all_rfi_items"]
            names = ", ".join(i["name"] for i in g["items"])
            extra = f"  [resolved: {', '.join(i['name'] for i in g['resolved'])}]" if g["resolved"] else ""
            print(f"  {r['job_no']}: {names}{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
