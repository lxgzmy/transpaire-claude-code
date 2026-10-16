"""Unit test for site_streets.py and the GARAGE SIDE values fill_inclusions.py takes (issue #59).

    python test_site_streets.py

Synthetic PDFs built in memory (no client data): a three-page set whose title
block names the lot's street on every page, with the site plan on page 1.
"""
import sys
import tempfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import site_streets  # noqa: E402
from fill_inclusions import GARAGE_RE  # noqa: E402


def pdf(pages, compress=True):
    """A minimal PDF: catalog -> pages -> one content stream per page, one
    BT..ET text object per label."""
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>"}
    kids = []
    for i, labels in enumerate(pages):
        page, content = 3 + 2 * i, 4 + 2 * i
        kids.append(f"{page} 0 R".encode())
        stream = b"".join(b"BT /F1 9 Tf 10 10 Td (" + l.encode("latin-1") + b") Tj ET\n" for l in labels)
        if compress:
            stream = zlib.compress(stream)
        objs[page] = f"<< /Type /Page /Parent 2 0 R /Contents {content} 0 R >>".encode()
        objs[content] = (b"<< /Length " + str(len(stream)).encode()
                         + (b" /Filter /FlateDecode" if compress else b"") + b" >>\nstream\n" + stream + b"\nendstream")
    objs[2] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count " + str(len(pages)).encode() + b" >>"
    return b"%PDF-1.4\n" + b"".join(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n" for n in sorted(objs)) + b"%%EOF\n"


TITLE = ["Lot 901 Sample Road Exampleton NSW 2999", "Sample Road", "Suite 3.3, 328 Example Drive"]
CASES = [
    ("corner", [["Cover & Site Plan", "Sample Road", "Example Street", "Lot 901"] + TITLE, TITLE, TITLE],
     "", "CORNER", ["Example Street"]),
    ("rear lane", [["Site Plan - Proposed", "Road 99", "Lane"] + TITLE, TITLE, TITLE], "", "REAR LANE", ["Road 99", "Lane"]),
    ("lot's own lane", [["Site Plan", "Example Lane"]], "Example Lane", "SINGLE", ["Example Lane"]),
    ("single, abbreviated", [["SITE PLAN", "SAMPLE RD", "Note: crossover to Sample Road by council"]],
     "", "SINGLE", ["Sample Road"]),
    ("site plan on page 2", [["Cover"] + TITLE, ["Site & Facade", "Other Road", "Example Street"] + TITLE, TITLE],
     "", "CORNER", ["Other Road", "Example Street"]),
    ("no labels", [["Floor Plan"], ["Elevations"]], "", "NONE", []),
]


def main():
    fails = 0
    with tempfile.TemporaryDirectory(dir=HERE.parents[2] / "runtime" if (HERE.parents[2] / "runtime").is_dir()
                                     else None) as tmp:
        for name, pages, street, verdict, streets in CASES:
            for compress in (True, False):
                f = Path(tmp) / "plans.pdf"
                f.write_bytes(pdf(pages, compress))
                r = site_streets.analyse(f, street)
                ok = r["verdict"] == verdict and all(s in r["streets"] for s in streets)
                fails += not ok
                print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if compress else ' (uncompressed)'}: "
                      f"{r['verdict']} page {r['site_page']} {r['streets']}")
    good = ["Left Hand Side", "Right Hand Side", "Rear Lane", "Via Sample Road", "Via Example Lane", "Via Lane",
            "Via Road 99", "Via O'Brien Street"]
    bad = ["LHS", "left", "Via", "Via <street>", "Access via rear Lane", "via Sample Road", "Left hand side"]
    for v in good + bad:
        ok = bool(GARAGE_RE.fullmatch(v)) == (v in good)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  garage side {v!r}: {'taken' if v in good else 'refused'}")
    print("\nPASS" if not fails else f"\nFAIL - {fails} case(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
