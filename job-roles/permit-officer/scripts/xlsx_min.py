#!/usr/bin/env python3
"""Minimal stdlib .xlsx reader for the permit-officer workflows.

No third-party packages on the server (no openpyxl), so this reads the
OOXML parts directly: sharedStrings + a worksheet, resolving cell values.

Usage:
  python xlsx_min.py BOOK.xlsx                 # sheet list + row/col summary
  python xlsx_min.py BOOK.xlsx --rows N        # dump first N rows (all cells)
  python xlsx_min.py BOOK.xlsx --rows 0        # dump every row
  python xlsx_min.py BOOK.xlsx --sheet 2       # pick a sheet by 1-based index
  python xlsx_min.py BOOK.xlsx --tsv           # tab-separated values to stdout

Read-only: never writes to the workbook.
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def load_shared(z):
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{M}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{M}t")))
    return shared


def sheet_parts(z):
    """Return [(name, part_path)] in workbook order."""
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/xl/workbook.xml.rels".replace("xl/_rels/xl/", "xl/_rels/")))
    rel_map = {}
    for rel in rels:
        rel_map[rel.get("Id")] = rel.get("Target")
    out = []
    for s in wb.iter(f"{M}sheet"):
        target = rel_map.get(s.get(f"{R}id"), "")
        if target.startswith("/"):
            target = target[1:]
        elif not target.startswith("xl/"):
            target = "xl/" + target
        out.append((s.get("name"), target))
    return out


def col_of(ref):
    return re.sub(r"\d", "", ref or "")


def col_index(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def cell_value(c, shared):
    v = c.find(f"{M}v")
    if v is None:
        inline = c.find(f"{M}is")
        if inline is not None:
            return "".join(t.text or "" for t in inline.iter(f"{M}t"))
        return ""
    if c.get("t") == "s":
        try:
            return shared[int(v.text)]
        except (ValueError, IndexError):
            return ""
    return v.text or ""


def read_rows(z, part, shared):
    root = ET.fromstring(z.read(part))
    rows = []
    for r in root.findall(f".//{M}row"):
        cells = {}
        for c in r.findall(f"{M}c"):
            val = cell_value(c, shared)
            if val != "":
                cells[col_of(c.get("r"))] = val
        rows.append((r.get("r"), cells))
    return rows


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    path = argv[0]
    n_rows = None
    sheet_no = 1
    tsv = False
    args = argv[1:]
    while args:
        a = args.pop(0)
        if a == "--rows":
            n_rows = int(args.pop(0))
        elif a == "--sheet":
            sheet_no = int(args.pop(0))
        elif a == "--tsv":
            tsv = True
    z = zipfile.ZipFile(path)
    shared = load_shared(z)
    sheets = sheet_parts(z)
    if n_rows is None and not tsv:
        print(f"{path}")
        for i, (name, part) in enumerate(sheets, 1):
            rows = read_rows(z, part, shared)
            width = max((max((col_index(c) for c in cells), default=0) for _, cells in rows), default=0)
            print(f"  sheet {i}: {name!r} — {len(rows)} rows x {width} cols ({part})")
        return 0
    name, part = sheets[sheet_no - 1]
    rows = read_rows(z, part, shared)
    if n_rows:
        rows = rows[:n_rows]
    if tsv:
        width = max((max((col_index(c) for c in cells), default=0) for _, cells in rows), default=0)
        cols = []
        i = 0
        while len(cols) < width:
            i += 1
            c, n = "", i
            while n:
                n, rem = divmod(n - 1, 26)
                c = chr(65 + rem) + c
            cols.append(c)
        for rnum, cells in rows:
            print("\t".join((cells.get(c, "") or "").replace("\t", " ").replace("\n", " ¶ ") for c in cols))
    else:
        for rnum, cells in rows:
            pretty = " ; ".join(f"{c}={v[:70]}" for c, v in sorted(cells.items(), key=lambda kv: col_index(kv[0])))
            print(f"ROW {rnum} | {pretty}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
