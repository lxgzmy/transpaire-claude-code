"""Dump the visible text of a .docx (paragraphs + table cells) using stdlib only.

Usage: python docx_text.py <file.docx> [--max N]
Reads word/document.xml out of the zip and walks it in document order so table
content appears where it actually sits in the document.
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_text(p):
    """Concatenate the runs of one <w:p>, keeping tabs as | separators."""
    out = []
    for node in p.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag == W + "tab":
            out.append(" | ")
        elif node.tag == W + "br":
            out.append(" / ")
    return "".join(out).strip()


def walk(el, depth=0, rows=None):
    """Emit (kind, text) in document order. Tables are flagged so the diff is readable."""
    rows = [] if rows is None else rows
    for child in el:
        if child.tag == W + "p":
            t = para_text(child)
            if t:
                rows.append(("P", t))
        elif child.tag == W + "tbl":
            rows.append(("TBL", "--- table ---"))
            for tr in child.findall(W + "tr"):
                cells = []
                for tc in tr.findall(W + "tc"):
                    cell = " ".join(
                        para_text(p) for p in tc.findall(W + "p") if para_text(p)
                    )
                    cells.append(cell)
                line = " ~ ".join(cells).strip()
                if line.strip(" ~"):
                    rows.append(("TR", line))
            rows.append(("TBL", "--- /table ---"))
        else:
            walk(child, depth + 1, rows)
    return rows


def main():
    path = sys.argv[1]
    limit = None
    if "--max" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--max") + 1])
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    rows = walk(root)
    if limit:
        rows = rows[:limit]
    for i, (kind, text) in enumerate(rows, 1):
        print(f"{i:04d} [{kind}] {text}")
    print(f"\n== {len(rows)} blocks ==", file=sys.stderr)


if __name__ == "__main__":
    main()
