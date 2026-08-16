"""Check fill_prelim.py still reproduces the completed preliminary agreements.

    python regress_prelim.py

Strict suite: for each completed single-client Tamworth agreement (jobs 26036
and 26045 - the only two whose editors made no edits beyond the fill itself),
read the filled values out of the real document, fill the current blank with
them, and require the two documents' full visible text to be IDENTICAL. Run
boundaries and formatting are ignored; every character of text counts.

Structural suite: a synthetic two-client fill must land both names in the
client row (keeping the template's "&"), both signature lines and the fee -
the two-client references disagree on cosmetic spacing, so only structure is
asserted there.

Exit code 0 = all suites pass.
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SYDNEY\CONTRACT"
             r"\NSW PRELIMINARY AGREEMENT 2024.docx")
# Resolved by job number at runtime - completed filenames carry client
# surnames, which stay out of this repo.
TAMWORTH = Path(r"Z:\PROJECTS\TAMWORTH")
REF_JOBS = [("26036 lot 144", "26036*"), ("26045 lot 143", "26045*")]


def ref_doc(pattern):
    for job in TAMWORTH.glob(pattern):
        hit = next((job / "CONTRACT" / "CONTRACT DOCUMENTATION")
                   .glob("PRELIMINARY AGREEMENT*.docx"), None)
        if hit:
            return hit
    return None

RESI_LABEL = "(Current Residential Address)"
CONS_LABEL = "(For Construction Address)"


def text(path):
    """All visible text, run boundaries ignored."""
    import html
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    return html.unescape("".join(
        m.group(1) for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", xml, re.S)))


def values_from(real):
    """Read the fill values back out of a completed single-client agreement."""
    t = text(real)
    owner = re.search(r"Constructions”\)And\s+(.+?)\(“Client”\)", t).group(1).strip()
    resi = re.search(re.escape(RESI_LABEL) + r"\s+(.+?)\(For", t).group(1).strip()
    cons = re.search(re.escape(CONS_LABEL) + r"\s+Lot (.+?)Herein", t).group(1).strip()
    fee = re.search(r"pay Transpire Constructions \$([\d,]+)\.", t).group(1)
    return {"owner_1": owner, "owner_2": "", "residential_address": resi,
            "site_address": cons, "prelim_fee": fee,
            "builders_rep": "Michael CRONK"}


def run_fill(vals, out):
    jf = out.with_name("job.json")
    jf.write_text(json.dumps(vals, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(HERE / "fill_prelim.py"),
                        "--template", str(BLANK), "--job", str(jf),
                        "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    jf.unlink(missing_ok=True)
    return r


def main():
    tmp = HERE.parent.parent.parent / "runtime" / "contract-admin" / "reports" / "_regress"
    tmp.mkdir(parents=True, exist_ok=True)
    failures = 0

    for name, pattern in REF_JOBS:
        real = ref_doc(pattern)
        if not real:
            print(f"FAIL  {name} - no completed agreement found for {pattern}")
            failures += 1
            continue
        out = tmp / "prelim_filled.docx"
        r = run_fill(values_from(real), out)
        if not out.exists():
            print(f"FAIL  {name} - fill did not run: {r.stderr.strip()[:200]}")
            failures += 1
            continue
        got, want = text(out), text(real)
        out.unlink(missing_ok=True)
        if got == want:
            print(f"PASS  {name} - filled blank is text-identical to the real agreement")
        else:
            failures += 1
            i = next((k for k, (a, b) in enumerate(zip(got, want)) if a != b),
                     min(len(got), len(want)))
            print(f"FAIL  {name} - first divergence at char {i}:")
            print(f"      filled: ...{got[max(0, i-40):i+40]!r}")
            print(f"      real  : ...{want[max(0, i-40):i+40]!r}")

    # two-client structural smoke test
    vals = {"owner_1": "Alpha ONE", "owner_2": "Beta TWO",
            "residential_address": "1 Test Street, TESTVILLE NSW 2000",
            "site_address": "9, Example Road, TESTVILLE NSW 2000",
            "prelim_fee": "7,500", "builders_rep": "Michael CRONK"}
    out = tmp / "prelim_two.docx"
    r = run_fill(vals, out)
    if not out.exists():
        print(f"FAIL  two-client smoke - fill did not run: {r.stderr.strip()[:200]}")
        failures += 1
    else:
        t = text(out)
        out.unlink(missing_ok=True)
        checks = [
            ("client row keeps & between the names",
             re.search(r"And Alpha ONE\s*&\s*Beta TWO", t)),
            ("fee replaced", "$7,500." in t and "$30,000." not in t),
            ("owner 1 signing line", "  Alpha ONE" in t),
            ("owner 2 signing line", "  Beta TWO" in t),
            ("builders rep signing line", "   Michael CRONK" in t),
        ]
        bad = [label for label, ok in checks if not ok]
        if bad:
            failures += 1
            print(f"FAIL  two-client smoke - {', '.join(bad)}")
        else:
            print("PASS  two-client smoke - structure holds")

    print("\n" + ("PASS" if not failures else f"FAIL - {failures} suite(s)"))
    return 1 if failures else 0


# This console is cp1252; document text carries curly quotes and dotted leaders.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
