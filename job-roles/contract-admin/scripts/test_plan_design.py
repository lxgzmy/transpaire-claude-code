r"""Self-test for plan_design.py and draft_contract.resolve_design (team rule, 10 Nov 2026:
the design and the façade come from the plans; the email or the SA only until the plans are
out). Synthetic values only.

    python test_plan_design.py

The title-block forms below are the ones read on the plans of 20 issued jobs in four regions
on 10 Nov 2026 (house designs and façade names only - no street, lot or client). Writes only
under runtime\contract-admin\state\_plan-design-selftest\ (removed at the end).
"""
import contextlib
import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402
import plan_design as P  # noqa: E402
import synthetic_plans_pdf as SP  # noqa: E402

SCRATCH = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_plan-design-selftest"
fails = []


def check(cond, msg):
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        fails.append(msg)


def plans(folder, name, lot, title, area="232.73", sheets=2):
    p = folder / name
    p.write_bytes(SP.build_pdf(sheets, SP.title_block_content(lot, title, total_area=area), compress=True))
    return p


def titles():
    print("title block forms (parse_title)")
    cases = [
        ("Sapphire 200 - Kent Facade", ("Sapphire 200", "Kent", False)),
        ("Hyams 145 + 60 - Hamptons facade", ("Hyams 145", "Hamptons", True)),
        ("4+2 Custom Hamptons Facade", ("Custom", "Hamptons", False)),
        ("Avoca 180 Koba Facade", ("Avoca 180", "Koba", False)),
        ("Hyams 145 + 60 Hamptons Facade", ("Hyams 145", "Hamptons", True)),
        ("Diamond mod (Karri Facade)", ("Diamond mod", "Karri", False)),
        ("Custom 290 - Maple", ("Custom 290", "Maple", False)),
        ("Cabarita 225", ("Cabarita 225", None, False)),
        ("Custom - Secondary dwelling - Mod Facade", ("Custom", "Mod", True)),
        ("Custom mod - Hamptons facade", ("Custom mod", "Hamptons", False)),
        ("TBA Lot 2051-2058 Integrated Housing", (None, None, False)),
    ]
    for title, want in cases:
        got = P.parse_title(title)
        check((got["design"], got["facade"], got["aux"]) == want, f"{title!r} -> {want}")
    words = "SCALE: 1:100 @A3 Sapphire 200 - Kent Facade Lot 9101 Sample Road".split()
    check(P.title_blocks(words, "9101") == ["Sapphire 200 - Kent Facade"], "title block found before 'Lot 9101'")
    check(P.title_blocks(words, "9999") == [], "another lot's title block is not this job's")
    check(P.title_blocks("Sample Road Lot 9101 402 m".split(), "9101") == [],
          "'Lot 9101' with no '@A3' before it (a site-plan label) is not a title block")


def decisions():
    print("the plans win only when they name a different design (decide)")
    plan = lambda d, aux=False: {"design": d, "aux": aux, "source": "PLANS.pdf"}
    cases = [
        ("Hyams 145 + Auxiliary Unit", plan("Custom"), "Custom + Auxiliary Unit", "26061: the plans' Custom wins, aux kept"),
        ("Sapphire 200", plan("Hyams 145", aux=True), "Hyams 145 + Auxiliary Unit", "'+ 60' on the plans makes it aux"),
        ("Custom", plan("Custom 290"), "Custom 290", "the plans add the size number"),
        ("Custom 200", plan("Custom mod"), "Modified Custom", "'mod' written as the team does"),
        ("", plan("Cabarita 225"), "Cabarita 225", "nothing in the job JSON: the plans' design"),
        ("Modified Custom", plan("Custom mod"), None, "same design in other words: kept"),
        ("Modified Diamond with Studio", plan("Diamond mod"), None, "the request says more than the title block: kept"),
        ("Hyams 145 + Auxiliary Unit", plan("Hyams 145", aux=True), None, "same design: kept"),
        ("X 100", plan(None), None, "no design on the plans: kept"),
    ]
    for house_type, p, want, what in cases:
        got, _ = P.decide(house_type, p)
        check(got == want, f"{house_type!r} vs plans {p['design']!r} -> {want!r} ({what})")
    print("the façade the same way (decide_facade)")
    fac = lambda f: {"facade": f}
    for facade, p, want, what in [
        ("Kent Façade", fac("Hamptons"), "Hamptons Façade", "a different façade: the plans', with the cedilla"),
        ("", fac("Bedarra"), "Bedarra Façade", "none in the job JSON: the plans'"),
        ("Hamptons Facade", fac("Hamptons"), None, "the same façade, typed without the cedilla: kept"),
        ("Modified Facade", fac("Mod"), None, "26032: 'Mod' is the team's 'Modified': kept"),
        ("", fac("Mod"), "Modified Façade", "'Mod' written as the team does"),
        ("Kent Façade", fac(None), None, "no façade on the plans: kept"),
    ]:
        got, _ = P.decide_facade(facade, p)
        check(got == want, f"{facade!r} vs plans {p['facade']!r} -> {want!r} ({what})")


