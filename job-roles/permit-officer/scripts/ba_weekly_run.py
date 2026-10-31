#!/usr/bin/env python3
"""The Monday BA report run in one command (workflows/ba-weekly-report.md, steps 0-2 and delivery).

  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py              # today's draft
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --dry-run    # say what it would do
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --restart september-test --asof 2026-11-02

In order, stopping at the first problem with nothing half done:

0. Self-check: the drafter's regression suite on synthetic data, run beside the snapshot (step 3)
   and waited for before anything is copied. Code that fails its own checks drafts nothing. Code
   that already passed (the same scripts, the same Python) is not checked again, so it runs in
   full only on the first Monday after a change (--no-self-check skips it, for when a check itself
   is wrong).
1. Base: the officer's latest export in the BA REPORTS archive dated before the draft's Monday and
   no more than 7 days before it (the archive's spacing varies: "BA REPORT- 19.10.2026",
   "BA REPORT -13.04.2026"). An older one is never used in its place.
2. Her edits: last week's draft as she left it in the drop folder, read against the same draft as
   written (runtime outputs). If that file is unchanged but another copy of the same Monday's draft
   there was changed (a Save As), the newest changed copy is read. A draft still open in Excel, or
   one with no changes at all, is said in the summary.
3. Snapshot: osc_snapshot.py under the osc-api virtual environment (read-only, production; a
   passing network fault is retried). It runs before anything is copied or set aside.
4. The base and her copy are copied into runtime\\permit-officer\\reports\\ under standard names;
   --restart LABEL renames the state file ba-items-first-seen.LABEL.json (nothing deleted), so the
   week starts clean apart from her edits.
5. Draft: ba_report_draft.build_draft into runtime\\permit-officer\\outputs\\.
6. Delivery: the draft and its evidence note copied to the drop folder. A file already there under
   that name is never overwritten (she may have started on it) unless --force. The delivered draft
   is then read back the way next Monday will read it.

Read-only on the archive; writes only under runtime\\ and the agreed drop folder.
"""
import argparse
import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# abspath, not resolve(): on this server resolve() turns the mapped Z: drive into its UNC form,
# which names the file server in every path printed.
HERE = Path(os.path.abspath(__file__)).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from ba_report_draft import DraftInputError, StateError, STATE_FILE, STATE_PREVIOUS, build_draft  # noqa: E402
from ba_report_parse import officer_edits, parse_report  # noqa: E402
from nsw_holidays import covers  # noqa: E402

RUNTIME = REPO / "runtime" / "permit-officer"
ARCHIVE = Path(r"Z:\ADMINISTRATION\REPORTS\REPORTS\BA REPORTS")
DROP = Path(r"Z:\AI test\Permit Officer\BA Report test")
PILOT_JOBS = "26029,26052,26001"
VENV_PYTHON = REPO / "shared" / "mcp" / "osc-api" / ".venv" / "Scripts" / "python.exe"

REPORT_NAME = re.compile(r"^BA REPORT\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\.xlsx$", re.I)
DRAFT_NAME = re.compile(r"^BA REPORT DRAFT - (\d{2})\.(\d{2})\.(\d{4})\.xlsx$", re.I)


class RunError(RuntimeError):
    pass


def _dated(folder, pattern):
    """[(date, path)] for the files in ``folder`` whose name matches, Excel lock files skipped."""
    out = []
    for p in Path(folder).iterdir():
        m = pattern.match(p.name)
        if m and p.is_file() and not p.name.startswith("~$"):
            try:
                out.append((date(int(m.group(3)), int(m.group(2)), int(m.group(1))), p))
            except ValueError:
                continue
    return sorted(out)


def find_base(archive, asof):
    """Her latest export dated before ``asof`` and within 7 days of it, or RunError."""
    before = [(d, p) for d, p in _dated(archive, REPORT_NAME) if d < asof]
    if not before:
        raise RunError(f"no BA report dated before {asof:%d.%m.%Y} in {archive}")
    d, p = before[-1]
    if d < asof - timedelta(days=7):
        raise RunError(f"the newest BA report before {asof:%d.%m.%Y} is {p.name} ({(asof - d).days} days old); "
                       "last week's report is not in the archive yet, so nothing was drafted")
    return d, p


