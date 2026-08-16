r"""Run the whole contract-drafting pipeline for one job, timed. Stdlib only.

    python draft_contract.py --job <workdir>/job.json --template "<blank inclusions>"
    python draft_contract.py --job <workdir>/job.json --template "<blank>" --prelim
    python draft_contract.py --job <workdir>/job.json --template "<blank>" --real-dir "<job's CONTRACT DOCUMENTATION>"

One command instead of six: anchor check, fill, blank-vs-filled diff, optional
preliminary agreement (same three stages), complete-PDF previews in a single
Word launch, and - when --real-dir points at the job's CONTRACT DOCUMENTATION -
a REAL_ PDF export of the completed documents plus a word-level diff against
each, for the flip-comparison the testing protocol requires.

NOTHING here weakens the gates. The anchor check still aborts the run, the
diffs are still written and must still be read, the preview is still produced
for the mandatory approval, and this script only ever writes into the workdir -
it refuses to run with a workdir under Z:\PROJECTS, and --real-dir is read-only
(the real documents are opened read-only by Word and exported INTO the
workdir). Saving into a job folder remains step 9 of the skill: a human
approval and a deliberate copy, never this script.

Each stage is timed and the summary lands in <workdir>/timings.txt, so a slow
run shows exactly where the time went (in practice: Word start-up - which is
why every PDF in the run is exported through one Word instance).

Filenames follow CD-7.2: <DOCTYPE>_LOT <lot>_<SUBURB>_<SURNAMES>.docx, where
SUBURB drops the trailing state token and SURNAMES are each owner's last name,
de-duplicated in order, joined by "&" (verified against completed jobs 26004 -
two distinct surnames joined - 26044 - one shared family surname for three
owners - and 26045 - a single owner).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRELIM_BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SYDNEY\CONTRACT"
                    r"\NSW PRELIMINARY AGREEMENT 2024.docx")
STATES = {"NSW", "QLD", "VIC", "ACT", "SA", "WA", "TAS", "NT"}


def doc_suffix(values):
    """'LOT <lot>_<SUBURB>_<SURNAMES>' from the job JSON, per CD-7.2."""
    lot = str(values.get("lot_no", "")).strip()
    suburb_words = str(values.get("suburb", "")).split()
    if suburb_words and suburb_words[-1].upper() in STATES:
        suburb_words = suburb_words[:-1]
    suburb = " ".join(suburb_words).upper()
    surnames = []
    for key in ("owner_1", "owner_2"):
        name = str(values.get(key) or "").strip()
        if name:
            last = name.split()[-1].upper()
            if last not in surnames:
                surnames.append(last)
    if not (lot and suburb and surnames):
        sys.exit(f"ERROR: lot_no/suburb/owner_1 needed to name the documents "
                 f"(got lot={lot!r}, suburb={suburb!r}, owners={surnames})")
    return f"LOT {lot}_{suburb}_{'&'.join(surnames)}"


def run_py(script, *args):
    return subprocess.run([sys.executable, str(HERE / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def export_pdfs(pairs, force):
    """All exports through ONE Word instance (start-up dominates the cost)."""
    docx = ",".join(ps_quote(a) for a, _ in pairs)
    outs = ",".join(ps_quote(b) for _, b in pairs)
    cmd = (f"& {ps_quote(HERE / 'export_pdf.ps1')} -Docx @({docx}) "
           f"-Out @({outs})" + (" -Force" if force else ""))
    return subprocess.run(["pwsh", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--template", help="blank inclusions template (omit for a prelim-only run)")
    ap.add_argument("--prelim", action="store_true",
                    help="also fill the preliminary agreement (CD-4.4: a human decided the job needs one)")
    ap.add_argument("--prelim-template", default=str(PRELIM_BLANK))
    ap.add_argument("--workdir", help="defaults to the job JSON's folder")
    ap.add_argument("--real-dir",
                    help="the job's CONTRACT DOCUMENTATION folder (read-only): "
                         "export REAL_ PDFs and worddiff the drafts against the completed documents")
    ap.add_argument("--no-pdf", action="store_true",
                    help="skip PDF exports (regression/timing use only - a draft for review ALWAYS gets its preview)")
    args = ap.parse_args()

    job_path = Path(args.job)
    values = json.loads(job_path.read_text(encoding="utf-8"))
    workdir = Path(args.workdir) if args.workdir else job_path.parent
    if "PROJECTS" in (part.upper() for part in workdir.parts):
        sys.exit("ERROR: workdir is inside Z:\\PROJECTS - this script never writes to job folders. "
                 "Saving there is the skill's step 9: human approval, then a deliberate copy.")
    workdir.mkdir(parents=True, exist_ok=True)
    if not args.template and not args.prelim:
        sys.exit("ERROR: nothing to do - give --template for the inclusions and/or --prelim")

    suffix = doc_suffix(values)
    timings, artifacts, failures = [], [], []
    t_total = time.perf_counter()

    def stage(name, fn):
        t = time.perf_counter()
        ok = fn()
        timings.append((name, time.perf_counter() - t))
        if not ok:
            failures.append(name)
        return ok

    def fill_doc(kind, script, template, out_name):
        """check -> fill -> blank diff; abort the document on a failed check."""
        check = run_py(script, "--template", template, "--job", job_path, "--check")
        (workdir / f"check_{kind}.txt").write_text(check.stdout + check.stderr, encoding="utf-8")
        if check.returncode != 0:
            print(f"  {kind}: ANCHOR CHECK FAILED - stopping this document. "
                  f"See check_{kind}.txt; the template may have been revised.")
            return None
        out = workdir / out_name
        fill = run_py(script, "--template", template, "--job", job_path, "--out", out)
        (workdir / f"fill_{kind}.txt").write_text(fill.stdout + fill.stderr, encoding="utf-8")
        if fill.returncode != 0 or not out.exists():
            print(f"  {kind}: FILL FAILED - see fill_{kind}.txt")
            return None
        diff = run_py("docx_diff.py", template, out)
        (workdir / f"diff_{kind}_vs_blank.txt").write_text(diff.stdout, encoding="utf-8")
        regions = diff.stdout.strip().splitlines()[-1] if diff.stdout.strip() else "?"
        print(f"  {kind}: filled -> {out.name}   blank-diff: {regions}")
        artifacts.append(out)
        return out

    made = {}
    if args.template:
        ok = stage("inclusions: check+fill+diff", lambda: bool(
            made.setdefault("inclusions", fill_doc(
                "inclusions", "fill_inclusions.py", args.template,
                f"INCLUSIONS_{suffix}.docx"))))
    if args.prelim:
        stage("prelim: check+fill+diff", lambda: bool(
            made.setdefault("prelim", fill_doc(
                "prelim", "fill_prelim.py", args.prelim_template,
                f"PRELIMINARY AGREEMENT_{suffix}.docx"))))

    # gather every PDF the run needs and export them through one Word launch
    pairs = [(doc, workdir / f"PREVIEW_{doc.stem}.pdf") for doc in made.values() if doc]
    real_docs = []
    if args.real_dir:
        real = Path(args.real_dir)
        for kind, pattern in (("inclusions", "INCLUSIONS*.docx"),
                              ("prelim", "PRELIMINARY AGREEMENT*.docx")):
            if kind in made and made[kind]:
                hit = next((p for p in sorted(real.glob(pattern))), None)
                if hit:
                    real_docs.append((kind, hit))
                    pairs.append((hit, workdir / f"REAL_{hit.stem}.pdf"))
                else:
                    print(f"  note: no completed {kind} in {real} to compare against")

    if pairs and not args.no_pdf:
        def do_export():
            r = export_pdfs(pairs, force=True)  # workdir previews are re-runnable scratch
            for line in (r.stdout or "").splitlines():
                if line.strip():
                    print(f"  {line.strip()}")
            if r.returncode != 0:
                print(f"  PDF EXPORT FAILED: {(r.stderr or '').strip()[:300]}")
                return False
            artifacts.extend(out for _, out in pairs)
            return True
        stage(f"pdf export x{len(pairs)} (one Word instance)", do_export)

    for kind, real_doc in real_docs:
        def do_diff(kind=kind, real_doc=real_doc):
            wd = run_py("docx_worddiff.py", made[kind], real_doc)
            out = workdir / f"worddiff_{kind}_vs_real.txt"
            out.write_text(wd.stdout, encoding="utf-8")
            blocks = wd.stdout.count("### block")
            print(f"  {kind} vs real: {blocks} differing block(s) -> {out.name} "
                  f"(every one must be classified: field, human spec content, or known variance)")
            artifacts.append(out)
            return True
        stage(f"{kind}: worddiff vs real", do_diff)

    total = time.perf_counter() - t_total
    lines = [f"{name:<44} {dt:7.2f}s" for name, dt in timings]
    lines.append(f"{'TOTAL':<44} {total:7.2f}s")
    (workdir / "timings.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    for line in lines:
        print(f"  {line}")
    print(f"\n  workdir  : {workdir}")
    for a in artifacts:
        print(f"  artifact : {a.name}")
    if failures:
        print(f"\n  FAILED stages: {', '.join(failures)}")
        return 1
    print("\n  DRAFTS ONLY. Show the complete PREVIEW PDFs and get an explicit "
          "approval before anything moves (skill step 7); saving to the job "
          "folder is step 9, by hand, on that approval.")
    return 0


# This console is cp1252; document text carries m2, curly quotes and dotted leaders.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
