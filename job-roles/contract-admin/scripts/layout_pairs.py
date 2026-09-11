"""Which left-column label sits level with which right-column wording, from a Word measurement.

    python layout_pairs.py <measure.json>            # print the pair map
    python layout_pairs.py <measure.json> --json      # as JSON

The Sydney inclusions body is one table row with two independent cells (see
word_layout.ps1). This module turns a `measure` JSON of the BLANK template
(word_layout.ps1 -Mode measure) into the structural pair map the layout pass
keeps: every non-empty left paragraph that has a right-column partner, paired
with the first line of that partner's item (an item is a run of non-empty
right paragraphs between blanks). Headings on the left have no partner and are
not paired; sub-headings on the right ("Living Room", "Single Storey Designs",
the three package headings) have no label and are not paired either.

The blank itself is only approximately level (the template's typist padded by
eye, and the upgraded section's first paragraph has 1.15 line spacing), so the
match is nearest-within-9.5pt AND monotonic: a partner is the closest
group-first right paragraph on the same page that is later than the previous
label's partner. On the 19.08.2026 NMA blank every one of the 141 labels
resolves that way except the section-18 area labels (handled explicitly by
edit_inclusions.py) and the red editor note.
"""
import json
import re
import sys

TOL = 9.5  # pt - well under one line (13.3), so a label can only take its own row


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def blank(p):
    return not norm(p["text"])


def group_firsts(R):
    """Right paragraphs that start an item: non-empty, preceded by a blank (or first)."""
    return [r for r in R if not blank(r) and (r["i"] == 0 or blank(R[r["i"] - 1]))]


def pairs_from_measure(measure, tol=TOL):
    L, R = measure["left"], measure["right"]
    firsts = group_firsts(R)
    out, used, last = [], set(), -1
    for l in L:
        if blank(l):
            continue
        cands = [r for r in firsts
                 if r["page"] == l["page"] and abs(r["top"] - l["top"]) <= tol
                 and r["i"] > last and r["i"] not in used]
        if not cands:
            out.append({"left_i": l["i"], "left": norm(l["text"]), "right_i": None, "right": None})
            continue
        r = min(cands, key=lambda r: abs(r["top"] - l["top"]))
        used.add(r["i"])
        last = r["i"]
        out.append({"left_i": l["i"], "left": norm(l["text"]), "right_i": r["i"],
                    "right": norm(r["text"]), "delta": round(r["top"] - l["top"], 2)})
    return out


def headings(measure, names=("INTERNAL TURNKEY PACKAGE", "EXTERNAL TURNKEY PACKAGE", "UPGRADED INCLUSIONS")):
    """Right-column paragraphs that must start a page, with their index."""
    return [{"right_i": r["i"], "right": norm(r["text"])}
            for r in measure["right"] if norm(r["text"]) in names]


def ordinal(paras, idx, key=lambda p: norm(p["text"])):
    """1-based count of paragraphs up to idx with the same normalised text (for text+ordinal lookups)."""
    want = key(paras[idx])
    return sum(1 for p in paras[: idx + 1] if key(p) == want)


def main():
    path = sys.argv[1]
    measure = json.load(open(path, encoding="utf-8"))
    pairs = pairs_from_measure(measure)
    if "--json" in sys.argv:
        print(json.dumps({"pairs": pairs, "headings": headings(measure)}, indent=1, ensure_ascii=False))
        return 0
    paired = [p for p in pairs if p["right_i"] is not None]
    print(f"{len(pairs)} labels, {len(paired)} paired, {len(pairs) - len(paired)} without partner")
    for p in pairs:
        r = f"{p['right_i']:4d} {p['right'][:60]!r}  ({p['delta']:+.1f})" if p["right_i"] is not None else "-"
        print(f"{p['left_i']:4d} {p['left'][:32]!r:36} -> {r}")
    print("\nheadings:", headings(measure))
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
