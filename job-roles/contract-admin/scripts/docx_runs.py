"""Show the <w:t> runs around a text anchor in a .docx. Stdlib only.

Usage: python docx_runs.py <file.docx> "<anchor>" [--after N] [--before N]

Used to work out exactly which run carries a fillable value before writing to it.
"""
import sys
import re
import zipfile


def runs(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    return [(m.start(), m.group(1)) for m in
            re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)]


def main():
    path, anchor = sys.argv[1], sys.argv[2]
    after = int(sys.argv[sys.argv.index("--after") + 1]) if "--after" in sys.argv else 6
    before = int(sys.argv[sys.argv.index("--before") + 1]) if "--before" in sys.argv else 1

    rs = runs(path)
    hits = [i for i, (_, t) in enumerate(rs) if anchor.lower() in t.lower()]
    if not hits:
        print(f"  (anchor {anchor!r} not found in a single run - it may be split across runs)")
        return
    for h in hits:
        print(f"  anchor at run #{h}")
        lo, hi = max(0, h - before), min(len(rs), h + after + 1)
        for i in range(lo, hi):
            mark = ">>" if i == h else "  "
            print(f"  {mark} #{i:<5} {rs[i][1]!r}")
        print()


if __name__ == "__main__":
    main()
