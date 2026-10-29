"""Check edit_inclusions.py on the live SEQ MWC blank (CD-9.12, the 26059 review of 28 Oct 2026).

    python test_seq_upgrades.py

Fills the blank with fixtures/inclusions-upgrades-seq/*.json (synthetic), runs
the editor and asserts what the review asked for: the September promotion in
(MWC benchtops, labels placed before Plumbing / Electrical), the request lines
replacing what they change (induction cooktop over the gas one, black tapware
over chrome), the label order of the team's finished 26059 document, and no
awning windows. XML level only - the Word layout pass runs in draft_contract.py.
Needs the blank's measurement in runtime\\contract-admin\\state\\layout\\ (the
first draft_contract.py run against the blank makes it). Exit 0 = pass.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))
import edit_inclusions as ed  # noqa: E402

BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SEQ\INCLUSIONS\INVESTOR & FIRST HOME OWNER"
             r"\3. Sth East Qld ESSENTIALS Range Turnkey Inclusions - MWC - NCC 2022 - 01.10.2023.docx")
FIXTURES = HERE.parent / "fixtures" / "inclusions-upgrades-seq"
STATE = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "layout"
OUT = HERE.parents[2] / "runtime" / "contract-admin" / "reports" / "_regress_edit_seq"

LABELS = ["Roof Covering", "Entrance Door", "Internal Doors", "Glazing", "Benchtops", "Tiling Walls", "Wardrobes",
          "Hinges & Drawer Runners", "Handles", "Shower Screens", "Mirrors", "Plumbing", "Oven", "Cooktop",
          "Rangehood", "Electrical", "Timber Flooring", "Carpet", "Air-Conditioning", "Window Furnishings"]


def run(*args):
    return subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    measure = STATE / f"{BLANK.stem}.measure.json"
    if not measure.exists():
        print(f"FAIL - no blank measurement at {measure}")
        return 1
    failures = 0
    for fx in sorted(FIXTURES.glob("*.json")):
        filled, edited = OUT / f"{fx.stem}.filled.docx", OUT / f"{fx.stem}.edited.docx"
        edited.unlink(missing_ok=True)
        run(HERE / "fill_inclusions.py", "--template", BLANK, "--job", fx, "--out", filled)
        r = run(HERE / "edit_inclusions.py", "--docx", filled, "--job", fx, "--blank", BLANK, "--blank-measure",
                measure, "--out", edited, "--report", OUT / f"{fx.stem}.edit.txt", "--plan", OUT / f"{fx.stem}.plan.json")
        if r.returncode != 0 or not edited.exists():
            print(f"== {fx.stem}: FAIL - editor: {(r.stdout + r.stderr)[-500:]}")
            failures += 1
            continue
        ed.use_family("seq")
        cols = ed.Columns(ed.read_xml(edited))
        labels, groups = ed.upgraded_section(cols)
        names = [ed.norm(ed.ptext(cols.left[i])) for i in labels]
        words = {n: [ed.norm(ed.ptext(cols.right[k])) for k in range(s, e)] for n, (s, e) in zip(names, groups)}
        allw = " | ".join(" | ".join(v) for v in words.values())
        problems = []
        checks = [
            ("label order as the team's 26059 document", names == LABELS),
            ("MWC benchtops (40mm, waterfall)", words.get("Benchtops", [""])[0].startswith("40mm")
             and any("waterfall" in l for l in words.get("Benchtops", []))),
            ("induction cooktop replaces the gas one and its notes",
             words.get("Cooktop") == ["Technika Venini GECE9004 900mm electric cooktop"]),
            ("chrome Posh Bristol rail swapped for the black Domaine", "Bristol" not in allw and "Domaine" in allw),
            ("chrome Mizu Soothe mixer swapped for Mizu Drift", "Soothe" not in allw and "Mizu Drift MK2" in allw),
            ("pendant lights under Electrical", any("Beacon Marcel" in l for l in words.get("Electrical", []))),
            ("ducted air replaces the split systems", words.get("Air-Conditioning", [""])[0]
             == "Reverse cycle ducted air-conditioning system." and "split system" not in allw),
            ("blinds and screens by owner", words.get("Window Furnishings")
             == ["Blinds and insect screens to be supplied and installed By Owner after handover"]),
            ("no awning windows written", "awning" not in allw.lower()),
            ("double vanity note excludes tapware", "standard range excluding tapware" in allw),
        ]
        for name, ok in checks:
            if not ok:
                problems.append(name)
        print(f"== {fx.stem}: " + ("PASS" if not problems else "FAIL - " + "; ".join(problems)))
        failures += bool(problems)
    print("\nPASS" if not failures else f"\nFAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
