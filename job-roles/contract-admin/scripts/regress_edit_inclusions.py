"""Check edit_inclusions.py against the synthetic upgrades fixtures on the live Sydney blank.

    python regress_edit_inclusions.py            # XML-level checks, a few seconds
    python regress_edit_inclusions.py --layout   # also run the Word layout pass + gate (~5 min per fixture)
    python regress_edit_inclusions.py --layout --only other-area-double-storey

For each fixture in fixtures/inclusions-upgrades/: fill the blank, run the
editor, then assert what the NSW inclusions feedback sheet 9.9 asked for -
one regional pair left, notes gone, black throughout, items placed as the
Standard Variation order says, the air-conditioning item kept when not
requested, the Bathroom 2 wording when it is on the ground floor. Exit 0 =
every fixture passes.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import os
# abspath, not resolve(): resolve() turns the mapped Z: into its UNC path, and Word
# opens UNC files in Protected View (Documents.Open returns nothing)
HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))
import edit_inclusions as ed  # noqa: E402
from fill_inclusions import editor_notes_left  # noqa: E402

BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SYDNEY\INCLUSIONS"
             r"\1. Sydney INTEGRITY RANGE + Turnkey Inclusions - NCC 2022 - STANDARD 19.08.2026 NMA.docx")
FIXTURES = HERE.parent / "fixtures" / "inclusions-upgrades"
STATE = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "layout"
OUT = HERE.parents[2] / "runtime" / "contract-admin" / "reports" / "_regress_edit"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def labels_and_groups(docx):
    cols = ed.Columns(ed.read_xml(docx))
    labels, groups = ed.upgraded_section(cols)
    return cols, [ed.norm(ed.ptext(cols.left[i])) for i in labels], \
        [[ed.norm(ed.ptext(cols.right[k])) for k in range(s, e)] for s, e in groups]


def check(name, cond, problems):
    if not cond:
        problems.append(name)
    return cond


def regional_state(cols):
    left = [l for l in ed.REGIONAL_LABELS if any(ed.norm(ed.ptext(p)) == l for p in cols.left)]
    right = [w for w in ed.REGIONAL_WORDING if any(w.lower() in ed.ptext(p).lower() for p in cols.right)]
    return left, right


def main():
    layout = "--layout" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    OUT.mkdir(parents=True, exist_ok=True)
    # the driver caches the blank's measurement under the template's own name
    blank_measure = STATE / f"{BLANK.stem}.measure.json"
    if not blank_measure.exists():
        print(f"FAIL - no blank measurement at {blank_measure}; run word_layout.ps1 -Mode measure on the blank first "
              f"(draft_contract.py does this itself on the first run against a blank)")
        return 1
    failures = 0
    for fx in sorted(FIXTURES.glob("*.json")):
        if only and fx.stem != only:
            continue
        job = json.loads(fx.read_text(encoding="utf-8"))
        up = job["upgrades"]
        filled, edited = OUT / f"{fx.stem}.filled.docx", OUT / f"{fx.stem}.edited.docx"
        report, plan = OUT / f"{fx.stem}.edit.txt", OUT / f"{fx.stem}.plan.json"
        problems = []
        r = run(HERE / "fill_inclusions.py", "--template", BLANK, "--job", fx, "--out", filled)
        if not filled.exists():
            print(f"== {fx.stem}: FAIL - fill did not run: {r.stderr[:200]}")
            failures += 1
            continue
        r = run(HERE / "edit_inclusions.py", "--docx", filled, "--job", fx, "--blank", BLANK,
                "--blank-measure", blank_measure, "--out", edited, "--report", report, "--plan", plan)
        check("editor exit 0", r.returncode == 0 and edited.exists(), problems)
        if not edited.exists():
            print(f"== {fx.stem}: FAIL - {problems}\n{r.stdout[-600:]}{r.stderr[-400:]}")
            failures += 1
            continue
        text = report.read_text(encoding="utf-8")
        cols, labels, groups = labels_and_groups(edited)
        xml = cols.xml
        left, right = regional_state(cols)
        want_label, want_word = ed.AREAS[up["area"]]
        check("one regional label, the right one", left == [want_label], problems)
        check("one regional wording, the right one", right == [want_word], problems)
        check("all runs black", not (set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', xml)) - {"000000"}), problems)
        check("no highlight", "<w:highlight" not in xml, problems)
        check("no editor notes", not editor_notes_left(xml), problems)
        check("labels == groups", len(labels) == len(groups), problems)
        check("air con red note gone", ed.AIRCON_NOTE not in labels, problems)
        ac = groups[labels.index(ed.AIRCON_LABEL)] if ed.AIRCON_LABEL in labels else []
        if up.get("aircon"):
            check("air con wording replaced", ac and ac[0].startswith(up["aircon"].split("\n")[0][:30]), problems)
        else:
            check("air con item kept", ac and ac[0].startswith(ed.AIRCON_FIRST), problems)
        rtext = " ".join(ed.ptext(p) for p in cols.right)
        if up.get("bathroom2_ground"):
            check("Bathroom 2 written 3x", rtext.count(ed.BATH2_NEW) == 3, problems)
        else:
            check("no Bathroom 2 wording", ed.BATH2_NEW not in rtext, problems)
        check("bathroom notes gone", not any(n in rtext for n in ed.BATH2_NOTES) and ed.BATH2_INLINE not in rtext, problems)
        for it in up.get("items", []):
            cat = it["category"]
            first = it["wording"].split("\n")[0].strip()
            check(f"item {cat!r} wording present", first in rtext, problems)
            check(f"item {cat!r} reported with confidence", f"[{it.get('confidence', 'low').upper():6}] {cat}" in text, problems)
            if it.get("variation_row") is None:
                check(f"custom item {cat!r} flagged", "not a Standard Variation category" in text
                      or "custom wording" in text, problems)
        # fixture-specific placement rules
        if fx.stem.startswith("other-area"):
            check("Wardrobe Doors before Shelving", labels.index("Wardrobe Doors") + 1 == labels.index("Shelving"), problems)
            bench = groups[labels.index("Benchtops")]
            check("benchtops: one line replaced, Waterfall kept", len(bench) == 2 and bench[1].startswith("Waterfall"), problems)
        if fx.stem.startswith("box-hill"):
            check("Cabinetry group grew to 3 lines", len(groups[labels.index("Cabinetry")]) == 3, problems)
        if fx.stem.startswith("north-kellyville"):
            check("custom label appended last", labels[-1] == up["items"][0]["category"], problems)
        if layout:
            aligned = OUT / f"{fx.stem}.aligned.docx"
            aligned.write_bytes(edited.read_bytes())
            rep = OUT / f"{fx.stem}.align.json"
            ps = subprocess.run(["pwsh", "-NoProfile", "-File", str(HERE / "word_layout.ps1"), "-Mode", "align",
                                 "-Docx", str(aligned), "-Plan", str(plan), "-Out", str(rep)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if ps.returncode != 0 or not rep.exists():
                print(f"   layout pass failed (exit {ps.returncode}):")
                print("   " + (ps.stderr or ps.stdout)[-800:].replace(chr(10), chr(10) + "   "))
            check("layout pass ran", ps.returncode == 0 and rep.exists(), problems)
            if rep.exists():
                g = run(HERE / "gate_inclusions.py", "--docx", aligned, "--measure", rep, "--plan", plan,
                        "--report", OUT / f"{fx.stem}.gate.txt")
                check("gate PASS", g.returncode == 0, problems)
                if g.returncode:
                    print(g.stdout[-1500:])
        status = "PASS" if not problems else "FAIL - " + "; ".join(problems)
        print(f"== {fx.stem}: {status}")
        failures += bool(problems)
    print(f"\n{'PASS' if not failures else f'FAIL - {failures} fixture(s)'}")
    return 1 if failures else 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    raise SystemExit(main())
