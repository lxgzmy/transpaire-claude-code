"""Extract embedded JPEG images from a PDF. Stdlib only.

    python pdf_images.py <file.pdf> -o <outdir>

EOIs and client IDs arrive as phone photos wrapped in a PDF (CD-0.2), and the
server has no poppler, so a scanned page cannot be rendered. Those pages are
stored as whole JPEGs (`/DCTDecode`), which can be lifted out byte-for-byte and
read as images instead.

Only handles DCTDecode (JPEG). Flate-compressed bitmaps are reported, not
converted - there is no image library here to do it with.
"""
import sys
import argparse
import re
from pathlib import Path


def extract(pdf_path, out_dir):
    data = Path(pdf_path).read_bytes()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(pdf_path).stem[:40]

    written = []
    # JPEG streams sit between 'stream' and 'endstream' and start with SOI ffd8ff
    for i, m in enumerate(re.finditer(rb"stream\r?\n?(\xff\xd8\xff.*?)\r?\n?endstream",
                                      data, re.S), 1):
        blob = m.group(1)
        out = out_dir / f"{stem}_img{i}.jpg"
        out.write_bytes(blob)
        written.append((out, len(blob)))

    flate = len(re.findall(rb"/Subtype\s*/Image(?:(?!endobj).)*?/FlateDecode", data, re.S))

    for out, size in written:
        print(f"  wrote {out.name}  ({size/1024:,.0f} KB)")
    if not written:
        print("  no JPEG streams found")
    if flate:
        print(f"  note: {flate} Flate-compressed image(s) present - not extracted")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args()
    print(f"{Path(args.pdf).name}:")
    extract(args.pdf, args.out)


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
