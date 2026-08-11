"""Compact block-level diff between two .docx files.

Usage: python docx_diff.py <blank.docx> <completed.docx> [--width N]

Prints only the blocks that differ, truncated, so a large contract document
produces a short readable summary instead of dumping client detail.
"""
import os
import sys
import difflib
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx_text import walk  # noqa: E402


def blocks(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return [t for _, t in walk(root)]


def split_cells(line):
    """A table row block is cells joined by ' ~ ' - compare cell by cell."""
    return line.split(" ~ ") if " ~ " in line else [line]


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    width = 150
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])

    a, b = blocks(a_path), blocks(b_path)
    print(f"blank     : {len(a)} blocks")
    print(f"completed : {len(b)} blocks")
    print()

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changes = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        changes += 1
        print(f"### {tag}: blank[{i1}:{i2}] -> completed[{j1}:{j2}]")
        if tag in ("replace", "delete"):
            for line in a[i1:i2]:
                for cell in split_cells(line):
                    if cell.strip():
                        print(f"  - {cell[:width]}")
        if tag in ("replace", "insert"):
            for line in b[j1:j2]:
                for cell in split_cells(line):
                    if cell.strip():
                        print(f"  + {cell[:width]}")
        print()

    if not changes:
        print("(no block-level differences)")
    else:
        print(f"== {changes} changed region(s) ==")


if __name__ == "__main__":
    main()
