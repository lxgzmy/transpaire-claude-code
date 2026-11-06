r"""Write a synthetic PLANS PDF for the DocuSign sandbox tab check. Stdlib only.

    python synthetic_plans_pdf.py --out "<runtime\docusign-sandbox\...\PLANS_<suffix>.pdf>" [--pages 5]

The sandbox check (docs/superpowers/brainstorms/2026-10-13-docusign-tab-placement.md)
needs a plans PDF beside the filled contract and inclusions, with a page count
that differs from the template's so the flag path runs too. Each A4 page says
SYNTHETIC on it and carries a title block with a client signature line near
the bottom right, where the templates put the plans' signature tabs. No real
drawing, address or name is in it.

Writes only under the checkout's runtime\docusign-sandbox folder, the one
place the sandbox server reads. Exit codes: 0 written, 2 refused.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANDBOX = HERE.parents[2] / "runtime" / "docusign-sandbox"
WIDTH, HEIGHT = 595, 842  # A4 portrait, points


def _text(x, y_top, size, words):
    """A text-showing op at x and y measured from the top, like DocuSign positions."""
    safe = words.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf {x} {HEIGHT - y_top} Td ({safe}) Tj ET\n"


def page_content(n, total):
    ops = ["0.5 w\n",
           f"36 36 {WIDTH - 72} {HEIGHT - 72} re S\n",           # sheet border
           _text(60, 90, 22, "SYNTHETIC PLANS - NOT A REAL JOB"),
           _text(60, 120, 11, f"Sheet {n} of {total}. Sandbox tab check only."),
           f"330 {HEIGHT - 806} 229 110 re S\n",                  # title block, bottom right
           _text(340, 712, 9, "SAMPLE DRAFTING CO. - SYNTHETIC"),
           _text(340, 726, 9, f"DRAWING {n:02d} / {total:02d}"),
           _text(340, 748, 8, "CLIENT SIGNATURE"),
           f"340 {HEIGHT - 772} m 550 {HEIGHT - 772} l S\n",      # the signature line
           _text(340, 790, 8, "DATE")]
    return "".join(ops).encode("latin-1")


def build_pdf(pages):
    """A minimal valid PDF: catalog, page tree, one Helvetica font, one stream per page."""
    objects = []  # index i holds object number i + 1

    def add(body):
        objects.append(body)
        return len(objects)

    catalog = add(None)
    tree = add(None)
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids = []
    for n in range(1, pages + 1):
        data = page_content(n, pages)
        stream = add(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] "
                        b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                        % (tree, WIDTH, HEIGHT, font, stream)))
    objects[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % tree
    objects[tree - 1] = (b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids)
                         + b"] /Count %d >>" % len(kids))
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, catalog, xref)
    return bytes(out)


def check_out(path):
    out = Path(path).resolve()
    sandbox = SANDBOX.resolve()
    if sandbox not in out.parents:
        raise ValueError(f"--out must be under {sandbox}: the sandbox server reads nowhere else")
    if out.suffix.lower() != ".pdf" or not out.name.upper().startswith("PLANS_"):
        raise ValueError("--out must be a PLANS_<suffix>.pdf file name (CD-7.2), so the payload lists it")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", type=int, default=5)
    args = ap.parse_args(argv)
    try:
        out = check_out(args.out)
        if not 1 <= args.pages <= 50:
            raise ValueError("--pages must be 1 to 50")
    except ValueError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build_pdf(args.pages))
    print(f"written: {out} ({args.pages} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
