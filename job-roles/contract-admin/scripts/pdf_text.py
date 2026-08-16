"""Extract text from a PDF's content streams. Stdlib only (zlib).

    python pdf_text.py <file.pdf> [--grep PATTERN]

Enough to pull the house size and garage side off a set of Archicad plans
(CD-2.7, CD-2.9) without a PDF library. Decompresses Flate streams and reads the
text-showing operators.

This is a plans-reading aid, not a general PDF extractor: it ignores font
encoding maps, so an unusual font can come out as mojibake. Treat anything it
returns as needing a human's eye before it lands in a contract - which is the
rule for those two fields anyway.
"""
import sys
import argparse
import re
import zlib
from pathlib import Path

# ( ... ) Tj   |   [ (a) (b) ] TJ
SHOW = re.compile(rb"\((?:[^()\\]|\\.)*\)")


def streams(data):
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        blob = m.group(1)
        try:
            yield zlib.decompress(blob)
        except zlib.error:
            continue


def unescape(b):
    # \ddd octal escapes first - Archicad writes UTF-16 text as \000H\000y...
    b = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8) & 0xFF]), b)
    return (
        b.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
        .replace(rb"\n", b"\n").replace(rb"\r", b"").replace(rb"\t", b"\t")
    )


def decode(piece):
    """Archicad and other CAD exports store show-strings as UTF-16BE."""
    if piece[:2] == b"\xfe\xff":
        return piece[2:].decode("utf-16-be", "replace")
    if piece.count(b"\x00") > len(piece) // 4:
        if len(piece) % 2:
            piece += b"\x00"
        return piece.decode("utf-16-be", "replace")
    try:
        return piece.decode("utf-8")
    except UnicodeDecodeError:
        return piece.decode("latin-1", "replace")


def text_of(pdf_path):
    data = Path(pdf_path).read_bytes()
    out = []
    for s in streams(data):
        if b"Tj" not in s and b"TJ" not in s:
            continue
        for m in SHOW.finditer(s):
            piece = decode(unescape(m.group(0)[1:-1]))
            if piece and printable_ratio(piece) > 0.8:
                out.append(piece)
    return out


def printable_ratio(s):
    """Embedded font programs also live in (...) strings - drop them."""
    ok = sum(1 for c in s if c.isprintable() or c in "\n\t")
    return ok / len(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--grep", help="only show pieces matching this pattern (case-insensitive)")
    ap.add_argument("--max", type=int, default=4000,
                    help="cap on characters printed (0 = no cap). The default keeps "
                         "quick looks cheap; scanned-in land contracts and 90-page "
                         "packs need --max 0 or they truncate SILENTLY.")
    args = ap.parse_args()

    pieces = text_of(args.pdf)
    print(f"{Path(args.pdf).name}: {len(pieces)} text pieces")
    if args.grep:
        rx = re.compile(args.grep, re.I)
        for i, p in enumerate(pieces):
            if rx.search(p):
                ctx = " ".join(pieces[max(0, i - 3):i + 4])
                print(f"  [{i}] {p}")
                print(f"        ...{ctx[:160]}")
    else:
        joined = " ".join(pieces)
        out = joined if args.max == 0 else joined[:args.max]
        print(out)
        if args.max and len(joined) > args.max:
            print(f"\n[TRUNCATED at {args.max} of {len(joined)} chars - rerun with --max 0]")


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
