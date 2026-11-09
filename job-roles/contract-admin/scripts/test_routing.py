r"""Self-test for draft_contract.py's per-document routing (CD-7.5-7.7).

    python test_routing.py

Synthetic values only - no client data, no Z:\PROJECTS. Builds a throwaway
workdir with stand-in "documents" (small files under the real deliverable
names, their bytes naming the version) and a fake CONTRACT DOCUMENTATION
folder, and asserts the 9 Nov 2026 rule (job 26061 feedback):

  1. a document type the job folder does not hold saves INTO the job folder;
  2. a revision saves into the job folder too, and the version it replaces
     moves into SS\ (created when missing) under its own name;
  3. a second and third revision never overwrite an archived copy - SS\ gets
     " V2", " V3", the team's own numbering - and a .docx and its .pdf keep
     one suffix;
  4. a failed save leaves the previous version in place and in use - a copy
     that fails, an old file that is open in another program (it cannot
     move), a new file that cannot take its name: each one puts everything
     back, with no "~saving" file left behind;
  5. a signed or executed copy in the folder stops a revision before
     anything is written;
  6. an owner change (a new file name) still archives the old one;
  7. the request email, plans, ID scans and a person's own subfolder are
     never moved and never make anything a revision; a type found only in
     SS\ is a revision with nothing left to move;
  8. the legacy "- TEST UNAPPROVED TEMPLATE" output is not delivered;
  9. a build-contract-only run (issue #73) revises the build contract alone.

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
KINDS = ("INCLUSIONS", "PRELIMINARY AGREEMENT", "BUILD CONTRACT")


def put(path, data=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def fresh():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    workdir = SCRATCH / "9999-lot1"
    job_dir = SCRATCH / "job" / "CONTRACT" / "CONTRACT DOCUMENTATION"
    job_dir.mkdir(parents=True)
    return workdir, job_dir


def make_docs(workdir, kinds, version=b"new", values=VALUES):
    suffix = dc.doc_suffix(values)
    for kind in kinds:
        put(workdir / f"{kind}_{suffix}.docx", version)
        put(workdir / f"PREVIEW_{kind}_{suffix}.pdf", version)
    put(workdir / "job.json")
    put(workdir / "fill_inclusions.txt")
    return suffix


def deliver(workdir, job_dir, **kw):
    return dc.deliver_routed(workdir, VALUES, job_dir, dc.existing_contract_docs(job_dir), **kw)


def names(folder):
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def check(cond, msg):
    if not cond:
        sys.exit(f"FAIL: {msg}")
    print(f"  ok  {msg}")


def expect_exit(fn, words, msg):
    try:
        fn()
    except SystemExit as e:
        check(words in str(e), f"{msg}  [{str(e)[:90]}...]")
        return
    sys.exit(f"FAIL: {msg} - the run did not stop")


def check_write_routes_and_company():
    wd = SCRATCH / "routes-wd"
    wd.mkdir(parents=True, exist_ok=True)
    routes = {"BUILD CONTRACT": ("PRODUCTION", Path(r"Z:\PROJECTS\X\CONTRACT DOCUMENTATION")),
              "INCLUSIONS": ("REVISION", Path(r"Z:\PROJECTS\X\CONTRACT DOCUMENTATION"))}
    out = dc.write_routes(wd, routes)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["BUILD CONTRACT\tPRODUCTION\tZ:\\PROJECTS\\X\\CONTRACT DOCUMENTATION",
                     "INCLUSIONS\tREVISION\tZ:\\PROJECTS\\X\\CONTRACT DOCUMENTATION"], lines
    assert dc.is_company_owner("EXAMPLE HOLDINGS PTY LTD ATF EXAMPLE FAMILY TRUST")
    assert dc.is_company_owner("Sample Nominees Pty. Ltd.")
    assert dc.is_company_owner("THE EXAMPLE FAMILY TRUST")
    assert not dc.is_company_owner("Alex EXAMPLE")
    (wd / "routes.txt").write_text("stale\n", encoding="utf-8")
    dc.clear_routes(wd)
    assert not (wd / "routes.txt").exists(), "stale routes.txt survived clear_routes"
    dc.clear_routes(wd)  # absent file is fine
    print("  ok  write_routes + clear_routes + is_company_owner")


def main():
    suffix = dc.doc_suffix(VALUES)
    check(suffix == "LOT 1_TESTVILLE_EXAMPLE&SAMPLE", f"suffix {suffix}")
    inc, bc = f"INCLUSIONS_{suffix}", f"BUILD CONTRACT_{suffix}"

    # 1: an empty job folder - every document is a first version saved into it
    workdir, job_dir = fresh()
    make_docs(workdir, KINDS)
    prod, rev = deliver(workdir, job_dir)
    check(len(prod) == 6 and not rev, "first save: all three pairs saved into the job folder")
    check(not (job_dir / "SS").exists(), "first save: no SS\\ created")
    check(dc.route_kind("INCLUSIONS", {"INCLUSIONS": []}, job_dir)[0] == "PRODUCTION"
          and dc.route_kind("INCLUSIONS", {"INCLUSIONS": ["x"]}, job_dir) == ("REVISION", job_dir),
          "route_kind: PRODUCTION first, REVISION after - both into the job folder")

    # 2: first revision - the new pair replaces the old one, which goes to SS\
    workdir, job_dir = fresh()
    put(job_dir / f"{inc}.docx", b"v1")
    put(job_dir / f"{inc}.pdf", b"v1")
    put(job_dir / "Contract Order - Lot 1.msg")
    put(job_dir / "PLANS_LOT 1_TESTVILLE_EXAMPLE&SAMPLE.pdf")
    put(job_dir / "claude" / f"{inc}.docx", b"a person's copy")
    make_docs(workdir, ("INCLUSIONS",), b"v2")
    prod, rev = deliver(workdir, job_dir)
    check(not prod and {k for _, _, k in rev} == {"INCLUSIONS"}, "first revision routed REVISION")
    check((job_dir / f"{inc}.docx").read_bytes() == b"v2" and (job_dir / f"{inc}.pdf").read_bytes() == b"v2",
          "first revision: the new pair is in the job folder under its real names")
    check(names(job_dir / "SS") == [f"{inc}.docx", f"{inc}.pdf"]
          and (job_dir / "SS" / f"{inc}.docx").read_bytes() == b"v1",
          "first revision: the previous pair moved into a new SS\\ under its own name")
    check((job_dir / "Contract Order - Lot 1.msg").exists()
          and (job_dir / "PLANS_LOT 1_TESTVILLE_EXAMPLE&SAMPLE.pdf").exists()
          and (job_dir / "claude" / f"{inc}.docx").read_bytes() == b"a person's copy",
          "email, plans and a person's own subfolder untouched")
    check(not [n for n in names(job_dir) if n.startswith(dc.STAGING_PREFIX)], "no ~saving file left")

    # 3: second and third revisions with SS\ already holding the names
    make_docs(workdir, ("INCLUSIONS",), b"v3")
    deliver(workdir, job_dir)
    make_docs(workdir, ("INCLUSIONS",), b"v4")
    deliver(workdir, job_dir)
    ss = job_dir / "SS"
    check(names(ss) == sorted([f"{inc}.docx", f"{inc}.pdf", f"{inc} V2.docx", f"{inc} V2.pdf",
                               f"{inc} V3.docx", f"{inc} V3.pdf"]),
          "repeat revisions: SS\\ keeps every version, numbered V2, V3, docx and pdf alike")
    check([(ss / f"{inc}{s}.docx").read_bytes() for s in ("", " V2", " V3")] == [b"v1", b"v2", b"v3"]
          and (job_dir / f"{inc}.docx").read_bytes() == b"v4",
          "repeat revisions: no archived copy overwritten; v4 is current")

    # 4a: the new version cannot be copied in - nothing changes
    workdir, job_dir = fresh()
    put(job_dir / f"{bc}.docx", b"v1")
    put(job_dir / f"{bc}.pdf", b"v1")
    make_docs(workdir, ("BUILD CONTRACT",), b"v2")
    real_copy, calls = dc.shutil.copy2, []

    def failing_copy(src, dst, *a, **k):
        calls.append(dst)
        if len(calls) == 2:
            Path(dst).write_bytes(b"half")      # a partial file, as a full disk leaves
            raise OSError("disk full (simulated)")
        return real_copy(src, dst, *a, **k)
    dc.shutil.copy2 = failing_copy
    try:
        expect_exit(lambda: deliver(workdir, job_dir), "previous version is still in use",
                    "failed copy: the run stops and says the old version is in use")
    finally:
        dc.shutil.copy2 = real_copy
    check(names(job_dir) == [f"{bc}.docx", f"{bc}.pdf"] and (job_dir / f"{bc}.pdf").read_bytes() == b"v1",
          "failed copy: the old pair untouched, no partial or ~saving file left, no SS\\")

    # 4b: the old version is open in another program and cannot move
    held = open(job_dir / f"{bc}.pdf", "rb")   # CPython opens without delete sharing
    try:
        expect_exit(lambda: deliver(workdir, job_dir), "moving the previous version into SS",
                    "old file open: the run stops at the move")
    finally:
        held.close()
    check(names(job_dir) == [f"{bc}.docx", f"{bc}.pdf"]
          and (job_dir / f"{bc}.docx").read_bytes() == b"v1" and (job_dir / f"{bc}.pdf").read_bytes() == b"v1",
          "old file open: the docx that had moved came back out of SS\\ (and the SS\\ the run made "
          "is gone); the old pair is current")

    # 4c: the new file cannot take its name - everything moves back
    (job_dir / f"{bc}.pdf").unlink()
    (job_dir / f"{bc}.pdf").mkdir()           # a folder of that name is not a file: never moved, blocks the rename
    expect_exit(lambda: deliver(workdir, job_dir), "giving the new version its name",
                "new file cannot be named: the run stops at the last step")
    check((job_dir / f"{bc}.docx").read_bytes() == b"v1" and not (job_dir / "SS").exists()
          and not [n for n in names(job_dir) if n.startswith(dc.STAGING_PREFIX)],
          "new file cannot be named: the new docx removed, the old docx back from SS\\")
    (job_dir / f"{bc}.pdf").rmdir()

    # 5: a signed copy among the files a revision would archive
    put(job_dir / f"{bc}_SIGNED.pdf", b"executed")
    expect_exit(lambda: deliver(workdir, job_dir), "looks signed or executed",
                "signed copy: the revision stops")
    check(names(job_dir) == [f"{bc}.docx", f"{bc}_SIGNED.pdf"],
          "signed copy: nothing written or moved")

    # 5b: an SS\ that already exists is kept by a rollback, with its contents
    put(job_dir / "SS" / "INCLUSIONS_LOT 1_TESTVILLE_OLD.pdf", b"v0")
    (job_dir / f"{bc}_SIGNED.pdf").unlink()
    held = open(job_dir / f"{bc}.docx", "rb")
    try:
        expect_exit(lambda: deliver(workdir, job_dir), "moving the previous version into SS",
                    "existing SS\\, old file open: the run stops at the move")
    finally:
        held.close()
    check(names(job_dir / "SS") == ["INCLUSIONS_LOT 1_TESTVILLE_OLD.pdf"]
          and (job_dir / f"{bc}.docx").read_bytes() == b"v1",
          "existing SS\\ kept as it was by the rollback")

    # 6: an owner change gives the revision a new name; the old file is still archived
    workdir, job_dir = fresh()
    put(job_dir / "INCLUSIONS_LOT 1_TESTVILLE_FORMER.docx", b"v1")
    put(job_dir / "INCLUSIONS_LOT 1_TESTVILLE_FORMER.pdf", b"v1")
    make_docs(workdir, ("INCLUSIONS",), b"v2")
    deliver(workdir, job_dir)
    check(names(job_dir) == sorted(["SS", f"{inc}.docx", f"{inc}.pdf"])
          and names(job_dir / "SS") == ["INCLUSIONS_LOT 1_TESTVILLE_FORMER.docx",
                                        "INCLUSIONS_LOT 1_TESTVILLE_FORMER.pdf"],
          "owner change: the old-named pair archived, the new pair current")

    # 7: inclusions only in SS\ (nothing current), build contract not there at all
    workdir, job_dir = fresh()
    put(job_dir / "SS" / f"{inc} V1.docx", b"v1")
    put(job_dir / "Build Contract Request - Lot 1.msg")
    make_docs(workdir, ("INCLUSIONS", "BUILD CONTRACT"))
    existing = dc.existing_contract_docs(job_dir)
    check(existing["INCLUSIONS"] and not existing["BUILD CONTRACT"] and not existing["PRELIMINARY AGREEMENT"],
          "existing docs seen per kind, SS\\ included, the request .msg ignored")
    prod, rev = deliver(workdir, job_dir)
    check({k for _, _, k in prod} == {"BUILD CONTRACT"} and {k for _, _, k in rev} == {"INCLUSIONS"},
          "one run: build contract first version, inclusions revision")
    check(names(job_dir / "SS") == [f"{inc} V1.docx"] and (job_dir / f"{inc}.docx").exists()
          and (job_dir / f"{bc}.docx").exists() and (job_dir / "Build Contract Request - Lot 1.msg").exists(),
          "a revision with nothing current: saved, SS\\ untouched")

    # 8: legacy tagged output is ignored, not delivered
    workdir, job_dir = fresh()
    make_docs(workdir, ("INCLUSIONS",))
    put(workdir / f"{bc}{dc.LEGACY_TEST_BC_TAG}.docx")
    put(workdir / f"PREVIEW_{bc}{dc.LEGACY_TEST_BC_TAG}.pdf")
    check({k for _, _, k in dc.collect_finals(workdir, VALUES)} == {"INCLUSIONS"},
          "legacy tagged build contract not delivered")

    # 9: build-contract-only (issue #73): the job folder holds all three, the
    # workdir still has the first run's inclusions and prelim
    workdir, job_dir = fresh()
    make_docs(workdir, KINDS, b"v2")
    for kind in KINDS:
        put(job_dir / f"{kind}_{suffix}.docx", b"v1")
    prod, rev = deliver(workdir, job_dir, kinds=["BUILD CONTRACT"])
    check(not prod and {k for _, _, k in rev} == {"BUILD CONTRACT"},
          "build-contract-only: only the build contract is delivered")
    check((job_dir / f"{bc}.docx").read_bytes() == b"v2" and names(job_dir / "SS") == [f"{bc}.docx"]
          and (job_dir / f"{inc}.docx").read_bytes() == b"v1"
          and (job_dir / f"PRELIMINARY AGREEMENT_{suffix}.docx").read_bytes() == b"v1",
          "build-contract-only: the contract revised, the other documents untouched")

    check_write_routes_and_company()

    shutil.rmtree(SCRATCH)
    print("PASS: per-document routing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
