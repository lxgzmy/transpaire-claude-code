"""Word-level diff of one block (or all blocks) between two .docx files.

Usage: python docx_worddiff.py <a.docx> <b.docx> [blockIndex ...]

Block indexes are 1-based, matching docx_text.py output. Omit them to scan every
block. Prints only the differing words with a few words of context, so a long
specification block reduces to just the edits.
"""
import os
import sys
import re
import difflib
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx_text import walk  # noqa: E402


def blocks(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return [t for _, t in walk(root)]


def words(s):
    return re.findall(r"\S+", s)


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    idxs = [int(x) for x in sys.argv[3:] if x.isdigit()]

    a, b = blocks(a_path), blocks(b_path)
    targets = idxs or range(1, min(len(a), len(b)) + 1)

    for i in targets:
        wa, wb = words(a[i - 1]), words(b[i - 1])
        if wa == wb:
            continue
        print(f"### block {i}  ({len(wa)} -> {len(wb)} words)")
        sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            ctx_before = " ".join(wa[max(0, i1 - 6):i1])
            ctx_after = " ".join(wa[i2:i2 + 6])
            print(f"  ...{ctx_before}")
            if tag in ("replace", "delete"):
                print(f"    - {' '.join(wa[i1:i2])[:400]}")
            if tag in ("replace", "insert"):
                print(f"    + {' '.join(wb[j1:j2])[:400]}")
            print(f"  {ctx_after}...")
            print()
        print()


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
