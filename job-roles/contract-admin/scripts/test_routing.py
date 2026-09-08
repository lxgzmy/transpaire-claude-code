r"""Self-test for draft_contract.py's per-document routing (CD-7.6/7.7, 8 Sep 2026).

    python test_routing.py

Synthetic values only - no client data, no Z:\PROJECTS. Builds a throwaway
workdir with stand-in "documents" (empty files under the real deliverable
names) and a fake CONTRACT DOCUMENTATION folder, points the module's test
root at a scratch folder, and asserts that:

  1. a document type the job folder does not hold saves INTO the job folder,
  2. a document type the job folder already holds (SS\ included) refreshes
     ONLY to the test root - the job folder copy is untouched,
  3. the two can happen in the same delivery,
  4. a production re-delivery never overwrites (clash -> SystemExit, and
     nothing is copied first),
  5. non-contract files in the job folder (the request email, plans) never
     make anything a test,
  6. the legacy "- TEST UNAPPROVED TEMPLATE" output is no longer delivered.

Scratch lives under runtime\contract-admin\state\ (git-ignored, on Z:) and is
removed at the end.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402

SCRATCH = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_routing-selftest"
VALUES = {"lot_no": "1", "suburb": "TESTVILLE NSW", "owner_1": "Alex EXAMPLE",
          "owner_2": "Sam SAMPLE"}


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def fresh():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    workdir = SCRATCH / "9999-lot1"
    job_dir = SCRATCH / "job" / "CONTRACT" / "CONTRACT DOCUMENTATION"
    job_dir.mkdir(parents=True)
    dc.TEST_ROOT = SCRATCH / "template-testing"
    return workdir, job_dir


def make_docs(workdir, kinds):
    suffix = dc.doc_suffix(VALUES)
    for kind in kinds:
        touch(workdir / f"{kind}_{suffix}.docx")
        touch(workdir / f"PREVIEW_{kind}_{suffix}.pdf")
    touch(workdir / "job.json")
    touch(workdir / "fill_inclusions.txt")
    return suffix


def check(cond, msg):
    if not cond:
        sys.exit(f"FAIL: {msg}")
    print(f"  ok  {msg}")


def main():
    suffix = dc.doc_suffix(VALUES)
    check(suffix == "LOT 1_TESTVILLE_EXAMPLE&SAMPLE", f"suffix {suffix}")

    # 1+3+5: inclusions already in the job folder (in SS\), a request email
    # too; build contract not there -> build contract to the job folder,
    # inclusions refresh to the test root.
    workdir, job_dir = fresh()
    make_docs(workdir, ("INCLUSIONS", "BUILD CONTRACT"))
    touch(job_dir / "SS" / f"INCLUSIONS_{suffix} V1.docx")
    touch(job_dir / "Build Contract Request - Lot 1.msg")
    existing = dc.existing_contract_docs(job_dir)
    check(existing["INCLUSIONS"] and not existing["BUILD CONTRACT"]
          and not existing["PRELIMINARY AGREEMENT"],
          "existing docs seen per kind, SS\\ included, .msg ignored")
    prod, test = dc.deliver_routed(workdir, VALUES, job_dir, existing)
    check({k for _, _, k in prod} == {"BUILD CONTRACT"}, "build contract routed to the job folder")
    check({k for _, _, k in test} == {"INCLUSIONS"}, "inclusions routed to the test folder")
    check((job_dir / f"BUILD CONTRACT_{suffix}.docx").exists()
          and (job_dir / f"BUILD CONTRACT_{suffix}.pdf").exists(),
          "build contract docx+pdf pair landed in the job folder")
    check(not (job_dir / f"INCLUSIONS_{suffix}.docx").exists(),
          "inclusions NOT written to the job folder")
    tdir = dc.TEST_ROOT / workdir.name
    check((tdir / f"INCLUSIONS_{suffix}.docx").exists() and (tdir / f"INCLUSIONS_{suffix}.pdf").exists(),
          "inclusions pair refreshed in template-testing\\<job>\\")
    check(not (tdir / f"BUILD CONTRACT_{suffix}.docx").exists(),
          "build contract NOT duplicated into the test folder")
    check((tdir / "temp" / "job.json").exists(), "working files in the test folder's temp\\")

    # 4: run it again - the build contract now exists in production, so it
    # routes to the test folder; a forced production re-delivery clashes.
    existing = dc.existing_contract_docs(job_dir)
    prod, test = dc.deliver_routed(workdir, VALUES, job_dir, existing)
    check(not prod and {k for _, _, k in test} == {"INCLUSIONS", "BUILD CONTRACT"},
          "second run: both documents now refresh to the test folder only")
    try:
        dc.deliver_production(dc.collect_finals(workdir, VALUES), job_dir)
        sys.exit("FAIL: production overwrite did not stop")
    except SystemExit as e:
        check("never overwrites" in str(e), "production never overwrites (clash stops the run)")

    # 2: an empty job folder -> everything is a first draft into the job folder.
    workdir, job_dir = fresh()
    make_docs(workdir, ("INCLUSIONS", "PRELIMINARY AGREEMENT", "BUILD CONTRACT"))
    existing = dc.existing_contract_docs(job_dir)
    prod, test = dc.deliver_routed(workdir, VALUES, job_dir, existing)
    check(len(prod) == 6 and not test, "empty job folder: all three pairs saved into it")
    check(not (dc.TEST_ROOT / workdir.name).exists(), "nothing written to the test root")

    # 6: legacy tagged output is ignored, not delivered.
    workdir, job_dir = fresh()
    make_docs(workdir, ("INCLUSIONS",))
    touch(workdir / f"BUILD CONTRACT_{suffix}{dc.LEGACY_TEST_BC_TAG}.docx")
    touch(workdir / f"PREVIEW_BUILD CONTRACT_{suffix}{dc.LEGACY_TEST_BC_TAG}.pdf")
    finals = dc.collect_finals(workdir, VALUES)
    check({k for _, _, k in finals} == {"INCLUSIONS"}, "legacy tagged build contract not delivered")

    shutil.rmtree(SCRATCH)
    print("PASS: per-document routing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