def reading():
    print("reading plans PDFs (from_plans)")
    d = SCRATCH / "read"
    d.mkdir(parents=True)
    one = plans(d, "PLANS_A.pdf", "9101", "Custom - Hamptons Facade")
    got = P.from_plans([one], "9101")
    check((got["design"], got["facade"], got["size"], got["source"]) == ("Custom", "Hamptons", "232.73", "PLANS_A.pdf"),
          f"design, façade and total area read: {got['design']}, {got['facade']}, {got['size']}")
    two = plans(d, "PLANS_B.pdf", "9101", "Hyams 145 + 60 - Kent Facade")
    got = P.from_plans([one, two], "9101")
    check(got["design"] is None and got["conflict"] == ["Custom", "Hyams 145"], "plans that disagree: no design, both named")
    other = plans(d, "PLANS_C.pdf", "4242", "Sapphire 200 - Kent Facade")
    check(P.from_plans([other], "9101")["design"] is None, "plans for another lot give no design")
    got = P.from_plans([d / "PLANS_missing.pdf"], "9101")
    check(got["design"] is None and got["unread"] and "FileNotFoundError" in got["unread"][0],
          "a plans file that cannot be read is reported, not skipped silently")


def run_step(job, plan_title=None, lot="9101", area="232.73"):
    wd = SCRATCH / f"wd-{len(list(SCRATCH.glob('wd-*')))}"
    wd.mkdir(parents=True)
    jp = wd / "job.json"
    jp.write_text(json.dumps(job), encoding="utf-8")
    if plan_title:
        plans(wd, "PLANS_LOT 9101_SAMPLE.pdf", lot, plan_title, area=area)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        path, values = dc.resolve_design(dict(job), jp, wd, None)
    return path, values, out.getvalue()


def the_run():
    print("the run (draft_contract.resolve_design, then resolve_job)")
    job = {"lot_no": "9101", "house_type": "Hyams 145 + Auxiliary Unit", "house_size": "232.72 m²",
           "facade": "Hamptons Façade"}
    path, values, log = run_step(job, "4+2 Custom Hamptons Facade")
    check(path.name == "job.design.json" and values["house_type"] == "Custom + Auxiliary Unit"
          and json.loads(path.read_text(encoding="utf-8"))["house_type"] == "Custom + Auxiliary Unit",
          "26061's case: a resolved copy reads 'Custom + Auxiliary Unit'; the job JSON is not edited")
    check("FLAG: design" in log and "'Custom + 60'" in log, "flagged, with OSC's Design to check ('Custom + 60')")
    check("FLAG: size" in log and "232.73" in log, "a size off the plans' total is flagged (CD-2.7)")
    check("FLAG: façade" not in log and values["facade"] == "Hamptons Façade" and "façade   :" in log,
          "the same façade in other words: kept, said so, no flag")
    path, values, log = run_step(dict(job, house_type="Custom + Auxiliary Unit", house_size="232.73 m²"),
                                 "4+2 Custom Hamptons Facade")
    check(path.name == "job.json" and "kept" in log and "FLAG" not in log, "plans and job agree: nothing changes, no flag")
    path, values, log = run_step(dict(job, facade="Kent Façade", house_size="232.73 m²",
                                      house_type="Custom + Auxiliary Unit"), "Custom - Hamptons Facade")
    check(path.name == "job.design.json" and values["facade"] == "Hamptons Façade"
          and values["house_type"] == "Custom + Auxiliary Unit" and "FLAG: façade" in log
          and "OSC's Facade" in log and "FLAG: design" not in log,
          "a different façade: the plans' 'Hamptons Façade', flagged with OSC's Facade; the design untouched")
    path, values, log = run_step(job)
    check(path.name == "job.json" and "no plans among the run's files" in log and "the SA" in log,
          "no plans: as the job JSON has it (the request or the SA), said so")
    wd = SCRATCH / "wd-resolve-job"
    wd.mkdir(parents=True)
    jp = wd / "job.json"
    sample = {"lot_no": "9101", "street": "9 Sample Road", "suburb": "SAMPLEVILLE NSW", "estate": "Sample Heights",
              "house_type": "Sample 145", "house_size": "200.00 m²", "facade": "Sample Façade"}
    jp.write_text(json.dumps(sample), encoding="utf-8")
    plans(wd, "PLANS_SAMPLE.pdf", "9101", "Sample 150 - Sample Front Facade", area="200.00")
    with contextlib.redirect_stdout(io.StringIO()):
        path, values = dc.resolve_job(dict(sample), jp, wd, None)
    check(values["house_type"] == "Sample 150" and values["facade"] == "Sample Front Façade",
          "resolve_job, the run's own sequence, ends with the plans' design and façade")


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    titles()
    decisions()
    reading()
    the_run()
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print(("FAIL - " + "; ".join(fails)) if fails else "PASS - 0 failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
