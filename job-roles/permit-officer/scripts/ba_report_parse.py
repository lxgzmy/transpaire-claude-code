#!/usr/bin/env python3
"""Parse a weekly BA report (.xlsx) into a row model.

The report is the OSC Executive Reporter export (header on row 1, one row
per job — ``reference/osc-field-map.md``, ``fixtures/ba-report-layout.md``).
Since v0.3 columns are located **by header text, not by letter**: the export
gained five columns on 28 Sep 2026 (Engineering Ordered, Receive
Engineering, Review Engineering - Michael, Forward Engineering to Certifier,
Covenant Ordered) and "Submit all RFI Items" moved from G to L. Known
headers map to row keys; every other column is carried through verbatim in
``row["extra"]`` so a draft reproduces the export column for column. The
"Submit all RFI Items" column is required — a workbook without it raises.

That column holds a date serial when the job's RFI response is complete, or
a "PENDING ..." item list while in flight (optionally followed by a
"RESOLVED ..." line naming items closed during the last cycle). Other date
columns can also hold text (e.g. "AWAITING RFI", "PENDING REVIEW").

Per-item values (Assigned to, Date submitted, Date resolved, Days
outstanding) live on a second sheet named **Items**, one row per item, keyed
by Job No. + Item (v0.3; the v0.2 L-O columns on the main sheet proved
unworkable for hand entry). An Items row is attached to the main-sheet item
whose name matches after normalisation; rows that match nothing are
reported in ``items_unmatched`` for the drafter to flag. The v0.2 L-O
columns are still read when their headers are present on the main sheet
(older drafts), with the old one-line-per-item alignment rule.

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

# Known export headers -> row-model key (matched after norm_header, so case,
# spacing and a trailing full stop do not matter). Anything else on the
# header row is an "extra" column, carried verbatim.
HEADER_KEYS = [
    ("Job No.", "job_no"),
    ("Marketer", "marketer"),
    ("Job Address", "address"),
    ("Submit for BA", "submit_for_ba"),
    ("Received RFI", "received_rfi"),
    ("Received Covenant Approval", "received_covenant"),
    ("Submit all RFI Items", "submit_all_rfi_items"),
    ("BA Received", "ba_received"),
    ("Deposit Paid", "deposit_paid"),
    ("Nominate Site Start", "nominate_site_start"),
    ("Site Start (Physical)", "site_start_physical"),
]
KEY_HEADERS = {k: h for h, k in HEADER_KEYS}
TEXT_KEYS = ["job_no", "marketer", "address"]
DATE_KEYS = [k for _, k in HEADER_KEYS if k not in TEXT_KEYS]
REQUIRED_KEY = "submit_all_rfi_items"

# Per-item fields. On the Items sheet they are columns keyed by header; on a
# v0.2 draft they were main-sheet columns L-O, one line per item.
ITEM_FIELDS = [
    ("assigned to", "assigned_to"),
    ("date submitted", "date_submitted"),
    ("date resolved", "date_resolved"),
    ("days outstanding", "days_outstanding"),
]
ITEM_HEADERS = ["Assigned to", "Date submitted", "Date resolved", "Days outstanding"]
ITEMS_SHEET = "Items"
# "Notes" is the officer's own column, carried week to week as typed; "Draft notes" is the
# drafter's evidence and prompts, rewritten each run (27 Oct 2026: the officer wrote her notes
# into the single Notes column of the 22.10 draft, which the next run would have overwritten).
ITEMS_SHEET_HEADERS = ["Job No.", "Item", "Assigned to", "Date submitted",
                       "Date resolved", "Days outstanding", "Flag", "Notes", "Draft notes"]

EPOCH = date(1899, 12, 30)  # Excel serial epoch (1900 date system)


def norm_header(text):
    s = " ".join(str(text or "").split()).strip().lower()
    return s.rstrip(".").strip()


def norm_item(name):
    """Item name key for matching Items-sheet rows to main-sheet items."""
    s = re.sub(r"\s*\([^)]*\)\s*$", "", str(name or "").strip())
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def serial_to_iso(value):
    try:
        return (EPOCH + timedelta(days=int(float(value)))).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def text_to_iso(value):
    """ISO date from 'dd/mm/yyyy' (also with . or - and a two-digit year, as people type them),
    'yyyy-mm-dd', or an Excel serial; None when it is not a real date."""
    if value in (None, ""):
        return None
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b", s)
    if m:
        year = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        try:
            return date(year, int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date.fromisoformat(m.group(0)).isoformat()
        except ValueError:  # 2026-02-30
            return None
    if re.match(r"^\d+(\.\d+)?$", s):
        return serial_to_iso(s)
    return None


def split_pending_resolved(g_text):
    """Split G text into (pending_text, resolved_text)."""
    text = (g_text or "").strip()
    m = re.search(r"(?:^|\n)\s*RESOLVED\b\s*(.*)$", text, flags=re.I | re.S)
    if not m:
        return text, ""
    return text[:m.start()].strip(), m.group(1).strip()


def _split_items(text):
    """Split on commas and line breaks outside brackets: "ENGINEERING (W/O CLIENT, DRAFTING)" is one item."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in ",\n" and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def parse_items(g_text):
    """Split a 'PENDING A (REVIEW), B, C (W/O X)' cell into items.

    Returns [{name, state}] where state is the trailing parenthetical (or
    slash-suffix) hint if present, else "".
    """
    text = (g_text or "").strip()
    text = re.sub(r"^(PENDING|RESOLVED)\s*", "", text, flags=re.I)
    items = []
    for raw in _split_items(text):
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