def find_last_draft(drop, outputs, asof):
    """(her copy in the drop folder, the same draft as delivered, notes) for the latest draft before
    ``asof``: (None, None, []) when there is none, None for the delivered one when it cannot be found.

    Her copy is the file under the draft's own name, unless that is still exactly as delivered and
    another copy of the same Monday's draft beside it has been changed (a Save As, "BA REPORT DRAFT -
    26.10.2026 GR.xlsx"): then the newest changed copy is hers. The notes say so, and say when the
    draft looks open in Excel (what she has not saved cannot be read) or holds no change at all."""
    before = [(d, p) for d, p in _dated(drop, DRAFT_NAME) if d < asof]
    if not before:
        return None, None, []
    when, edited = before[-1]
    drafted = next((p for p in (Path(outputs) / "delivered" / edited.name, Path(outputs) / edited.name)
                    if p.exists()), None)
    stamp, notes = f"{when:%d.%m.%Y}", []
    nearby = [p for p in Path(drop).iterdir() if p.is_file() and stamp in p.name and p != edited]
    if any(p.name.startswith("~$") for p in nearby):
        notes.append(f"{edited.name} looked open in Excel when the run started; anything she had not "
                     "saved was not read")
    copies = [p for p in nearby if p.suffix.lower() == ".xlsx" and not p.name.startswith("~$")
              and p.name.upper().startswith("BA REPORT DRAFT")]
    if drafted and filecmp.cmp(edited, drafted, shallow=False):
        changed = [p for p in copies if not filecmp.cmp(p, drafted, shallow=False)]
        if changed:
            newest = max(changed, key=lambda p: p.stat().st_mtime)
            notes.append(f"{edited.name} is as delivered, so her changes were read from {newest.name}")
            edited = newest
        else:
            notes.append(f"{edited.name} is exactly as delivered: no corrections from her were read this week")
    elif copies:
        notes.append("also in the drop folder for that Monday, not read: " + ", ".join(p.name for p in copies))
    return edited, drafted, notes


def copy_in(src, dst):
    """Copy into runtime under a fixed name; an identical file is left as it is."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return dst
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    return dst


def restart_state(state_dir, label):
    """Set the state aside under ``label``; nothing is deleted. Returns the renamed paths."""
    moved = []
    for name in (STATE_FILE, STATE_PREVIOUS):
        src = Path(state_dir) / name
        if src.exists():
            dst = src.with_name(src.name.replace(".json", f".{label}.json"))
            if dst.exists():
                raise RunError(f"{dst.name} already exists; choose another --restart label")
            src.rename(dst)
            moved.append(dst)
    return moved


def deliver(files, drop, kept, force=False):
    """Copy the draft and its note into the drop folder, and keep a copy of each in ``kept``.

    A file already in the drop folder is replaced only when it is still exactly what was delivered
    last time (a re-run of the same Monday before she opened it). One she has changed is never
    overwritten unless forced."""
    def untouched(f):
        there, ours = Path(drop) / f.name, Path(kept) / f.name
        return (not there.exists() or filecmp.cmp(f, there, shallow=False)
                or (ours.exists() and filecmp.cmp(there, ours, shallow=False)))
    changed = [f for f in files if not untouched(f)]
    if changed and not force:
        raise RunError("the drop folder already has " + ", ".join(f.name for f in changed) +
                       " and it has been changed since it was delivered (the officer may be working on it); "
                       "nothing was delivered. Re-run with --force only once you know it can be replaced.")
    for f in files:
        copy_in(f, Path(drop) / f.name)
        copy_in(f, Path(kept) / f.name)
    return [Path(drop) / f.name for f in files]


def verify_delivered(draft, delivered, base):
    """Read the delivered draft back the way next Monday will: it is the file written, it keeps the
    base's jobs in order, and its Items sheet reads back with no differences. Returns (jobs, rows)."""
    if not filecmp.cmp(draft, delivered, shallow=False):
        raise RunError(f"{delivered} is not the draft that was written; check the drop folder")
    got, want = parse_report(delivered), parse_report(base)
    if [r["job_no"] for r in got["rows"]] != [r["job_no"] for r in want["rows"]]:
        raise RunError(f"{delivered.name} does not hold the base report's jobs in order; "
                       "check it before she does")
    back = officer_edits(delivered, draft)
    if back["edits"] or back["unmatched"]:
        raise RunError(f"{delivered.name} does not read back cleanly; next week's read-back of her edits "
                       "would go wrong")
    return len(got["rows"]), sum(len(names) for names in back["drafted_names"].values())


SELF_CHECK_RECORD = "self-check.json"


