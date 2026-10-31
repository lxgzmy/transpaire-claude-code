#!/usr/bin/env python3
"""The Monday BA report run in one command (workflows/ba-weekly-report.md, steps 0-2 and delivery).

  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py              # today's draft
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --dry-run    # say what it would do
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --restart september-test --asof 2026-11-02

In order, stopping at the first problem with nothing half done:

1. Base: the officer's latest export in the BA REPORTS archive dated before the draft's Monday and
   no more than 7 days before it (the archive's spacing varies: "BA REPORT- 19.10.2026",
   "BA REPORT -13.04.2026"), copied into runtime\\permit-officer\\reports\\ under the standard name.
   An older one is never used in its place.
2. Her edits: last week's draft as she left it in the drop folder, copied beside it as
   "(officer-edited)" and read against the same draft as written (runtime outputs).
3. --restart LABEL only: the state file is renamed ba-items-first-seen.LABEL.json (nothing deleted),
   so the week starts clean apart from her edits.
4. Snapshot: osc_snapshot.py under the osc-api virtual environment (read-only, production).
5. Draft: ba_report_draft.build_draft into runtime\\permit-officer\\outputs\\.
6. Delivery: the draft and its evidence note copied to the drop folder. A file already there under
   that name is never overwritten (she may have started on it) unless --force.

Read-only on the archive; writes only under runtime\\ and the agreed drop folder.
"""
import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# abspath, not resolve(): on this server resolve() turns the mapped Z: drive into its UNC form,
# which names the file server in every path printed.
HERE = Path(os.path.abspath(__file__)).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from ba_report_draft import DraftInputError, StateError, STATE_FILE, STATE_PREVIOUS, build_draft  # noqa: E402

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
    """(edited copy in the drop folder, the same draft as delivered) for the latest draft before ``asof``,
    or (None, None) when there is none, or None for the delivered one when it cannot be found."""
    before = [(d, p) for d, p in _dated(drop, DRAFT_NAME) if d < asof]
    if not before:
        return None, None
    _, edited = before[-1]
    for drafted in (Path(outputs) / "delivered" / edited.name, Path(outputs) / edited.name):
        if drafted.exists():
            return edited, drafted
    return edited, None


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


def run(asof, jobs, archive=ARCHIVE, drop=DROP, runtime=RUNTIME, restart=None, dry_run=False, force=False,
        snapshot=None):
    """The Monday run. ``snapshot(out_dir, jobs)`` replaces the production snapshot step in tests."""
    reports, outputs, state = runtime / "reports", runtime / "outputs", runtime / "state"
    base_date, base_src = find_base(archive, asof)
    base = reports / f"BA REPORT - {base_date:%d.%m.%Y}.xlsx"
    edited_src, drafted = find_last_draft(drop, outputs, asof)
    edited = reports / edited_src.name.replace(".xlsx", " (officer-edited).xlsx") if edited_src else None
    plan = [f"base: {base_src.name} -> {base}",
            (f"her edits: {edited_src.name} (drop folder), read against {drafted}" if drafted else
             f"her edits: {edited_src.name} found but the draft as written is not in {outputs}; not read"
             if edited_src else "her edits: no earlier draft in the drop folder"),
            f"restart: state set aside as .{restart}.json" if restart else "state: carried on",
            f"snapshot: jobs {','.join(jobs)} -> {state / 'snapshots'}",
            f"draft: BA REPORT DRAFT - {asof:%d.%m.%Y}.xlsx -> {outputs}, delivered to {drop}"]
    if dry_run:
        return {"plan": plan, "dry_run": True}
    copy_in(base_src, base)
    use_edits = bool(edited_src and drafted)
    if use_edits:
        copy_in(edited_src, edited)
    moved = restart_state(state, restart) if restart else []
    snap_dir = state / "snapshots"
    if snapshot:
        snapshot(snap_dir, jobs)
    else:
        if not VENV_PYTHON.exists():
            raise RunError(f"the osc-api virtual environment is missing ({VENV_PYTHON})")
        done = subprocess.run([str(VENV_PYTHON), str(HERE / "osc_snapshot.py"), "--jobs", ",".join(jobs),
                               "--out", str(snap_dir)])
        if done.returncode != 0:
            raise RunError("the OSC snapshot did not complete (see above); nothing was drafted")
    draft, ev_md, evidence = build_draft(base, snap_dir, outputs, asof=asof.isoformat(), state_dir=state,
                                         jobs=jobs, edited=edited if use_edits else None,
                                         drafted=drafted if use_edits else None)
    # The kept copy is what next week's read-back compares her edits with, even if this Monday is re-run.
    delivered = deliver([Path(draft), Path(ev_md)], drop, outputs / "delivered", force=force)
    return {"plan": plan, "moved": moved, "draft": draft, "evidence": evidence, "delivered": delivered}


def _summary(result):
    ev = result["evidence"]
    lines = [f"Draft: {result['draft']}", "Delivered: " + ", ".join(str(p) for p in result["delivered"])]
    if result["moved"]:
        lines.append("State set aside: " + ", ".join(p.name for p in result["moved"]))
    for j in ev["jobs"]:
        if not j["pilot"]:
            continue
        red = sum(1 for i in j["outstanding"] if i.get("flag") == "RED")
        lines.append(f"  {j['job_no']}: {len(j['outstanding'])} open ({red} red), {len(j['resolved'])} resolved, "
                     f"{len(j['flags'])} to check")
    lines += [f"  note: {n}" for n in ev["notes"]]
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", help="the draft's Monday, YYYY-MM-DD (default today)")
    ap.add_argument("--jobs", default=PILOT_JOBS, help=f"pilot job numbers (default {PILOT_JOBS})")
    ap.add_argument("--restart", metavar="LABEL", help="start the state afresh, keeping the old one as .LABEL.json")
    ap.add_argument("--dry-run", action="store_true", help="say what would happen; change nothing")
    ap.add_argument("--force", action="store_true", help="replace a different draft already in the drop folder")
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
    try:
        result = run(asof, jobs, archive=Path(args.archive), drop=Path(args.drop), restart=args.restart,
                     dry_run=args.dry_run, force=args.force)
    except (RunError, StateError, DraftInputError) as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 2
    if result.get("dry_run"):
        print("Would run (nothing changed):\n  " + "\n  ".join(result["plan"]))
        return 0
    print(_summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