def _set_item_field(item, key, val):
    val = "" if val is None else str(val).strip()
    if key in ("date_submitted", "date_resolved"):
        item[key] = text_to_iso(val)
        item[key + "_raw"] = val  # what was typed, so an unreadable date is reported, not taken as empty
    elif key == "days_outstanding":
        m = re.match(r"^(\d+)", val)
        item[key] = int(m.group(1)) if m else None
    else:
        item[key] = re.sub(r"^\W+", "", val).strip() or None  # strip ⚠ marker


def attach_item_columns(g, cells, letters):
    """v0.2 layout: zip main-sheet L-O lines onto items when counts line up."""
    present = {key: _lines(cells.get(letters[key])) for key in letters}
    if not any(present.values()):
        g["item_cols_present"] = False
        return
    g["item_cols_present"] = True
    all_items = g["items"] + g["resolved"]
    n = len(all_items)
    for key, lines in present.items():
        if lines is not None and len(lines) != n:
            g["item_cols_misaligned"] = True
            return
    g["item_cols_misaligned"] = False
    for i, item in enumerate(all_items):
        for key, lines in present.items():
            _set_item_field(item, key, lines[i] if lines is not None else "")


def _header_map(raw_rows):
    """Find the header row; return (row_index, {letter: header_text})."""
    for idx, (_rnum, cells) in enumerate(raw_rows):
        if any(norm_header(v).startswith("job no") for v in cells.values()):
            return idx, {col: str(v).strip() for col, v in cells.items() if str(v).strip()}
    return None, {}


def _read_sheet(z, shared, part):
    return xlsx_min.read_rows(z, part, shared)


def parse_items_sheet(z, shared, part):
    """Rows of the Items sheet as dicts keyed by ITEM_FIELDS + job_no/item/flag."""
    raw_rows = _read_sheet(z, shared, part)
    hidx, headers = _header_map(raw_rows)
    if hidx is None:
        return []
    by_norm = {norm_header(h): col for col, h in headers.items()}
    col_job = by_norm.get("job no")
    col_item = by_norm.get("item")
    if not col_job or not col_item:
        return []
    out = []
    for _rnum, cells in raw_rows[hidx + 1:]:
        job_no = str(cells.get(col_job, "") or "").strip()
        name = str(cells.get(col_item, "") or "").strip()
        if not job_no or not name:
            continue
        entry = {"job_no": job_no, "item": name, "flag": str(cells.get(by_norm.get("flag", ""), "") or "").strip(),
                 "row": int(_rnum), "notes": str(cells.get(by_norm.get("notes", ""), "") or "").strip(),
                 "draft_notes": str(cells.get(by_norm.get("draft notes", ""), "") or "").strip(),
                 "own_notes_column": "draft notes" in by_norm}
        for header, key in ITEM_FIELDS:
            _set_item_field(entry, key, cells.get(by_norm.get(header, ""), ""))
        out.append(entry)
    return out


