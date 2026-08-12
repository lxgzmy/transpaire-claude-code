"""Check fill_inclusions.py still reproduces the house convention, per template family.

    python regress_inclusions.py

For each family it reads the page-1 field indents out of every completed job on
the drive, takes the convention to be the indent most of those jobs agree on,
then fills the blank template and checks the filler produces exactly that.

Measuring against the convention rather than against each individual document is
deliberate. These are hand-typed contracts: one Holmview job indents every field
one to three spaces wider than its four neighbours, and one differs on SUBURB
alone. Failing on those would leave the check permanently red, and a check that
is always red gets ignored. Jobs that disagree with their own family are listed
as variance, and only a filler that disagrees with the convention fails.

Exit code 0 = the filler matches every family's convention.
"""
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACTS = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS")

# family -> where its completed jobs live, and the blank the filler must reproduce
SUITES = [
    ("gunnedah", Path(r"Z:\PROJECTS\TAMWORTH"), "*PIONEER CLOSE*",
     CONTRACTS / "REGION - GUNNEDAH, NSW"
     / "Gunnedah INTEGRITY Range + Turnkey Inclusions - NCC 2022 - V4 Transpire 08.11.24.docx"),
    ("seq", Path(r"Z:\PROJECTS\SEQ"), "*ZHANG STREET*",
     CONTRACTS / "REGION - SEQ" / "INCLUSIONS" / "INVESTOR & FIRST HOME OWNER"
     / "1. Sth East Qld ESSENTIALS Range Turnkey Inclusions - Transpire - NCC 2022 - 01.10.23.docx"),
]

LABELS = ["Lot No. :", "HOUSE TYPE :", "STREET :", "HOUSE SIZE :", "SUBURB :",
          "HOUSE FA\u00c7ADE :", "ESTATE :", "GARAGE SIDE :", "PRICE :"]
KEY_OF = {"Lot No. :": "lot_no", "HOUSE TYPE :": "house_type", "STREET :": "street",
          "HOUSE SIZE :": "house_size", "SUBURB :": "suburb",
          "HOUSE FA\u00c7ADE :": "facade", "ESTATE :": "estate",
          "GARAGE SIDE :": "garage_side", "PRICE :": "price"}

# The child's stdout defaults to the console codepage, which mangles the m² in
# HOUSE SIZE before we can compare it.
UTF8 = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", env=UTF8)


def page1_cells(docx):
    """The page-1 table cells, e.g. 'HOUSE TYPE :      Avoca 180'."""
    out = run(HERE / "docx_text.py", docx).stdout
    rows = [l.split("] ", 1)[1] for l in out.splitlines() if re.match(r"^000[2-6] \[TR\]", l)]
    return [c.strip() for row in rows for c in row.split("~")]


def read_fields(docx):
    """{label: (indent, value)} for every page-1 field present."""
    found = {}
    for cell in page1_cells(docx):
        for label in LABELS:
            if not cell.startswith(label):
                continue
            rest = cell[len(label):]
            found[label] = (len(rest) - len(rest.lstrip(" ")), rest.strip())
    return found


def completed_jobs(root, pattern):
    for job in sorted(p for p in root.glob(pattern) if p.is_dir()):
        doc = next((job / "CONTRACT" / "CONTRACT DOCUMENTATION").glob("INCLUSIONS*.docx"), None)
        if doc:
            yield job.name, doc


def run_suite(family, root, pattern, blank):
    print(f"\n== {family} ==")
    jobs = list(completed_jobs(root, pattern))
    if not jobs:
        print(f"   FAIL - no completed jobs matched {pattern} under {root}")
        return 1

    per_job = {name: read_fields(doc) for name, doc in jobs}

    # The convention: the indent most completed jobs agree on, per field - kept as
    # a SET, because a genuine tie means there is no convention to match. Gunnedah
    # PRICE splits two jobs to two between five and six spaces; failing the filler
    # for picking either side would be inventing a rule the documents do not have.
    convention = {}
    for label in LABELS:
        seen = [f[label][0] for f in per_job.values() if label in f]
        if not seen:
            continue
        counts = Counter(seen)
        top = max(counts.values())
        convention[label] = {n for n, c in counts.items() if c == top}

    for name, fields in per_job.items():
        odd = [l.split(":")[0].strip() for l in LABELS
               if l in fields and l in convention and fields[l][0] not in convention[l]]
        note = f"variance on {', '.join(odd)}" if odd else "matches convention"
        print(f"   {name[:34]:36s} {note}")

    # Fill the blank with one job's values and see where the filler puts them.
    sample_name, sample_doc = jobs[0]
    vals = {KEY_OF[l]: v for l, (_, v) in read_fields(sample_doc).items()}
    vals["price"] = vals.get("price", "").lstrip("$")
    for k in ("owner_1", "owner_2", "site_address"):
        vals.setdefault(k, "")
    vals.setdefault("builders_rep", "Michael CRONK")

    # Stage on Z:, never the system temp dir - that is on C: (repo CLAUDE.md).
    tmp = HERE.parent.parent.parent / "runtime" / "contract-admin" / "reports" / "_regress"
    tmp.mkdir(parents=True, exist_ok=True)
    jf, out = tmp / "job.json", tmp / "filled.docx"
    jf.write_text(__import__("json").dumps(vals, ensure_ascii=False), encoding="utf-8")
    r = run(HERE / "fill_inclusions.py", "--template", blank, "--job", jf, "--out", out)
    if not out.exists():
        print(f"   FAIL - fill did not run: {r.stderr.strip()[:200]}")
        return 1

    got = {l: n for l, (n, _) in read_fields(out).items()}
    bad = [(l, convention[l], got.get(l)) for l in LABELS
           if l in convention and got.get(l) not in convention[l]]
    out.unlink(missing_ok=True)
    jf.unlink(missing_ok=True)

    if bad:
        print("   FAIL - filler disagrees with the convention:")
        for label, want, have in bad:
            allowed = " or ".join(str(n) for n in sorted(want))
            print(f"      {label:<16} convention {allowed}, filler {have}")
        return 1
    print(f"   PASS - filler matches the convention on all {len(convention)} fields")
    return 0


def main():
    failures = sum(run_suite(*s) for s in SUITES)
    print(f"\n{'PASS' if not failures else f'FAIL - {failures} family(ies) wrong'}")
    return 1 if failures else 0


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
