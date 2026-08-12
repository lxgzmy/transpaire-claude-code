"""Everything the contract workflow asks about a job, in one call.

    python probe_job.py "lot 13 Zhang Street"
    python probe_job.py 144 --region TAMWORTH

Answers the six questions step 2 of the new-contract workflow asks every time,
which otherwise cost six separate searches:

  1. Where is the job folder? (all regions, and the CANCELLED / COMPLETED levels
     - most jobs are not in the live region folder)
  2. Is there already a contract set in it? -> amendment, not a first draft (CD-7.6)
  3. Is there a CANCELLED job at the same lot? -> the twin that is easy to grab
  4. Which template family does its region use?
  5. Where are the plans?
  6. What do the plans say - house type, facade, size, council?

Read-only. Prints a report and touches nothing.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = Path(r"Z:\PROJECTS")

# Region -> inclusions template family. There is no Tamworth template folder:
# Tamworth and Gunnedah jobs share the Gunnedah INTEGRITY document, and the NSW
# build contract is filed under Sydney. That mapping is the main trap here.
REGION_FAMILY = {
    "TAMWORTH": "gunnedah", "GUNNEDAH": "gunnedah",
    "SYDNEY": "sydney", "SEQ": "seq", "CUDGEN": "seq",
}

UTF8 = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def find_jobs(term):
    """Every job folder matching, at any lifecycle level, with its region."""
    words = [w for w in re.split(r"[\s,]+", term.strip().lower()) if w]
    hits = []
    for path in PROJECTS.glob("*/*"):
        if not path.is_dir():
            continue
        for sub in [path] + ([p for p in path.glob("*") if p.is_dir()]
                             if path.name in ("CANCELLED", "COMPLETED CONTRACTS",
                                              "ARCHIVE-HANDED OVER") else []):
            name = sub.name.lower()
            if all(w in name for w in words):
                rel = sub.relative_to(PROJECTS)
                hits.append((rel.parts[0], sub, "CANCELLED" in str(rel).upper()))
    return sorted(set(hits), key=lambda h: (h[2], str(h[1])))


def lot_of(name):
    m = re.search(r"\bLOT\s+(\d+)", name.upper())
    return m.group(1) if m else None


def contract_docs(job):
    d = job / "CONTRACT" / "CONTRACT DOCUMENTATION"
    if not d.is_dir():
        return None, []
    live = sorted(p.name for p in d.glob("*") if p.is_file()
                  and p.suffix.lower() in (".docx", ".pdf"))
    return d, live


def plans_text(job):
    d = job / "CONTRACT" / "CONTRACT DOCUMENTATION"
    pdf = next(d.glob("PLANS*.pdf"), None) if d.is_dir() else None
    if not pdf:
        return None, ""
    out = subprocess.run([sys.executable, str(HERE / "pdf_text.py"), str(pdf)],
                         capture_output=True, text=True, encoding="utf-8", env=UTF8)
    return pdf, out.stdout


def facts_from_plans(text):
    """The handful of values the email never carries (CD-2.7, CD-2.9)."""
    flat = re.sub(r"\s+", " ", text)
    facts = {}
    m = re.search(r"@A3\s+(.+?)\s+Lot\s", flat)
    if m:
        facts["design / facade (title block)"] = m.group(1).strip()
    m = re.search(r"local\s+authority\s+(.+?)\s+N?\s*A1\.", flat)
    if m:
        facts["local authority"] = m.group(1).strip()
    m = re.search(r"Total\s+Areas(.+?)m\s*.?\s*\d", flat)
    if m:
        nums = re.findall(r"\d+\.\d\d", m.group(1))
        # The last figure in the table IS the total, so summing every number
        # double-counts it. Sum the components and check they equal the stated
        # total - if they do not, say so rather than report a number (CD "never
        # guess a contract value").
        if len(nums) >= 2:
            *parts, total = nums
            summed = sum(float(n) for n in parts)
            if abs(summed - float(total)) < 0.02:
                facts["house size"] = f"{total} m2   (= {' + '.join(parts)})"
            else:
                facts["house size"] = (f"UNCLEAR - {' + '.join(parts)} = {summed:.2f} "
                                       f"but the table says {total}; read the plan")
        elif nums:
            facts["house size"] = f"UNCLEAR - only one figure found ({nums[0]}); read the plan"
    return facts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("term", help='e.g. "lot 13 Zhang Street" or "144 pioneer"')
    ap.add_argument("--region", help="narrow to one region folder")
    args = ap.parse_args()

    hits = find_jobs(args.term)
    if args.region:
        hits = [h for h in hits if h[0].upper() == args.region.upper()]
    if not hits:
        print(f"No job folder matches {args.term!r}.")
        print("Try fewer words - folder names vary (brackets, extra spaces, estate names).")
        return 1

    live = [h for h in hits if not h[2]]
    cancelled = [h for h in hits if h[2]]

    print(f"=== {len(live)} live, {len(cancelled)} cancelled match {args.term!r} ===\n")

    for region, job, _ in live:
        family = REGION_FAMILY.get(region.upper(), "UNKNOWN")
        print(f"JOB      {job}")
        print(f"region   {region}   ->  template family: {family}")
        if family == "UNKNOWN":
            print("         !! no template family known for this region - do not fill")

        d, docs = contract_docs(job)
        if not d:
            print("contract no CONTRACT DOCUMENTATION folder - first draft")
        elif not docs:
            print("contract folder exists but is empty - first draft")
        else:
            print(f"contract !! {len(docs)} document(s) ALREADY THERE - amendment, not a "
                  f"first draft (CD-7.6)")
            for n in docs[:8]:
                print(f"           {n}")
            ss = d / "SS"
            if ss.is_dir():
                n = len(list(ss.glob("*")))
                print(f"           SS\\ holds {n} superseded file(s) - already revised")

        pdf, text = plans_text(job)
        if pdf:
            print(f"plans    {pdf.name}")
            for k, v in facts_from_plans(text).items():
                print(f"           {k:<28} {v}")
            print("           garage side                  NOT IN TEXT - read the site plan (JD-9.5)")
        else:
            print("plans    none in CONTRACT DOCUMENTATION - house size/garage side unavailable")
        print()

    for region, job, _ in cancelled:
        lot = lot_of(job.name)
        clash = [j for r, j, c in live if not c and lot_of(j.name) == lot]
        mark = "  <-- SAME LOT AS A LIVE JOB" if clash else ""
        print(f"CANCELLED {job}{mark}")
    if cancelled:
        print("\nA cancelled job at the same lot is easy to mistake for the live one.")
        print("Check the purchaser name on the documents, not just the lot number.")
    return 0


# This console is cp1252; plans text carries m² and degree signs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