# The drafter's own wording in a v0.3 "Notes" cell (before the officer had a column of her own).
# Only a whole part of the note that is one of these is dropped: inside her own sentence the
# same words ("council to verify the corrected plans") are hers.
DRAFT_NOTE_PHRASES = [r"date submitted (assumed|corrected)(\s*[—–-]\s*please correct)?", r"please correct",
                      r"verify", r"no evidence rule for this item", r"no completion evidence found", r"corrected"]


def own_words(edited, drafted):
    """The officer's words in a Notes cell that first held only the draft's text.

    The draft's longer pieces (evidence such as 'document "APPROVAL - X" attached ...') are taken
    out wherever they stand; then the note is cut at its separators and sentences, and a part that
    is only the draft's stock wording is dropped. Her sentences are kept whole."""
    text = str(edited or "")
    for piece in sorted((p.strip() for p in str(drafted or "").split(";")), key=len, reverse=True):
        if len(piece.split()) >= 3:
            text = text.replace(piece, " ")
    kept = []
    for part in re.split(r";|\s[—–-]\s|[—–]", text):
        for sentence in re.split(r"(?<=\.)\s+", part):
            s = re.sub(r"\s+(please correct|verify)\s*$", "", sentence.strip(" ;—–-"), flags=re.I)
            if s and not any(re.fullmatch(ph, s.strip(" ."), re.I) for ph in DRAFT_NOTE_PHRASES):
                kept.append(s)
    return "; ".join(kept)


def _items_sheet(path):
    with zipfile.ZipFile(path) as z:
        shared = xlsx_min.load_shared(z)
        part = next((p for n, p in xlsx_min.sheet_parts(z) if norm_header(n) == ITEMS_SHEET.lower()), None)
        return parse_items_sheet(z, shared, part) if part else []


def officer_edits(edited_path, drafted_path):
    """What the officer changed on a draft's Items sheet, compared cell by cell with the draft as written.

    Returns {"edits": [...], "unmatched": [...], "drafted_names": {job: {item name key}},
    "last_rows": {(job, item name key): {"item", "flag", "date_submitted", "assigned_to", "hers"}}}:
    last_rows is what each row showed when she left it (the draft's flag; her date and assignee;
    "hers" when she changed either). Each
    edit has job_no, item, row and only the fields she changed: assigned_to ("" = cleared),
    date_submitted (None = emptied, meaning not yet submitted), date_resolved, note ("" =
    cleared); a date she typed that cannot be read comes back as date_submitted_unreadable /
    date_resolved_unreadable (her text), never as an emptied cell. An edited row is matched to the
    drafted row by job and item name, else by row number on the same job.
    """
    drafted = _items_sheet(drafted_path)
    by_name = {(r["job_no"], norm_item(r["item"])): r for r in drafted}
    by_row = {(r["job_no"], r["row"]): r for r in drafted}
    out = {"edits": [], "unmatched": [], "drafted_names": {}, "last_rows": {}}
    for r in drafted:
        out["drafted_names"].setdefault(r["job_no"], set()).add(norm_item(r["item"]))
        out["last_rows"][(r["job_no"], norm_item(r["item"]))] = {
            "item": r["item"], "flag": r.get("flag", "").upper(), "date_submitted": r.get("date_submitted"),
            "assigned_to": r.get("assigned_to"), "hers": False}
    for e in _items_sheet(edited_path):
        d = by_name.get((e["job_no"], norm_item(e["item"]))) or by_row.get((e["job_no"], e["row"]))
        if d is None:
            out["unmatched"].append({"job_no": e["job_no"], "item": e["item"], "row": e["row"]})
            continue
        last = out["last_rows"][(d["job_no"], norm_item(d["item"]))]
        unreadable = e.get("date_submitted_raw") and not e.get("date_submitted")
        last.update(date_submitted=d.get("date_submitted") if unreadable else e.get("date_submitted"),
                    assigned_to=e.get("assigned_to"))
        last["hers"] = (last["date_submitted"] != d.get("date_submitted")
                        or (last["assigned_to"] or "") != (d.get("assigned_to") or ""))
        edit = {"job_no": e["job_no"], "item": e["item"], "row": e["row"],
                "was_resolved": d.get("flag", "").upper() == "RESOLVED"}
        if (e.get("assigned_to") or "") != (d.get("assigned_to") or ""):
            edit["assigned_to"] = e.get("assigned_to") or ""
        if e.get("date_submitted_raw") and not e.get("date_submitted"):
            if e["date_submitted_raw"] != d.get("date_submitted_raw"):
                edit["date_submitted_unreadable"] = e["date_submitted_raw"]
        elif e.get("date_submitted") != d.get("date_submitted"):
            edit["date_submitted"] = e.get("date_submitted")
        if e.get("date_resolved_raw") and not e.get("date_resolved"):
            if e["date_resolved_raw"] != d.get("date_resolved_raw"):
                edit["date_resolved_unreadable"] = e["date_resolved_raw"]
        elif e.get("date_resolved") and e.get("date_resolved") != d.get("date_resolved"):
            edit["date_resolved"] = e["date_resolved"]
        if e["own_notes_column"]:
            if e["notes"] != d.get("notes", ""):
                edit["note"] = e["notes"]
        elif e["notes"] != d.get("notes", ""):
            words = own_words(e["notes"], d.get("notes", ""))
            if words:
                edit["note"] = words
        if len(edit) > 4:
            out["edits"].append(edit)
    return out


