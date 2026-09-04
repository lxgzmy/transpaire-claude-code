#!/usr/bin/env python3
"""Minimal stdlib .xlsx reader/writer for the permit-officer workflows.

No third-party packages on the server (no openpyxl), so this reads and
writes the OOXML parts directly: sharedStrings + a worksheet, resolving
cell values; the writer emits a single-sheet workbook with inline strings
and a small fixed style set (see ``write_xlsx``).

Usage:
  python xlsx_min.py BOOK.xlsx                 # sheet list + row/col summary
  python xlsx_min.py BOOK.xlsx --rows N        # dump first N rows (all cells)
  python xlsx_min.py BOOK.xlsx --rows 0        # dump every row
  python xlsx_min.py BOOK.xlsx --sheet 2       # pick a sheet by 1-based index
  python xlsx_min.py BOOK.xlsx --tsv           # tab-separated values to stdout

Reading never modifies the workbook; writing only ever creates new files.
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

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


# ---------------------------------------------------------------- writer

# Style indexes accepted by write_xlsx cells (cellXfs order below).
S_DEFAULT = 0
S_HEADER = 1     # bold, grey fill, wrapped
S_WRAP = 2       # wrapped text
S_RED = 3        # red bold text, wrapped (pending / outstanding items)
S_AMBER = 4      # amber fill, wrapped (age flag: near threshold)
S_REDFILL = 5    # red fill, wrapped (age flag: over threshold)
S_DATE = 6       # dd/mm/yyyy number format
S_FLAGGED = 7    # yellow fill (low-confidence / review-me)

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/></numFmts>
<fonts count="3">
  <font><sz val="10"/><name val="Calibri"/></font>
  <font><b/><sz val="10"/><name val="Calibri"/></font>
  <font><b/><sz val="10"/><color rgb="FFCC0000"/><name val="Calibri"/></font>
</fonts>
<fills count="6">
  <fill><patternFill patternType="none"/></fill>
  <fill><patternFill patternType="gray125"/></fill>
  <fill><patternFill patternType="solid"><fgColor rgb="FFD9D9D9"/><bgColor indexed="64"/></patternFill></fill>
  <fill><patternFill patternType="solid"><fgColor rgb="FFFFE699"/><bgColor indexed="64"/></patternFill></fill>
  <fill><patternFill patternType="solid"><fgColor rgb="FFFFC7CE"/><bgColor indexed="64"/></patternFill></fill>
  <fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="8">
  <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
  <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  <xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
  <xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0"/>
  <xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
</cellXfs>
</styleSheet>"""


def _col_letter(n):
    c = ""
    while n:
        n, rem = divmod(n - 1, 26)
        c = chr(65 + rem) + c
    return c


def write_xlsx(path, rows, sheet_name="Sheet 1", col_widths=None):
    """Write a single-sheet workbook.

    rows: list of rows; each row is a list of cells; each cell is either a
    plain value (str/int/float/None) or a (value, style_index) tuple using
    the S_* constants. Numeric values are written as numbers (so Excel date
    serials + S_DATE render as dates); everything else as inline strings.
    col_widths: optional {column letter: width}.
    """
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if col_widths:
        lines.append("<cols>")
        for col, width in sorted(col_widths.items(), key=lambda kv: col_index(kv[0])):
            i = col_index(col)
            lines.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
        lines.append("</cols>")
    lines.append("<sheetData>")
    for rn, row in enumerate(rows, 1):
        lines.append(f'<row r="{rn}">')
        for cn, cell in enumerate(row, 1):
            style = S_DEFAULT
            value = cell
            if isinstance(cell, tuple):
                value, style = cell
            if value is None or value == "":
                if style != S_DEFAULT:
                    lines.append(f'<c r="{_col_letter(cn)}{rn}" s="{style}"/>')
                continue
            ref = f"{_col_letter(cn)}{rn}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                lines.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
            else:
                text = escape(str(value)).replace("\n", "&#10;")
                lines.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
        lines.append("</row>")
    lines.append("</sheetData></worksheet>")
    sheet_xml = "\n".join(lines)

    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                     '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                     '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                     '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", _STYLES_XML)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)


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
