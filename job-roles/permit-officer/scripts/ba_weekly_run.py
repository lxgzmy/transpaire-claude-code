#!/usr/bin/env python3
"""The Monday BA report run in one command (workflows/ba-weekly-report.md, steps 0-2 and delivery).

  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py              # this week's Monday's draft
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --dry-run    # say what it would do
  python job-roles\\permit-officer\\scripts\\ba_weekly_run.py --restart september-test --asof 2026-11-02

Unattended (since 27 Nov 2026): a scheduled task runs ba_weekly_task.ps1, which calls this with
--scheduled at 06:30 and 12:30 each Monday to Wednesday until the Monday's draft is in the drop folder
(register_ba_weekly_task.ps1 sets it up). Whenever a run stops with no draft out, a note saying why
is left in the drop folder ("BA REPORT DRAFT - dd.mm.yyyy - NOT READY.txt") and removed once the
draft is delivered; every run, by hand or scheduled, adds a line to runtime\\permit-officer\\logs\\
ba-weekly-runs.log.

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
7. Score (the pilot measure): last week's draft as written against the base, when the two are for
   the same week, into runtime\\permit-officer\\reports\\compare-dd.mm.yyyy.md, its headline in the
   summary. A scorecard already there is kept (it may hold the review time typed into it). A
   problem scoring is said and never costs the draft.

A Monday inside the Christmas shutdown (nsw_holidays.SHUTDOWNS) drafts nothing and says when to
run; the first Monday back takes the last export before the break as its base.

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
from datetime import date, datetime, timedelta
from pathlib import Path

# abspath, not resolve(): on this server resolve() turns the mapped Z: drive into its UNC form,
# which names the file server in every path printed.
HERE = Path(os.path.abspath(__file__)).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import safe_files  # noqa: E402
from ba_report_draft import DraftInputError, StateError, STATE_FILE, STATE_PREVIOUS, build_draft  # noqa: E402
from ba_report_parse import officer_edits, parse_report  # noqa: E402
from compare_ba_report import compare, headline, render  # noqa: E402
from nsw_holidays import covers, in_shutdown, reopens  # noqa: E402

RUNTIME = REPO / "runtime" / "permit-officer"
ARCHIVE = Path(r"Z:\ADMINISTRATION\REPORTS\REPORTS\BA REPORTS")
DROP = Path(r"Z:\AI test\Permit Officer\BA Report test")
# 26044 joined on 16 Nov 2026 at the officer's request (12 Nov): the other three were nearly through.
PILOT_JOBS = "26029,26052,26001,26044"
VENV_PYTHON = REPO / "shared" / "mcp" / "osc-api" / ".venv" / "Scripts" / "python.exe"

# Her archive names vary in their spacing ("BA REPORT- 19.10.2026", "BA REPORT -13.04.2026", and on
# 16 Nov 2026 "BA REPORT -16.11. 2026", which the stricter pattern missed, so 23 Nov had no draft).
REPORT_NAME = re.compile(r"^BA\s*REPORT\s*-?\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})\s*\.xlsx$", re.I)
DRAFT_NAME = re.compile(r"^BA REPORT DRAFT - (\d{2})\.(\d{2})\.(\d{4})\.xlsx$", re.I)
# Left in the drop folder when a Monday's draft could not be made, so she sees why without asking;
# removed once that draft is delivered.
NOTICE_NAME = "BA REPORT DRAFT - {:%d.%m.%Y} - NOT READY.txt"
RUN_LOG = "ba-weekly-runs.log"
# When the scheduled task runs (register_ba_weekly_task.ps1 sets the same times; the self-check
# compares them). Each run after the draft is out does nothing.
SCHEDULE_DAYS = ("Monday", "Tuesday", "Wednesday")
SCHEDULE_TIMES = ("06:30", "12:30")


class RunError(RuntimeError):
    pass


YEAR_FOLDER = re.compile(r"^\d{4}$")


def archive_files(archive):
    """The files in the archive and in its year folders. Each January she files the year before into a
    folder named for it ("2024" made 6 Jan 2025, "2025" made 14 Jan 2026), so the first Mondays of a
    year find their base there once she has. Other folders are not read."""
    root = Path(archive)
    folders = [root] + sorted(p for p in root.iterdir() if p.is_dir() and YEAR_FOLDER.match(p.name))
    return [p for f in folders for p in f.iterdir()]


def _dated(files, pattern):
    """[(date, path)] for the ``files`` whose name matches, Excel lock files skipped."""
    out = []
    for p in files:
        m = pattern.match(p.name)
        if m and p.is_file() and not p.name.startswith("~$"):
            try:
                out.append((date(int(m.group(3)), int(m.group(2)), int(m.group(1))), p))
            except ValueError:
                continue
    return sorted(out)


def unread_reports(archive, since):
    """Reports in the archive saved after ``since`` whose name holds no date the run can read
    ("BA REPORT FINAL.xlsx"): said when the run stops, so the fix is a rename, not a guess."""
    out = []
    for p in archive_files(archive):
        n = p.name
        if (p.is_file() and n.lower().endswith(".xlsx") and not n.startswith("~$")
                and re.match(r"^BA\s*REPORT", n, re.I) and "DRAFT" not in n.upper() and not REPORT_NAME.match(n)
                and date.fromtimestamp(p.stat().st_mtime) > since):
            out.append(p)
    return sorted(out, key=lambda p: p.stat().st_mtime)


def find_base(archive, asof):
    """Her latest export dated before ``asof`` and within 7 days of it, the Christmas shutdown not
    counted (no export is made while the office is closed), or RunError."""
    before = [(d, p) for d, p in _dated(archive_files(archive), REPORT_NAME) if d < asof]
    last = before[-1][0] if before else date(2000, 1, 1)
    odd = [p for p in unread_reports(archive, last) if date.fromtimestamp(p.stat().st_mtime) < asof + timedelta(1)]
    hint = ""
    if odd:
        hint = (" The archive also holds " + ", ".join(f'"{p.name}"' for p in odd) + ", but its name has no date "
                f"the run can read; saved as \"BA REPORT - dd.mm.yyyy.xlsx\" it will be used.")
    if not before:
        raise RunError(f"no BA report dated before {asof:%d.%m.%Y} was found in {archive} or its year "
                       f"folders.{hint}")
    d, p = before[-1]
    if sum(not in_shutdown(d + timedelta(n)) for n in range(1, (asof - d).days + 1)) > 7:
        raise RunError(f"last week's BA report is not in {archive} yet: the newest one before {asof:%d.%m.%Y} is "
                       f"\"{p.name}\" ({(asof - d).days} days old), so nothing was drafted.{hint}")
    return d, p


def find_last_draft(drop, outputs, asof):
    """(her copy in the drop folder, the same draft as delivered, notes) for the latest draft before
    ``asof``: (None, None, []) when there is none, None for the delivered one when it cannot be found.

    Her copy is the file under the draft's own name, unless that is still exactly as delivered and
    another copy of the same Monday's draft beside it has been changed (a Save As, "BA REPORT DRAFT -
    26.10.2026 GR.xlsx"): then the newest changed copy is hers. The notes say so, and say when the
    draft looks open in Excel (what she has not saved cannot be read) or holds no change at all."""
    before = [(d, p) for d, p in _dated(Path(drop).iterdir(), DRAFT_NAME) if d < asof]
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


def last_week_score(drafted, base_date, reports):
    """(the draft's Monday, its scorecard path) when last week's draft as written and her report are
    for the same week, Monday to Sunday; else None. A draft from another week (the 22.10 preview
    against her 26.10 report) is not hers to be scored against."""
    m = DRAFT_NAME.match(drafted.name) if drafted else None
    if not m:
        return None
    week = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if week - timedelta(days=week.weekday()) != base_date - timedelta(days=base_date.weekday()):
        return None
    return week, Path(reports) / f"compare-{week:%d.%m.%Y}.md"


def drafted_jobs(drafted, outputs, jobs):
    """The pilot jobs last week's draft was made for, read from the evidence written beside it in runtime
    outputs. A job that joins the pilot this week is then not scored on a draft that only carried its row
    forward unchanged. ``jobs`` when that record is missing or unreadable."""
    if drafted is None:
        return list(jobs)
    record = Path(outputs) / Path(drafted).name.replace(".xlsx", "-evidence.json")
    try:
        made_for = json.loads(record.read_text(encoding="utf-8")).get("pilot_jobs")
    except (OSError, ValueError, AttributeError):
        made_for = None
    return [str(j) for j in made_for] if made_for else list(jobs)


def score_last_week(score, drafted, base, base_src, jobs):
    """Score last week's draft against her report and write the scorecard unless one is there.
    A problem is returned to be said, never raised: the score is a side report, not the draft."""
    week, card = score
    try:
        report = compare(drafted, base, jobs)
        kept = card.exists()
        if not kept:
            card.parent.mkdir(parents=True, exist_ok=True)
            card.write_text(render(report, drafted, base_src, jobs, week=week), encoding="utf-8")
        return {"week": week, "card": card, "report": report, "kept": kept, "jobs": list(jobs)}
    except Exception as exc:  # noqa: BLE001 (any failure here is reported in the summary instead)
        return {"week": week, "card": card, "error": f"{type(exc).__name__}: {exc}", "jobs": list(jobs)}


def copy_in(src, dst):
    """Copy into runtime under a fixed name; an identical file is left as it is."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return dst
    tmp = dst.with_name(dst.name + ".tmp")
    safe_files.copy(src, tmp)
    safe_files.replace(tmp, dst)
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
    for p in sorted(HERE.glob("*.py")) + sorted(HERE.glob("*.ps1")) + sorted(client.glob("*.py")):
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


def _run_suite():
    """The regression suite in the foreground: (stdout, stderr, exit code)."""
    done = subprocess.run([sys.executable, str(HERE / "regress_ba_report.py")], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return done.stdout, done.stderr, done.returncode


def finish_self_check(check):
    """Wait for the self-check; RunError when it failed. Returns its line for the summary.

    A suite that stopped without failing a check (on 27 Nov 2026, a state file the share held for a
    moment) is run once more before it counts; a failed check is never run again."""
    if "passed_before" in check:
        last = check["passed_before"]
        return f"Self-check: this code passed {last.get('passed')} checks on {last.get('on')}; not run again"
    out, err = check["proc"].communicate()
    code = check["proc"].returncode
    lines = out.splitlines()
    again = ""
    if code != 0 and not any(ln.startswith("FAIL") for ln in lines):
        first = (err.strip().splitlines() or ["it stopped with an error"])[-1]
        out, err, code = _run_suite()
        lines = out.splitlines()
        again = f"; run twice, the first stopped on {first}"
    passed = sum(1 for ln in lines if ln.startswith("PASS"))
    if code != 0:
        failed = [ln[6:].split(" — ")[0] for ln in lines if ln.startswith("FAIL")]
        why = "; ".join(failed[:3]) or (err.strip().splitlines() or ["it stopped with an error"])[-1]
        raise RunError(f"the self-check failed ({why}), so nothing was copied or drafted. The scripts need "
                       "fixing first; --no-self-check runs anyway, only once a person has judged the check "
                       "itself wrong.")
    check["record"].parent.mkdir(parents=True, exist_ok=True)
    check["record"].write_text(json.dumps({"code": check["code"], "passed": passed,
                                           "on": date.today().isoformat()}), encoding="utf-8")
    took = time.monotonic() - check["started"]
    return f"Self-check: {passed} checks passed ({took:.0f} s, beside the snapshot{again})"


def run(asof, jobs, archive=ARCHIVE, drop=DROP, runtime=RUNTIME, restart=None, dry_run=False, force=False,
        snapshot=None, gate=None):
    """The Monday run. ``snapshot(out_dir, jobs)`` replaces the production snapshot step in tests;
    ``gate()``, when given, is waited for after the snapshot and before anything is copied (the
    self-check); it stops the run by raising RunError."""
    # No draft while the office is closed for Christmas (PO-11d): she would not see it until work resumes.
    back = reopens(asof)
    if back:
        stop = (f"{asof:%d.%m.%Y} falls in the Christmas shutdown; nothing is drafted until work resumes, so "
                f"run on {back:%A %d.%m.%Y}")
        if not dry_run:
            raise RunError(stop)
        return {"plan": ["would stop: " + stop], "dry_run": True}
    reports, outputs, state = runtime / "reports", runtime / "outputs", runtime / "state"
    before_first = state / STATE_FILE.replace(".json", f".before-{asof:%d.%m.%Y}.json")
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
            f"restart: state set aside as .{restart}.json" if restart else
            "state: as it was before this Monday's first run (a re-run)" if before_first.exists() else "state: carried on",
            f"snapshot: jobs {','.join(jobs)} -> {state / 'snapshots'}",
            f"draft: BA REPORT DRAFT - {asof:%d.%m.%Y}.xlsx -> {outputs}, delivered to {drop}"]
    score = last_week_score(drafted, base_date, reports)
    scored_jobs = drafted_jobs(drafted, outputs, jobs)
    if score:
        plan.append(f"score: last week's draft ({score[0]:%d.%m.%Y}) against {base_src.name} -> {score[1]}"
                    + (" (already there: kept, the headline said again)" if score[1].exists() else ""))
        if set(scored_jobs) != set(jobs):
            plan.append(f"score: on jobs {','.join(scored_jobs)}, the ones that draft was made for "
                        f"(this week: {','.join(jobs)})")
    else:
        plan.append(f"score: none (no draft of ours for the week of {base_src.name})")
    plan += found
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
    # A run tidies items she resolved out of the state, so a re-run of this Monday starts from the state
    # as it was before its first run; otherwise what she typed on those items in earlier weeks is lost.
    current = state / STATE_FILE
    if before_first.exists():
        shutil.copyfile(before_first, current)
    else:
        state.mkdir(parents=True, exist_ok=True)
        before_first.write_text(current.read_text(encoding="utf-8") if current.exists() else "{}", encoding="utf-8")
    draft, ev_md, evidence = build_draft(base, snap_dir, outputs, asof=asof.isoformat(), state_dir=state,
                                         jobs=jobs, edited=edited if use_edits else None,
                                         drafted=drafted if use_edits else None)
    lap("draft")
    # The kept copy is what next week's read-back compares her edits with, even if this Monday is re-run.
    delivered = deliver([Path(draft), Path(ev_md)], drop, outputs / "delivered", force=force)
    checked = verify_delivered(Path(draft), delivered[0], base)
    lap("delivery")
    scored = score_last_week(score, drafted, base, base_src, scored_jobs) if score else None
    if scored:
        lap("score")
    return {"plan": plan, "moved": moved, "draft": draft, "evidence": evidence, "delivered": delivered,
            "found": found, "checked": checked, "took": took, "scored": scored}


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
    sc = result.get("scored")
    if sc and "error" in sc:
        lines.append(f"Last week ({sc['week']:%d.%m.%Y}) not scored: {sc['error']}. The draft is unaffected; "
                     "score it by hand with compare_ba_report.py")
    elif sc:
        lines.append(f"Last week ({sc['week']:%d.%m.%Y}): {headline(sc['report'])}. "
                     f"Scorecard {'kept' if sc['kept'] else 'written'}: {sc['card']}")
    if sc and set(sc["jobs"]) != set(ev.get("pilot_jobs") or []):
        lines.append(f"  scored on {', '.join(sc['jobs'])}, the jobs that draft was made for")
    lines.append("Took "+ ", ".join(f"{step} {secs:.0f} s" for step, secs in result["took"].items()))
    return "\n".join(lines)


def draft_monday(today):
    """The Monday a run drafts for when no --asof is given: this week's on a weekday, so a run on
    Tuesday after a missed Monday still makes Monday's draft; next week's at the weekend (made ahead)."""
    if today.weekday() >= 5:
        return today + timedelta(days=7 - today.weekday())
    return today - timedelta(days=today.weekday())


def _clock(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return f"{h % 12 or 12}:{m:02d} {'am' if h < 12 else 'pm'}"


def notice_text(asof, reason, scheduled, contact):
    """What she reads in the drop folder when a Monday's draft could not be made."""
    days = ", ".join(SCHEDULE_DAYS[:-1]) + " and " + SCHEDULE_DAYS[-1]
    lines = [f"No BA report draft has been made for Monday {asof:%d.%m.%Y} yet.", "", f"Why: {reason}", ""]
    if scheduled:
        lines.append(f"The run tries again at {' and '.join(_clock(t) for t in SCHEDULE_TIMES)} each {days}. "
                     "This note goes once the draft is delivered.")
    else:
        lines.append("This note goes once the draft is delivered.")
    lines.append(f"If it is still here on {SCHEDULE_DAYS[-1]} afternoon, please let {contact} know.")
    return "\r\n".join(lines) + "\r\n"


def record_run(runtime, asof, mode, outcome, detail=""):
    """One line per run in runtime\\permit-officer\\logs\\ba-weekly-runs.log, so a Monday with no draft
    shows whether the run started and where it stopped. Never fails the run."""
    try:
        log = Path(runtime) / "logs" / RUN_LOG
        log.parent.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | Monday {asof:%d.%m.%Y} | {mode} | {outcome}"
        with log.open("a", encoding="utf-8") as f:
            f.write(line + (f" | {' '.join(str(detail).split())}" if detail else "") + "\n")
    except OSError:
        pass


def weekly(asof, jobs, archive=ARCHIVE, drop=DROP, runtime=RUNTIME, scheduled=False, contact=None, restart=None,
           dry_run=False, force=False, self_check=True, snapshot=None):
    """One run as the command line asks for it: (exit code, what to print). Scheduled runs (Monday to
    Wednesday, twice a day) do nothing once the Monday's draft is in the drop folder. Whenever a run
    stops with no draft there, a note saying why is left there for her, and removed once the draft is
    delivered. Every run is recorded in the run log, an unexpected error included."""
    mode = "dry run" if dry_run else "scheduled" if scheduled else "by hand"
    contact = contact or "the person who runs the AI pilot"
    drop, runtime = Path(drop), Path(runtime)
    there = drop / f"BA REPORT DRAFT - {asof:%d.%m.%Y}.xlsx"
    notice = drop / NOTICE_NAME.format(asof)
    if scheduled and not dry_run and not force and there.exists():
        notice.unlink(missing_ok=True)
        record_run(runtime, asof, mode, "nothing to do", f"{there.name} is already in the drop folder")
        return 0, f"{there.name} is already in the drop folder; nothing to do"
    if scheduled and reopens(asof):
        record_run(runtime, asof, mode, "shutdown", f"no draft until {reopens(asof):%d.%m.%Y}")
        return 0, f"{asof:%d.%m.%Y} falls in the Christmas shutdown; nothing is drafted"
    check = start_self_check(runtime / "state") if self_check else None
    gate = (lambda: print(finish_self_check(check), flush=True)) if check else None
    try:
        result = run(asof, jobs, archive=Path(archive), drop=drop, runtime=runtime, restart=restart,
                     dry_run=dry_run, force=force, snapshot=snapshot, gate=gate)
        if result.get("dry_run") and gate:
            gate()
    except Exception as exc:  # noqa: BLE001 (every stop is recorded and, with no draft out, said to her)
        known = isinstance(exc, (RunError, StateError, DraftInputError))
        reason = str(exc) if known else f"the run hit an unexpected error ({type(exc).__name__}: {exc})"
        said = ""
        if not dry_run and not there.exists() and not reopens(asof):
            try:
                notice.write_text(notice_text(asof, reason, scheduled, contact), encoding="utf-8")
                said = f"\nA note saying why is in the drop folder: {notice}"
            except OSError as werr:
                said = f"\nThe note for the drop folder could not be written ({werr})"
        record_run(runtime, asof, mode, "stopped", reason)
        if not known:
            import traceback
            traceback.print_exc()
        return (2 if known else 3), f"stopped: {reason}{said}"
    finally:
        if check and "proc" in check and check["proc"].poll() is None:
            check["proc"].kill()  # the run stopped before it needed the answer
    if result.get("dry_run"):
        record_run(runtime, asof, mode, "planned")
        return 0, "Would run (nothing changed):\n  " + "\n  ".join(result["plan"])
    notice.unlink(missing_ok=True)
    record_run(runtime, asof, mode, "delivered", Path(result["draft"]).name)
    return 0, _summary(result)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--asof", help="the draft's Monday, YYYY-MM-DD (default this week's Monday; at the weekend, "
                                   "the coming one)")
    ap.add_argument("--scheduled", action="store_true",
                    help="the unattended run (ba_weekly_task.ps1): nothing to do once the draft is delivered")
    ap.add_argument("--contact", help="who the drop-folder note tells her to ask when the draft is late")
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
    sys.stderr.reconfigure(encoding="utf-8")
    asof = date.fromisoformat(args.asof) if args.asof else draft_monday(date.today())
    if args.restart and not re.fullmatch(r"[\w.-]+", args.restart):
        sys.exit("--restart LABEL may hold letters, digits, dots and dashes only")
    jobs = [j.strip() for j in args.jobs.split(",") if j.strip()]
    print(f"{datetime.now():%d.%m.%Y %H:%M}: the draft for Monday {asof:%d.%m.%Y}"
          + (" (scheduled run)" if args.scheduled else ""), flush=True)
    if asof.weekday() != 0:
        print(f"note: {asof:%d.%m.%Y} is not a Monday")
    ahead = asof + timedelta(days=60)
    if not covers(ahead):
        print(f"note: add the {ahead.year} NSW public holidays to nsw_holidays.py; from 1 January the "
              "business-day counts would miss them")
    code, text = weekly(asof, jobs, archive=Path(args.archive), drop=Path(args.drop), scheduled=args.scheduled,
                        contact=args.contact, restart=args.restart, dry_run=args.dry_run, force=args.force,
                        self_check=not args.no_self_check)
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