def parse_report(path):
    """Return the row model for one workbook.

    {source, sheet_name, columns: [{letter, header, key}], rows: [...],
     header_warnings: [...], items_sheet: bool, items_unmatched: [...]}
    """
    z = zipfile.ZipFile(path)
    shared = xlsx_min.load_shared(z)
    sheets = xlsx_min.sheet_parts(z)
    sheet_name, part = sheets[0]
    raw_rows = _read_sheet(z, shared, part)
    hidx, headers = _header_map(raw_rows)
    if hidx is None:
        raise ValueError(f"{path}: no header row (no 'Job No.' cell) on sheet {sheet_name!r}")

    by_norm = {norm_header(h): col for col, h in headers.items()}
    key_letters = {}
    for header, key in HEADER_KEYS:
        if norm_header(header) in by_norm:
            key_letters[key] = by_norm[norm_header(header)]
    if REQUIRED_KEY not in key_letters:
        raise ValueError(f"{path}: header {KEY_HEADERS[REQUIRED_KEY]!r} not found on row {raw_rows[hidx][0]} "
                         f"— headers seen: {list(headers.values())}")
    warnings = []
    letter_key = {col: key for key, col in key_letters.items()}
    columns = []
    for col in sorted(headers, key=xlsx_min.col_index):
        columns.append({"letter": col, "header": headers[col], "key": letter_key.get(col)})
    legacy_letters = {key: by_norm[h] for h, key in ITEM_FIELDS if h in by_norm}
    for c in columns:
        if c["key"] is None and norm_header(c["header"]) in dict(ITEM_FIELDS):
            c["key"] = "legacy_item_col"
    missing = [KEY_HEADERS[k] for k in DATE_KEYS + TEXT_KEYS if k not in key_letters]
    if missing:
        warnings.append(f"columns not found (left blank): {', '.join(missing)}")
    extras = [c["header"] for c in columns if c["key"] is None]
    if extras:
        warnings.append(f"columns carried verbatim on the main sheet: {', '.join(extras)}")
    if len(legacy_letters) == len(ITEM_FIELDS):
        warnings.append("v0.2 per-item columns found on the main sheet; read with the one-line-per-item rule")

    rows = []
    for _rnum, cells in raw_rows[hidx + 1:]:
        job_no = str(cells.get(key_letters.get("job_no", "A"), "") or "").strip()
        if not job_no:
            continue  # blank / spacer row
        row = {"row": int(_rnum), "extra": {}}
        for key in TEXT_KEYS:
            v = cells.get(key_letters.get(key, ""), "")
            row[key] = v.strip() if isinstance(v, str) else v
        for key in DATE_KEYS:
            val = cells.get(key_letters.get(key, ""), "")
            val = val.strip() if isinstance(val, str) else val
            iso = serial_to_iso(val) if val not in (None, "") else None
            row[key] = {"raw": val, "date": iso}
        for c in columns:
            if c["key"] is None:
                val = cells.get(c["letter"], "")
                val = val.strip() if isinstance(val, str) else val
                row["extra"][c["header"]] = {"raw": val, "date": serial_to_iso(val) if val not in (None, "") else None}
        g = row["submit_all_rfi_items"]
        # Only a "PENDING ..." list is items; other text ("AWAITING RFI") is carried verbatim.
        is_text = g["date"] is None and bool(g["raw"])
        g["pending"] = is_text and bool(re.match(r"^\s*PENDING\b", str(g["raw"]), re.I))
        g["other_text"] = is_text and not g["pending"]
        pending_text, resolved_text = split_pending_resolved(str(g["raw"])) if g["pending"] else ("", "")
        g["items"] = parse_items(pending_text) if g["pending"] else []
        g["resolved"] = parse_items(resolved_text) if resolved_text else []
        for r in g["resolved"]:
            r["date_resolved"] = text_to_iso(r["state"])
        if len(legacy_letters) == len(ITEM_FIELDS):
            attach_item_columns(g, cells, legacy_letters)
        else:
            g["item_cols_present"] = False
        row["items_unmatched"] = []
        row["complete"] = row["ba_received"]["date"] is not None
        rows.append(row)

    # ---- Items sheet (v0.3): one row per item, matched by job + item name
    items_part = next((p for n, p in sheets if norm_header(n) == ITEMS_SHEET.lower()), None)
    items_unmatched = []
    if items_part:
        by_job = {str(r["job_no"]): r for r in rows}
        for entry in parse_items_sheet(z, shared, items_part):
            row = by_job.get(entry["job_no"])
            target = None
            if row:
                g = row["submit_all_rfi_items"]
                want = norm_item(entry["item"])
                target = next((i for i in g["items"] + g["resolved"] if norm_item(i["name"]) == want), None)
            if target is None:
                # A RESOLVED row whose job has since closed its RFI cell (a
                # date instead of a PENDING list) is history, not a mistake.
                closed = entry.get("date_resolved") or entry.get("flag", "").upper() == "RESOLVED"
                if row and closed and not row["submit_all_rfi_items"]["pending"]:
                    continue
                items_unmatched.append(entry)
                if row:
                    row["items_unmatched"].append(entry)
                continue
            for _h, key in ITEM_FIELDS:
                target[key] = entry.get(key)
            target["items_sheet"] = True
            row["submit_all_rfi_items"]["item_cols_present"] = True
            row["submit_all_rfi_items"]["item_cols_misaligned"] = False

    return {"source": str(path), "sheet_name": sheet_name, "columns": columns, "rows": rows,
            "header_warnings": warnings, "items_sheet": items_part is not None,
            "items_unmatched": items_unmatched}


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
        print(f"NOTE {w}")
    if out:
        Path(out).write_text(json.dumps(model, indent=2), encoding="utf-8")
        print(f"{len(model['rows'])} rows -> {out}")
    else:
        pending = [r for r in model["rows"] if r["submit_all_rfi_items"]["pending"]]
        print(f"{path}: {len(model['rows'])} job rows, {len(pending)} with outstanding items; "
              f"columns: {', '.join(c['header'] for c in model['columns'])}; "
              f"Items sheet: {'yes' if model['items_sheet'] else 'no'}")
        for r in pending:
            g = r["submit_all_rfi_items"]
            names = ", ".join(i["name"] for i in g["items"])
            extra = f"  [resolved: {', '.join(i['name'] for i in g['resolved'])}]" if g["resolved"] else ""
            print(f"  {r['job_no']}: {names}{extra}")
        for e in model["items_unmatched"]:
            print(f"  ! Items row not matched: job {e['job_no']} item {e['item']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
