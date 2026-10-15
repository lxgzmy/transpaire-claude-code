r"""Unit checks for gate_inclusions.check_section18 (issue #57), synthetic measurements only.

    python test_gate_section18.py

Same page as the NBN wording: one blank line between them passes; none, or a ten-line gap,
fails. A heading left at a page foot with its label on the next page fails. A heading on the
next page passes only when the kept area wording could not fit on the NBN wording's page: it
starts the next page too, no more than the editor's 3 blank lines follow the NBN wording on
its page, and the heading starts its page (15 Oct 2026 - the old "more than 4 lines free"
rule failed a document Word had laid out correctly with 5 free). Measurements without the
blank count still get the old rule.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_inclusions as g  # noqa: E402

LINE = g.TEXT_LINE_PT
PAGE = {"page_top": 72.0, "usable": 697.9}   # foot of the text area at 769.9 pt


def verdict(s18, page=PAGE):
    out = []
    ok = g.check_section18(dict(page, section18=s18), out)
    return ok, out[-1]


def same_page(gap_lines):
    return {"heading_page": 7, "heading_top": 500.0 + (gap_lines + 1) * LINE, "label_page": 7,
            "note_page": 7, "note_last_top": 500.0}


def new_page(blanks=3, starts=True, wording_page=8):
    return {"heading_page": 8, "heading_top": 112.0, "label_page": 8, "heading_starts_page": starts,
            "note_page": 7, "note_last_top": 683.25, "blanks_on_note_page": blanks,
            "wording": "Connection of Recycled Water to one (1)", "wording_page": wording_page}


CASES = [
    ("one blank line below the NBN wording", same_page(1.0), True, "1.0 blank line"),
    ("no blank line", same_page(0.0), False, "want one"),
    ("a ten-line gap", same_page(10.0), False, "want one"),
    ("heading stranded at a page foot", dict(same_page(1.0), label_page=8), False, "stranded"),
    ("new page: wording could not fit (3 blanks, 5 lines free)", new_page(), True, "heading starts a new page"),
    ("new page pushed by a gap (7 blanks)", new_page(blanks=7), False, "a gap pushed the heading"),
    ("new page, heading not at its top", new_page(starts=False), False, "does not start it"),
    ("new page, wording left behind", new_page(wording_page=7), False, "its area wording starts page 7"),
    ("old measurement, 3 lines free", {k: v for k, v in new_page().items()
                                       if k not in ("blanks_on_note_page", "heading_starts_page", "wording", "wording_page")}
     | {"note_last_top": 769.9 - 3 * LINE}, True, "heading starts a new page"),
    ("old measurement, 9 lines free", {k: v for k, v in new_page().items()
                                       if k not in ("blanks_on_note_page", "heading_starts_page", "wording", "wording_page")}
     | {"note_last_top": 769.9 - 9 * LINE}, False, "lines are free"),
    ("not measured", None, True, "not measured"),
]


def main():
    fails = 0
    for name, s18, want, text in CASES:
        ok, line = verdict(s18)
        good = ok is want and text in line
        fails += not good
        print(f"  {'ok  ' if good else 'FAIL'} {name}: {line}")
    print("PASS: section 18 gate" if not fails else f"FAIL: {fails} case(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