def _code_fingerprint():
    """The scripts, the OSC client the snapshot uses, and the Python that runs them: the same
    fingerprint gives the same check result."""
    h = hashlib.sha256(sys.version.encode())
    client = REPO / "shared" / "mcp" / "osc-api" / "osc_mcp"
    for p in sorted(HERE.glob("*.py")) + sorted(client.glob("*.py")):
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def start_self_check(state_dir):
    """Start the drafter's regression suite on synthetic data in the background, or say it already
    passed on exactly this code. Better no draft on Monday than a wrong one."""
    record = Path(state_dir) / SELF_CHECK_RECORD
    code = _code_fingerprint()
    try:
        last = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if last.get("code") == code:
        return {"passed_before": last}
    proc = subprocess.Popen([sys.executable, str(HERE / "regress_ba_report.py")], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    return {"proc": proc, "code": code, "record": record, "started": time.monotonic()}


def finish_self_check(check):
    """Wait for the self-check; RunError when it failed. Returns its line for the summary."""
    if "passed_before" in check:
        last = check["passed_before"]
        return f"Self-check: this code passed {last.get('passed')} checks on {last.get('on')}; not run again"
    out, err = check["proc"].communicate()
    lines = out.splitlines()
    passed = sum(1 for ln in lines if ln.startswith("PASS"))
    if check["proc"].returncode != 0:
        failed = [ln[6:].split(" — ")[0] for ln in lines if ln.startswith("FAIL")]
        why = "; ".join(failed[:3]) or (err.strip().splitlines() or ["it stopped with an error"])[-1]
        raise RunError(f"the self-check failed ({why}), so nothing was copied or drafted. The scripts need "
                       "fixing first; --no-self-check runs anyway, only once a person has judged the check "
                       "itself wrong.")
    check["record"].parent.mkdir(parents=True, exist_ok=True)
    check["record"].write_text(json.dumps({"code": check["code"], "passed": passed,
                                           "on": date.today().isoformat()}), encoding="utf-8")
    took = time.monotonic() - check["started"]
    return f"Self-check: {passed} checks passed ({took:.0f} s, beside the snapshot)"


def run(asof, jobs, archive=ARCHIVE, drop=DROP, runtime=RUNTIME, restart=None, dry_run=False, force=False,
        snapshot=None, gate=None):
    """The Monday run. ``snapshot(out_dir, jobs)`` replaces the production snapshot step in tests;
    ``gate()``, when given, is waited for after the snapshot and before anything is copied (the
    self-check); it stops the run by raising RunError."""
    reports, outputs, state = runtime / "reports", runtime / "outputs", runtime / "state"
    base_date, base_src = find_base(archive, asof)
    base = reports / f"BA REPORT - {base_date:%d.%m.%Y}.xlsx"
    edited_src, drafted, found = find_last_draft(drop, outputs, asof)
    # her copy under the standard name, whatever she saved it as
    edited = (reports / (drafted or edited_src).name.replace(".xlsx", " (officer-edited).xlsx")
              if edited_src else None)
    plan = [f"base: {base_src.name} -> {base}",
            (f"her edits: {edited_src.name} (drop folder), read against {drafted}" if drafted else
             f"her edits: {edited_src.name} found but the draft as written is not in {outputs}; not read"
             if edited_src else "her edits: no earlier draft in the drop folder"),
            f"restart: state set aside as .{restart}.json" if restart else "state: carried on",
            f"snapshot: jobs {','.join(jobs)} -> {state / 'snapshots'}",
            f"draft: BA REPORT DRAFT - {asof:%d.%m.%Y}.xlsx -> {outputs}, delivered to {drop}"] + found
    there = Path(drop) / f"BA REPORT DRAFT - {asof:%d.%m.%Y}.xlsx"
    if there.exists():
        saved = time.strftime("%d/%m/%Y %H:%M", time.localtime(there.stat().st_mtime))
        plan.append(f"this Monday's draft is already in the drop folder (saved {saved}); it is replaced "
                    "only if she has not changed it")
    # A restart done once is not done again (a week-1 command run a second time): said before anything runs.
    set_aside = state / STATE_FILE.replace(".json", f".{restart}.json")
    if restart and set_aside.exists():
        stop = (f"--restart {restart} has already been done (the state was set aside as {set_aside.name}); "
                "run without --restart to redo or carry on this week")
        if not dry_run:
            raise RunError(stop)
        plan.append("would stop: " + stop)
    if dry_run:
        return {"plan": plan, "dry_run": True}
    took, clock = {}, time.monotonic()

    def lap(step):
        nonlocal clock
        took[step], clock = time.monotonic() - clock, time.monotonic()

    # The network step first: if OSC cannot be read, nothing has been copied or set aside.
    snap_dir = state / "snapshots"
    if snapshot:
        snapshot(snap_dir, jobs)
    else:
        if not VENV_PYTHON.exists():
            raise RunError(f"the osc-api virtual environment is missing ({VENV_PYTHON})")
        done = subprocess.run([str(VENV_PYTHON), str(HERE / "osc_snapshot.py"), "--jobs", ",".join(jobs),
                               "--out", str(snap_dir)])
        if done.returncode != 0:
            raise RunError("the OSC snapshot did not complete (see above); nothing was copied or drafted")
    lap("snapshot")
    if gate:
        gate()
        lap("self-check")
    copy_in(base_src, base)
    use_edits = bool(edited_src and drafted)
    if use_edits:
        copy_in(edited_src, edited)
    moved = restart_state(state, restart) if restart else []
    draft, ev_md, evidence = build_draft(base, snap_dir, outputs, asof=asof.isoformat(), state_dir=state,
                                         jobs=jobs, edited=edited if use_edits else None,
                                         drafted=drafted if use_edits else None)
    lap("draft")
    # The kept copy is what next week's read-back compares her edits with, even if this Monday is re-run.
    delivered = deliver([Path(draft), Path(ev_md)], drop, outputs / "delivered", force=force)
    checked = verify_delivered(Path(draft), delivered[0], base)
    lap("delivery")
    return {"plan": plan, "moved": moved, "draft": draft, "evidence": evidence, "delivered": delivered,
            "found": found, "checked": checked, "took": took}


def _summary(result):
    ev = result["evidence"]
    lines = [f"Draft: {result['draft']}", "Delivered: " + ", ".join(str(p) for p in result["delivered"]),
             "Read back from the drop folder: {} jobs, {} Items rows".format(*result["checked"])]
    lines += [f"Her edits: {n}" for n in result["found"]]
    if result["moved"]:
        lines.append("State set aside: " + ", ".join(p.name for p in result["moved"]))
    for j in ev["jobs"]:
        if not j["pilot"]:
            continue
        red = sum(1 for i in j["outstanding"] if i.get("flag") == "RED")
        lines.append(f"  {j['job_no']}: {len(j['outstanding'])} open ({red} red), {len(j['resolved'])} resolved, "
                     f"{len(j['flags'])} to check")
    lines += [f"  note: {n}" for n in ev["notes"]]
    lines.append("Took " + ", ".join(f"{step} {secs:.0f} s" for step, secs in result["took"].items()))
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", help="the draft's Monday, YYYY-MM-DD (default today)")
    ap.add_argument("--jobs", default=PILOT_JOBS, help=f"pilot job numbers (default {PILOT_JOBS})")
    ap.add_argument("--restart", metavar="LABEL", help="start the state afresh, keeping the old one as .LABEL.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="say what would happen; changes nothing but the record of a passed self-check")
    ap.add_argument("--force", action="store_true", help="replace a different draft already in the drop folder")
    ap.add_argument("--no-self-check", action="store_true",
                    help="skip the self-check (only once a person has judged a failing check itself wrong)")
    ap.add_argument("--archive", default=str(ARCHIVE), help=argparse.SUPPRESS)
    ap.add_argument("--drop", default=str(DROP), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    asof = date.fromisoformat(args.asof) if args.asof else date.today()
    if args.restart and not re.fullmatch(r"[\w.-]+", args.restart):
        sys.exit("--restart LABEL may hold letters, digits, dots and dashes only")
    jobs = [j.strip() for j in args.jobs.split(",") if j.strip()]
    if asof.weekday() != 0:
        print(f"note: {asof:%d.%m.%Y} is not a Monday")
    ahead = asof + timedelta(days=60)
    if not covers(ahead):
        print(f"note: add the {ahead.year} NSW public holidays to nsw_holidays.py; from 1 January the "
              "business-day counts would miss them")
    check = None if args.no_self_check else start_self_check(RUNTIME / "state")
    gate = (lambda: print(finish_self_check(check))) if check else None
    try:
        result = run(asof, jobs, archive=Path(args.archive), drop=Path(args.drop), restart=args.restart,
                     dry_run=args.dry_run, force=args.force, gate=gate)
        if result.get("dry_run") and gate:
            gate()
    except (RunError, StateError, DraftInputError) as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 2
    finally:
        if check and "proc" in check and check["proc"].poll() is None:
            check["proc"].kill()  # the run stopped before it needed the answer
    if result.get("dry_run"):
        print("Would run (nothing changed):\n  " + "\n  ".join(result["plan"]))
        return 0
    print(_summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
