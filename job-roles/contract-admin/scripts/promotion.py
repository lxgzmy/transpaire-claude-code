r"""Turn a SEQ promotion inclusions document into `upgrades.items` for edit_inclusions.py. Stdlib only.

    python promotion.py --doc "<SALES INCLUSIONS - SEPTEMBER PROMOTION 2023.docx>" [--marketer MWC]
                        [--request "MWC Exclusive Upgrade Pack - September Promotion"] [--json]

A request naming a promotion ("MWC Exclusive Upgrade Pack - September
Promotion") has its whole PROMOTIONAL UPGRADES block copied into the job's
inclusions (contract admin review of job 26059, 28 Oct 2026, CD-9.12). The
promotion document is the same two-column table as the inclusions: labels on
the left, wording groups on the right, one blank line between groups. Label k
pairs with group k.

Where each label goes, from the review:
  Benchtops               replaces the blank's Benchtops wording. A label
                          "Benchtops - MWC ONLY" is the MWC version: an MWC
                          job takes it, any other marketer the plain one.
  Plumbing, Electrical    added under the blank's existing label (no second label)
  Hinges & Drawer Runners, Handles, Shower Screens, Mirrors
                          new labels, before Plumbing
  Oven, Cooktop, Rangehood
                          new labels, after Plumbing (before Electrical)
  anything else           a new label at its Standard Variation place,
                          flagged medium for a person to confirm

The items come out in that order. Request lines that change a promotion line
(an induction cooktop, black tapware) follow them in the job JSON with mode
"replace" or `replaces`, so they win.
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HEADING = "PROMOTIONAL UPGRADES"
ADD_UNDER = ("Plumbing", "Electrical")
BEFORE_PLUMBING = ("Hinges & Drawer Runners", "Handles", "Shower Screens", "Mirrors")
BEFORE_ELECTRICAL = ("Oven", "Cooktop", "Rangehood")
VARIANT = re.compile(r"^(?P<label>.+?)\s*[–—-]\s*(?P<who>[A-Za-z &]+?)\s+ONLY$", re.I)


def norm(t):
    return re.sub(r"\s+", " ", (t or "").replace(" ", " ")).strip()


def ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def columns(path):
    """(left paragraphs, right paragraphs) of the table row holding PROMOTIONAL UPGRADES."""
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    for tr in root.iter(W + "tr"):
        cells = tr.findall(W + "tc")
        if len(cells) < 2:
            continue
        right = [norm(ptext(p)) for p in cells[-1].findall(W + "p")]
        if HEADING in right:
            return [norm(ptext(p)) for p in cells[0].findall(W + "p")], right
    raise SystemExit(f"ERROR: no {HEADING!r} column in {path}")


def groups(lines):
    out, cur = [], []
    for t in lines:
        if t:
            cur.append(t)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def read(path):
    """[(label, [wording lines])] in document order."""
    left, right = columns(path)
    labels = [t for t in left if t]
    words = groups(right[right.index(HEADING) + 1:])
    if len(labels) != len(words):
        raise SystemExit(f"ERROR: {len(labels)} labels but {len(words)} wording groups in {Path(path).name} - "
                         f"the promotion document's layout has changed; a person maps it")
    return list(zip(labels, words))


def items(path, marketer="", request=""):
    pairs = read(path)
    who = norm(marketer).upper()
    chosen = {}
    for label, lines in pairs:
        m = VARIANT.match(label)
        base = norm(m.group("label")) if m else label
        if m and norm(m.group("who")).upper() != who:
            continue          # another marketer's version
        if m or base not in chosen:
            chosen[base] = lines   # a marketer's own version wins over the plain one
    src = f"{Path(path).name}" + (f" ({who} version where it has one)" if who else "")
    out = []
    for label, lines in chosen.items():
        it = {"category": label, "wording": "\n".join(lines), "request": request or src,
              "variation_row": None, "confidence": "high", "note": f"promotion: {src}"}
        if label == "Benchtops":
            it["mode"] = "replace"
        elif label in ADD_UNDER:
            it["mode"] = "add"
        elif label in BEFORE_PLUMBING:
            it["before"] = "Plumbing"
        elif label in BEFORE_ELECTRICAL:
            it["before"] = "Electrical"
        else:
            it["confidence"] = "medium"
            it["note"] += " - label with no placement rule; Standard Variation order, confirm"
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--marketer", default="")
    ap.add_argument("--request", default="")
    ap.add_argument("--json", action="store_true", help="print the items as JSON for the job's upgrades block")
    a = ap.parse_args()
    its = items(a.doc, a.marketer, a.request)
    if a.json:
        print(json.dumps(its, indent=1, ensure_ascii=False))
        return 0
    for it in its:
        where = it.get("mode") or (f"before {it['before']}" if it.get("before") else "new label")
        print(f"{it['category']:26} [{where}]")
        for l in it["wording"].split("\n"):
            print(f"    {l}")
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
