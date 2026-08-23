r"""Run the whole contract-drafting pipeline for one job, timed. Stdlib only.

    python draft_contract.py --job <workdir>/job.json --template "<blank>" --job-dir "<job's CONTRACT DOCUMENTATION>"
    python draft_contract.py --job <workdir>/job.json --template "<blank>" --prelim --job-dir "<...>"
    python draft_contract.py --job <workdir>/job.json --job-dir "<...>"            (route+deliver an already-filled workdir)
    python draft_contract.py --job <workdir>/job.json --deliver "<output folder>"  (explicit destination, e.g. a handover)

One command for the whole run: anchor check, fill, blank-vs-filled diff,
optional preliminary agreement (same three stages), complete PDF exports in a
single Word launch, and - with --job-dir - delivery to the correct destination
in the same pass. The preview/approval stop was REMOVED by instruction on
17 Aug 2026: the run no longer pauses for a human between fill and save.

--job-dir points at the job's CONTRACT DOCUMENTATION folder and decides the
destination automatically (skill rule, 17 Aug 2026):

  TEST - the folder already holds contract documents (INCLUSIONS*,
     PRELIMINARY AGREEMENT* or BUILD CONTRACT*, SS\ included): the job already
     exists in production, so this run is a test. Finals go ONLY to
     Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\
     (refreshed in place), working files to its temp\, and NOTHING is written
     to the job folder. --real-dir defaults to the job folder so the drafts
     are worddiffed against the completed documents.
  PRODUCTION - the folder holds no contract document (a genuine first draft):
     the final .docx + .pdf pair per document is copied into the job folder
     itself (CD-7.1/7.4). Never overwrites - a name clash stops the run;
     superseding a version stays a person's copy + SS\ move (CD-7.5). Note the
     consequence: re-running the same job after a production save routes to
     TEST (the job now exists in production), so fixes land in the test folder
     and a person promotes them.

The gates that remain are data gates, not preview gates: a missing anchor
still aborts its document, an unsourced mandatory value still refuses the
fill, any failed stage blocks delivery, production never overwrites, and the
workdir still may not sit under Z:\PROJECTS - the only thing ever written
into a job folder is the final pair, by deliver_production. --real-dir stays
read-only (the real documents are opened read-only by Word and exported INTO
the workdir).

Every --job-dir run also probes the HIA build contract status (hia_probe.py,
CD-5.2a) and - since 18 Aug 2026, by explicit instruction - FILLS the build
contract in the same pass when a template it may use exists (fill_hia.py,
region-aware): an approved CANDIDATE blank in the region's CONTRACT folder is
filled under the real deliverable name (the anchor check is the automated
regression gate; eye-verify the first fill after a template lands); with no
candidate, TEST runs fill from the staged UNAPPROVED conversion under a
"- TEST UNAPPROVED TEMPLATE" name; PRODUCTION with no approved blank stays
data-sheet-only. The verdict prints in the summary and ships as
hia_status.txt with the evidence. --no-build-contract skips the stage.

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
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hia_probe  # noqa: E402  (region mapping + blank classification)
PRELIM_BLANK = Path(r"Z:\PROCEDURES & FORMS\CONTRACTS\REGION - SYDNEY\CONTRACT"
                    r"\NSW PRELIMINARY AGREEMENT 2024.docx")
STATES = {"NSW", "QLD", "VIC", "ACT", "SA", "WA", "TAS", "NT"}

# Test-mode destination: a job whose CONTRACT DOCUMENTATION already holds any
# of these already exists in production, so a new run is a test and lands here.
TEST_ROOT = Path(r"Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing")
CONTRACT_DOC_GLOBS = ("INCLUSIONS*", "PRELIMINARY AGREEMENT*", "BUILD CONTRACT*")

# HIA build contract (CD-5.2a/5.2b, driver-integrated 18 Aug 2026 by explicit
# instruction). Template resolution order, per region:
#   1. an approved CANDIDATE .docx in the region's CONTRACT template folder
#      (a person + MCR put it there) -> filled under the real deliverable name.
#      The anchor --check is the automated regression gate; the first run
#      after a template lands must still be eye-verified.
#   2. no candidate, TEST mode only -> the staged template below, filled under
#      a name that says so. Never in PRODUCTION: a template MCR has not filed
#      never produces a document that could reach a job folder.
#   3. otherwise -> data sheet only (the pre-existing behaviour).
# NSW's staged template is the team's own Word build of the contract
# (NSW.BUILD.CONTRACT.Final.docx, 21 Aug 2026) - it replaced the repaired PDF
# conversion on 23 Aug 2026 and removed the conversion path's layout artifacts.
# QLD still fills from its repaired conversion until the team builds one.
STAGED_HIA_DIR = HERE.parents[2] / "runtime" / "contract-admin" / "outputs" / "_hia-word-templates"
STAGED_HIA = {
    "NSW": STAGED_HIA_DIR / "NSW BUILD CONTRACT Final 21.08.2026 - TEAM BUILD PENDING MCR.docx",
    "QLD": STAGED_HIA_DIR / "QLD HIA BUILD CONTRACT 09.02.2023 upd 30.07.26 - REPAIRED UNAPPROVED.docx",
}
TEST_BC_TAG = " - TEST UNAPPROVED TEMPLATE"


COMPANY_TAILS = ("PTY LTD", "PTY LIMITED", "LTD", "LIMITED", "PTY. LTD.")


def owner_token(name):
    """The filename token for one owner: surname, or a company's leading word.

    A company owner carries Pty Ltd or the like; taking the 'surname' would
    name every company job _LTD. The completed job 26039 names its files
    INCLUSIONS_LOT 4_PALLARA_VWJJ for owner 'VWJJ INVESTMENT No.1 PTY LTD ATF
    WANG AND LIU No.1 FAMILY TRUST' - the distinctive first word of the
    trustee company is the token, and any 'ATF <trust>' clause is ignored.
    The tail is matched anywhere in the name, not just at its end, because a
    land contract may write the ACN inline after it ('<Name> Pty Ltd A.C.N
    nnn nnn nnn ATF <trust>', seen 18 Aug 2026 on job 25163): an endswith
    test falls through and names the file after the ACN's last digit group
    instead of the company's first word.
    """
    up = " ".join(name.upper().replace(".", "").split())
    up = up.split(" ATF ")[0]  # trustee-for clause never feeds the filename
    for tail in COMPANY_TAILS:
        if f" {tail.replace('.', '')} " in f" {up} ":
            return up.split()[0]
    if up.endswith("TRUST"):
        return up.split()[0]
    return name.split(" ATF ")[0].split()[-1].upper()


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
            last = owner_token(name)
            if last not in surnames:
                surnames.append(last)
    if not (lot and suburb and surnames):
        sys.exit(f"ERROR: lot_no/suburb/owner_1 needed to name the documents "
                 f"(got lot={lot!r}, suburb={suburb!r}, owners={surnames})")
    return f"LOT {lot}_{suburb}_{'&'.join(surnames)}"


def contract_docs_present(job_dir):
    """Contract documents already in the job's CONTRACT DOCUMENTATION, SS\\ included.

    Any hit means the job already exists in production, so a new run for it is
    a TEST run and must not touch the job folder (skill rule, 17 Aug 2026).
    """
    hits = set()
    for pattern in CONTRACT_DOC_GLOBS:
        hits.update(p.relative_to(job_dir).as_posix()
                    for p in job_dir.rglob(pattern) if p.is_file())
    return sorted(hits)


def collect_finals(workdir, values):
    """(source, deliverable name) for every filled document in the workdir.

    A document only ever ships as its .docx + .pdf pair (CD-7.4); the PDF is
    the workdir's PREVIEW_ export renamed to the real deliverable name.
    """
    suffix = doc_suffix(values)
    finals = []
    for kind in ("INCLUSIONS", "PRELIMINARY AGREEMENT", "BUILD CONTRACT"):
        for tag in ("", TEST_BC_TAG):
            docx = workdir / f"{kind}_{suffix}{tag}.docx"
            pdf = workdir / f"PREVIEW_{kind}_{suffix}{tag}.pdf"
            if docx.exists():
                if not pdf.exists():
                    sys.exit(f"ERROR: {pdf.name} missing - a document only ships as its "
                             f"docx + PDF pair (CD-7.4). Re-run the fill without --no-pdf.")
                finals.append((docx, docx.name))
                finals.append((pdf, f"{kind}_{suffix}{tag}.pdf"))
    if not finals:
        sys.exit(f"ERROR: nothing to deliver - no filled documents named *_{suffix} in {workdir}")
    return finals


def deliver(workdir, values, dest, force):
    """Copy the finals to an explicit destination (test or handover folders).

    End users are non-technical and get exactly the deliverable pair per
    document - the filled .docx and its .pdf under the REAL deliverable names
    (no PREVIEW_ prefix). Every working file (diffs, worddiffs, fill reports,
    REAL_/PREVIEW_ exports, job JSON, timings) goes to <dest>/temp/ so the
    output folder stays clean but the evidence stays reachable.
    """
    dest = Path(dest)
    if "PROJECTS" in (part.upper() for part in dest.parts):
        sys.exit("ERROR: --deliver never writes under Z:\\PROJECTS. A production save is "
                 "--job-dir pointing at the job's CONTRACT DOCUMENTATION folder - that "
                 "route test-detects first and never overwrites.")
    finals = [(src, dest / name) for src, name in collect_finals(workdir, values)]
    clash = [b for _, b in finals if b.exists()]
    if clash and not force:
        sys.exit("ERROR: already delivered: " + ", ".join(c.name for c in clash)
                 + ". --deliver-force replaces them (test-folder refreshes only).")
    dest.mkdir(parents=True, exist_ok=True)
    temp = dest / "temp"
    temp.mkdir(exist_ok=True)
    final_sources = {a for a, _ in finals}
    for a, b in finals:
        copy_final(a, b)
        print(f"  delivered : {b}")
    moved = 0
    for f in sorted(workdir.iterdir()):
        if f.is_file() and f not in final_sources:
            shutil.copy2(f, temp / f.name)
            moved += 1
    print(f"  evidence  : {moved} working file(s) -> {temp}")


def deliver_production(workdir, values, job_dir):
    """First-draft save into the job's own CONTRACT DOCUMENTATION (CD-7.1).

    Writes the final docx + PDF pairs and nothing else - evidence stays in the
    workdir. Never overwrites: a name clash stops the run, because superseding
    a version is a person's copy + SS\\ move (CD-7.5).
    """
    finals = [(src, job_dir / name) for src, name in collect_finals(workdir, values)]
    clash = [b for _, b in finals if b.exists()]
    if clash:
        sys.exit("ERROR: already in the job folder: " + ", ".join(c.name for c in clash)
                 + ". Production never overwrites - superseding a version is a person's "
                 "copy with the old one moved to the folder's SS\\ (CD-7.5).")
    for a, b in finals:
        copy_final(a, b)
        print(f"  saved     : {b}")


def copy_final(src, dst):
    """copy2 with retries: a reviewer having the old PDF open must produce a
    clear message naming the locked file, not a traceback mid-delivery."""
    for attempt in range(3):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError:
            if attempt < 2:
                time.sleep(0.8)
    sys.exit(f"ERROR: {dst} is open in another program (file locked). Close it and "
             f"re-run the delivery - with --job-dir and no --template it re-ships the "
             f"already-filled workdir without re-filling anything.")


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
                    help="skip PDF exports (regression/timing use only - the deliverable is "
                         "always the docx+pdf pair, so this cannot combine with a save)")
    ap.add_argument("--job-dir",
                    help="the job's CONTRACT DOCUMENTATION folder. Decides the destination and "
                         "saves in the same pass: existing contract docs there -> TEST (finals "
                         "to the template-testing folder ONLY); none -> PRODUCTION (finals into "
                         "the job folder, never overwriting). Without --template/--prelim it "
                         "routes and delivers an already-filled workdir.")
    ap.add_argument("--deliver",
                    help="explicit destination (handover/test folders, never Z:\\PROJECTS): copy "
                         "the final docx+pdf under their real deliverable names to this folder, "
                         "and every working file to <folder>/temp. Its own invocation - for a "
                         "fill-and-save in one pass use --job-dir.")
    ap.add_argument("--deliver-force", action="store_true",
                    help="allow --deliver to replace an earlier delivery (test folders only)")
    ap.add_argument("--no-build-contract", action="store_true",
                    help="skip the HIA build-contract fill (it otherwise runs on every "
                         "--job-dir fill: approved blank when one exists, staged UNAPPROVED "
                         "conversion in TEST mode, data sheet otherwise)")
    args = ap.parse_args()

    job_path = Path(args.job)
    values = json.loads(job_path.read_text(encoding="utf-8"))
    workdir = Path(args.workdir) if args.workdir else job_path.parent
    if "PROJECTS" in (part.upper() for part in workdir.parts):
        sys.exit("ERROR: workdir is inside Z:\\PROJECTS - the workdir is scratch space. The only "
                 "write into a job folder is the final pair, via --job-dir routing.")
    workdir.mkdir(parents=True, exist_ok=True)

    if args.deliver:
        if args.template or args.prelim or args.real_dir or args.job_dir:
            sys.exit("ERROR: --deliver is its own invocation for an explicit folder. To fill "
                     "and save in one pass, use --job-dir instead.")
        deliver(workdir, values, args.deliver, args.deliver_force)
        return 0

    # --job-dir: detect test vs production BEFORE anything runs, and say so.
    mode = dest = None
    if args.job_dir:
        if args.no_pdf:
            sys.exit("ERROR: --job-dir saves the docx+pdf pair, so it cannot combine with "
                     "--no-pdf.")
        job_dir = Path(args.job_dir)
        if job_dir.name.upper() != "CONTRACT DOCUMENTATION":
            sys.exit(f"ERROR: --job-dir must point at the job's CONTRACT DOCUMENTATION "
                     f"folder, got: {job_dir}")
        if not job_dir.is_dir():
            sys.exit(f"ERROR: --job-dir does not exist - verify the job folder before "
                     f"saving anything: {job_dir}")
        existing = contract_docs_present(job_dir)
        if existing:
            mode, dest = "TEST", TEST_ROOT / workdir.name
            print(f"  mode      : TEST - the job already exists in production "
                  f"({len(existing)} contract document(s) in the job folder, e.g. "
                  f"{existing[0]}). Nothing will be written there. Destination: {dest}")
            if not args.real_dir:
                args.real_dir = str(job_dir)
        else:
            mode, dest = "PRODUCTION", job_dir
            print(f"  mode      : PRODUCTION - first draft, no contract documents in the "
                  f"job folder yet. Destination: {dest}")

        # HIA build contract status (CD-5.2a): the licence makes the filled
        # docx+pdf pair a requirement, blocked until a fillable Word blank
        # lands in the region's contract folder. Probe it on every routed save
        # so the report is automatic and current, not hand-written prose.
        # Informational only - it never blocks the run, and it never fills:
        # a CANDIDATE means a person commissions fill_hia.py against it.
        hia = run_py("hia_probe.py", "--job-dir", job_dir)
        (workdir / "hia_status.txt").write_text(hia.stdout + hia.stderr,
                                                encoding="utf-8")
        for line in hia.stdout.splitlines():
            if "hia contract:" in line:
                print(f"  {line.strip()}")

    if not args.template and not args.prelim:
        if mode == "TEST":
            deliver(workdir, values, dest, force=True)
            return 0
        if mode == "PRODUCTION":
            deliver_production(workdir, values, dest)
            return 0
        sys.exit("ERROR: nothing to do - give --template for the inclusions and/or --prelim "
                 "(add --job-dir to save in the same pass)")

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

    def fill_doc(kind, script, template, out_name, extra=()):
        """check -> fill -> blank diff; abort the document on a failed check."""
        check = run_py(script, "--template", template, "--job", job_path, "--check", *extra)
        (workdir / f"check_{kind}.txt").write_text(check.stdout + check.stderr, encoding="utf-8")
        if check.returncode != 0:
            print(f"  {kind}: ANCHOR CHECK FAILED - stopping this document. "
                  f"See check_{kind}.txt; the template may have been revised.")
            return None
        out = workdir / out_name
        fill = run_py(script, "--template", template, "--job", job_path, "--out", out, *extra)
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

    # HIA build contract (CD-5.2a/5.2b): filled in the same pass whenever a
    # usable template exists - see the STAGED_HIA note above for the order.
    if args.job_dir and not args.no_build_contract:
        region = hia_probe.region_from_job_dir(job_dir)
        state = hia_probe.REGION_TO_FOLDER[region][0] if region else None
        if not state:
            print(f"  build contract: region not recognised in {job_dir} - data sheet only")
        else:
            folder = hia_probe.CONTRACTS_ROOT / hia_probe.REGION_TO_FOLDER[region][1]
            rows = hia_probe.classify(folder) if folder.is_dir() else []
            approved = [folder / rel for status, rel, _ in rows if status == "CANDIDATE"]
            template = out_name = provenance = None
            if len(approved) == 1:
                template = approved[0]
                out_name = f"BUILD CONTRACT_{suffix}.docx"
                provenance = f"approved blank {template.name} - eye-verify the first fill after a template lands"
            elif len(approved) > 1:
                print("  build contract: MORE THAN ONE candidate blank in "
                      f"{folder} - a person must pick; data sheet only this run")
            elif mode == "TEST" and STAGED_HIA[state].exists():
                template = STAGED_HIA[state]
                out_name = f"BUILD CONTRACT_{suffix}{TEST_BC_TAG}.docx"
                provenance = (f"staged template {template.name} (CD-5.2b, not yet "
                              f"MCR-filed) - never issuable, review against the licensed PDF")
            elif mode == "TEST":
                print(f"  build contract: no staged conversion for {state} at "
                      f"{STAGED_HIA[state]} - data sheet only")
            else:
                print("  build contract: BLOCKED - no approved Word blank in the region's "
                      "CONTRACT folder; data sheet only (CD-5.1/5.2a). TEST runs draft "
                      "from the staged UNAPPROVED conversion.")
            if template:
                def do_bc():
                    doc = fill_doc("buildcontract", "fill_hia.py", template,
                                   out_name, extra=("--region", state))
                    if doc:
                        made["buildcontract"] = doc
                        print(f"  build contract: from {provenance}")
                    return bool(doc)
                stage("build contract: check+fill+diff", do_bc)

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

    # Save in the same pass (17 Aug 2026: no preview stop). A failed stage
    # still blocks the save - the run fails closed, it never ships a partial.
    if mode and not failures:
        def do_deliver():
            if mode == "TEST":
                deliver(workdir, values, dest, force=True)
            else:
                deliver_production(workdir, values, dest)
            return True
        stage(f"deliver ({mode.lower()})", do_deliver)

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
        print(f"\n  FAILED stages: {', '.join(failures)}"
              + (" - NOT delivered; nothing left the workdir." if mode else ""))
        return 1
    if mode:
        print(f"\n  Saved in one pass ({mode}) - no preview stop (removed 17 Aug 2026). "
              "Flags and unsourced fields are in the fill reports for a person to "
              "resolve before issue; issuing, signing and sending stay human.")
    else:
        print("\n  No destination given (--job-dir) - the filled documents remain in "
              "the workdir.")
    return 0


# This console is cp1252; document text carries m2, curly quotes and dotted leaders.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
