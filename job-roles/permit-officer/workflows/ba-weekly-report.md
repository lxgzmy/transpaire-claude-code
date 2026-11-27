# Workflow: weekly BA report pre-population

Draft the Monday building-approval status report so the permit officer
reviews and corrects instead of compiling from scratch. Rules: `PO-9`,
`PO-10`, `PO-11`; HITL per the role `CLAUDE.md` (draft only — the officer
finalises and distributes).

## Today (manual baseline)

Every Monday the permit officer starts from last week's Excel, then walks
OSC job-by-job (activities, alerts, Document Manager descriptions), the QLD
certifier portal, and the mailbox (NSW) to re-derive each job's outstanding
RFI items, typing them in red. Printed copies marked during the week feed
the update. This is the single most time-consuming task named at discovery.
The report itself is an OSC Executive Reporter export (saved definition,
"BA lodged jobs only") — the export mechanics are documented in the AI
testing folder (see `../reference/README.md`).

## Target flow

1. **Carry forward.** Read last week's report from the runtime reports
   folder (`runtime\permit-officer\reports\`); parse rows (job number,
   client, site, dates, outstanding items).
2. **Read OSC per job** (via the `osc-api-prod` MCP, reads only): job activities
   and their completion state, alerts raised/acknowledged during the week,
   Document Manager entries — including the energy application → energy
   report rename that encodes energy status (PO-8a).
3. **Read the nominated mailbox** for NSW jobs (read-only, once scope and
   consent are confirmed): match correspondence to jobs, note items sent to
   the certifier during the week. Mailbox evidence is additive — the draft
   works from OSC alone and improves when the mailbox lands.
4. **Draft the new report**: mark items evidenced complete as RESOLVED
   (shown once, then dropped), keep the rest, track engineering and
   covenant from their columns (PO-11b), and write one row per item on the
   **Items** sheet — *Assigned to*, *Date submitted*, *Date resolved*, *Days
   outstanding* in NSW business days — with the YELLOW/RED flag by tier
   (Internal 10, Energy 10, External consultants 20, Council 30; PO-11a,
   confirmed on issue #29) or by the item's own limit (engineering 15 while
   the engineer designs it and 10 in Transpire's internal review, PO-11c;
   covenant 10, an amended DA 60, PO-11b). The main sheet and the RFI list
   stay hers: the export, column for column, plus RESOLVED lines.
5. **Evidence bundle**: for every removed or added item, cite the OSC
   activity/alert/document or email that justifies it. Low-confidence
   changes are flagged, not silently applied (org HITL rule).
6. **Human review**: the permit officer corrects the draft's Items sheet;
   her changes are read back the next Monday and kept from then on, while
   her own export stays the base.

## Explicitly out of scope

- Writing anything to OSC. The report only reads; the officer's OSC
  record-keeping through Claude is its own workflow (`osc-updates.md`).
- Reading or operating the QLD certifier portal (PO-14) — portal-only facts
  stay manual and are marked as such in the draft.
- Deciding whether an RFI item is satisfied when evidence conflicts —
  flag for the officer (PO-13).

## How to run (v0.4 — the pilot, from week 1 on Monday 2 November 2026)

Pilot jobs (issue #29, 10 Sep 2026): **26029, 26052, 26001**, and **26044**
from Monday 16 Nov 2026. The officer asked for another NSW job on 12 Nov,
when 26001 was the only pilot job with items still open; 26044 had five,
its RFI received 23 Oct.

**It runs by itself (since 27 Nov 2026).** Monday 23 November had no
draft: nobody started the run that day, and it would have stopped anyway,
because her 16 Nov export was saved as `BA REPORT -16.11. 2026.xlsx`, a
spacing the archive pattern did not read, and a stopped run left nothing
to show. Now:

- A scheduled task (`scripts\register_ba_weekly_task.ps1`, set up once by
  a person, who types the account's password) runs
  `scripts\ba_weekly_task.ps1` at 06:30 and 12:30 each Monday, Tuesday and
  Wednesday, whether or not anyone is signed in; a run missed while the
  server was off starts when it is back. The wrapper maps `Z:` for the run
  and calls `ba_weekly_run.py --scheduled`, which drafts this week's
  Monday and does nothing once that draft is in the drop folder. It writes
  what the command a person runs writes, nothing more.
- Archive names are read whatever their spacing, and a report saved with
  no readable date in its name is named in the stop, so the fix is a
  rename.
- Whenever a run stops with no draft out for that Monday, it leaves
  `BA REPORT DRAFT - dd.mm.yyyy - NOT READY.txt` in the drop folder saying
  why, when it tries again and who to tell (`-Contact` when the task is
  registered). The note goes once the draft is delivered. An unexpected
  error is caught and said the same way.
- Every run adds a line to `runtime\permit-officer\logs\ba-weekly-runs.log`
  (when, which Monday, scheduled or by hand, the outcome and why); a
  scheduled run's full output is in `ba-weekly-<date>.log` beside it.
- No stop is silent, even one Python never gets to report (since the
  27 Nov 2026 review). If Python crashes before it can say why (a missing
  package, a broken import) or cannot be started at all, the wrapper
  leaves the same note and writes the run-log line itself. A checkout that
  is not on `main` still runs, since a draft from that code is better than
  none, but each run then adds a `warning` line to the run log.

To set the task up, or change the contact, in your own PowerShell 7 window
from the `Z:` checkout (`-Show` first says what it would register):

```
pwsh job-roles\permit-officer\scripts\register_ba_weekly_task.ps1 -Contact "<first name>" -Show
pwsh job-roles\permit-officer\scripts\register_ba_weekly_task.ps1 -Contact "<first name>"
```

**Is it on track?** One read-only look, any time, from the `Z:` checkout:

```
pwsh job-roles\permit-officer\scripts\ba_weekly_status.ps1
```

It says `OK` or `NEEDS A PERSON` (exit code 0 or 1) with each reason, and
checks what the drop-folder note cannot: the task is registered, enabled,
logs on with a stored password and starts this checkout's wrapper; the
latest 06:30 or 12:30 slot actually started; the last result in words;
this week's draft is in the drop folder, or the note's reason; the checkout
the task runs is on `main` and not behind `origin/main` as last fetched.
Worth a look each Monday morning until the pilot ends.

**No draft on a Monday?** Run the status check first. Then:

| It says | Do this |
|---|---|
| The note's reason (last week's report not in the archive, OSC snapshot, self-check) | Fix what it names; the next slot retries, or run `ba_weekly_run.py` by hand. |
| The run due at a slot has not started | Task Scheduler, the task's History tab. A changed password for the task's account shows as a sign-in failure: run `register_ba_weekly_task.ps1` again. |
| Z: could not be mapped (result 4) | The share was unreachable; the next slot retries. |
| The checkout is on another branch | `git checkout main` and `git pull` in the shared checkout (after its owner has committed their work). |
| Not registered, disabled, or other triggers | Run `register_ba_weekly_task.ps1` again. |

By hand, from the repo root, any day: with no `--asof` it drafts this
week's Monday (at the weekend, the coming one), so a late run still makes
Monday's draft.

```
python job-roles\permit-officer\scripts\ba_weekly_run.py --dry-run
python job-roles\permit-officer\scripts\ba_weekly_run.py
```

It does steps 0 to 2 below, delivers the draft and its evidence note to
the drop folder, and scores last week's draft against her report (step 4).
A problem scoring is said and never costs the draft. It stops, with nothing half done, when last week's export
is not in the archive yet (it never falls back to an older one), when the
snapshot fails, or when the draft for that Monday in the drop folder has been
changed since it was delivered (she may be working on it; `--force` only once
you know it can go). Re-running a Monday is fine while the draft there is
still exactly what was delivered: a re-run starts from the state as it was
before that Monday's first run (`state\ba-items-first-seen.before-dd.mm.yyyy.json`,
kept by the first run), so it gives the same draft apart from what changed in
OSC. It keeps a copy of what it delivered in `outputs\delivered\`, so next
week her edits are read against exactly what she was given.

Checks it makes on every run (since 31 Oct 2026), each with a regression
check behind it:

- **Self-check first.** The regression suite runs beside the snapshot and
  is waited for before anything is copied: code that fails its own checks
  drafts nothing. Code that already passed (the same scripts, the same OSC
  client, the same Python; recorded in `state\self-check.json`) is not
  checked again, so it costs time only on the first Monday after a change.
  `--no-self-check` is for when a person has judged a failing check itself
  wrong. A suite that stops without failing a check is run once more
  before it counts (27 Nov 2026: a state file the share held for a moment).
- **A held file is tried again.** Every file the run puts in place on the
  share (the state, the snapshots, the copies into runtime and the drop
  folder) is swapped or copied in again for about five seconds when
  Windows says another process holds it (`scripts\safe_files.py`); any
  other error stops the run as before.
- **The network step first.** The OSC snapshot runs before the base is
  copied or the state set aside, and retries a timeout, a dropped
  connection or a busy answer twice (2 s, then 5 s); any other error stops
  it at once. The jobs are read side by side, at most four requests at a
  time (about 7 s for the pilot instead of 14).
- **Her copy found, or its absence said.** If the draft under its own name
  is exactly as delivered but another copy of that Monday's draft in the
  drop folder was changed (a Save As), the newest changed copy is read. A
  draft open in Excel when the run starts (unsaved changes cannot be read)
  and a draft with no changes at all are both said in the summary.
- **A restart is done once.** Running a `--restart` command again stops
  before any network step and says so; leave `--restart` off to redo the
  week.
- **No draft over the Christmas shutdown (PO-11d).** A Monday inside the
  break stops before any network step and names the day to run (2026-27:
  no runs on 28 December or 4 January; run on Monday 11 January 2027).
  The first Monday back takes her last export before the break (21
  December) as its base and reads her edits on the last draft she had.
- **Delivery read back.** The delivered draft is compared byte for byte
  with the one written, checked to hold the base's jobs in order, and read
  back the way next Monday will read it.
- The summary ends with how long each step took. Sixty days before the
  NSW holiday table runs out, every run says to add the next year. From
  1 December to 31 January, every run says so while that break's
  Christmas shutdown dates are not set (PO-11d).

The steps, for reference or to run by hand:

0. **Base report.** Copy the officer's latest export from the BA REPORTS
   archive under `Z:\ADMINISTRATION` into `runtime\permit-officer\reports\`
   as `BA REPORT - dd.mm.yyyy.xlsx` (the archive's own spacing varies; the
   date in the name is what matters). Copy last week's draft as she left it
   in the drop folder (`Z:\AI test\Permit Officer\BA Report test`) into the
   same folder as `BA REPORT DRAFT - dd.mm.yyyy (officer-edited).xlsx`.
1. **Snapshot step (read-only, production OSC):**

   ```
   "shared\mcp\osc-api\.venv\Scripts\python.exe" ../scripts/osc_snapshot.py
          --jobs 26029,26052,26001,26044
          --out runtime\permit-officer\state\snapshots
   ```

   writes one JSON per job (job, activities, alerts, documents — the
   queries in `../reference/osc-field-map.md`) through the same client and
   credentials the `osc-api-prod` MCP server uses, GET only, after checking
   the connection is the live system. It prints counts and dates, never
   names. It reads every job before writing any file, so a run that stops
   part-way writes nothing. A pilot job that is not yet lodged is not a row in the export;
   the draft notes it, never fabricates a row.
2. **Draft step (deterministic, no network):**

   ```
   python ../scripts/ba_report_draft.py
          --prev "runtime\permit-officer\reports\BA REPORT - dd.mm.yyyy.xlsx"
          --snapshots runtime\permit-officer\state\snapshots
          --out runtime\permit-officer\outputs
          --state runtime\permit-officer\state
          --jobs 26029,26052,26001,26044
          --edited "runtime\permit-officer\reports\BA REPORT DRAFT - dd.mm.yyyy (officer-edited).xlsx"
   ```

   Produces the draft workbook — main sheet = the base's columns exactly
   (located by header text, so the 28 Sep 2026 template's engineering and
   covenant columns carry through), plus an **Items** sheet with one row
   per outstanding item — layout in `../fixtures/ba-report-layout.md`, and
   the evidence bundle (`…-evidence.md` / `.json`). Pilot rows are aged and
   coloured; every other row is carried forward verbatim with no Items
   rows. Carried values are never overwritten; an item resolves only on
   fresh completion evidence and is shown once on a `RESOLVED` line;
   everything else is kept and flagged. An application or request document
   never resolves an item, and an approval document never does while the
   item's OSC step is still open (kept, flagged "still open"). An item name
   that fits two evidence rules, or names an engineering discipline OSC
   does not track (hydraulic, civil…), gets no rule and is flagged for the
   officer. A snapshot taken before the base report, or for another job, is
   not used (row carried, flagged). RFI-cell text that is not a `PENDING`
   list is carried verbatim and flagged. Per-item state (first seen, date
   submitted, assigned-to, and what the AI wrote last time) persists in
   `state\ba-items-first-seen.json`, swapped in whole each run with the run
   before kept as `ba-items-first-seen.prev.json`; an unreadable state file
   stops the run rather than starting afresh.
   `--edited` reads her changes from last week's draft (compared with the
   draft as written, found in `--out` by the same name, or `--drafted`).
3. **Review (the officer):** correct the draft on the **Items sheet**, in
   the drop folder, and save it there — and keep typing the PENDING list on
   the main sheet as today. Type the real *Assigned to* and *Date
   submitted* where the draft guessed (`⚠`, "assumed", or a date from a
   document filed on or before the BA lodgement, which may be the original
   rather than what the RFI asked for again); empty *Date
   submitted* for an item that has not gone out yet (NOT SUBMITTED, no
   days counted); type *Date resolved* to close an item; write anything
   she wants kept in *Notes* (hers, carried week to week); *Draft notes*
   are rewritten every run. One row per item, no merged or multi-line
   cells. Her values win and stick from then on. What she types is as at
   that draft's Monday (her words, 20 Nov 2026: "the notes reflect the
   jobs status at 16/11"), so when OSC later shows a newer step on the
   item (a lodgement, an order, a completed step in its chain), the row
   is flagged: "since your entries (as at dd/mm/yyyy), OSC shows ...:
   please check Assigned to and Notes". Her values stay until she
   changes the row on a later draft, which dates them afresh; items
   tracked from their columns already start a new cycle instead. Each row's *Draft notes*
   starts with what changed since the draft she checked ("new this
   week", "since last week: now RED (was YELLOW)", "after your change"
   when it follows her own edit, or "no change since last week"), so she
   can pass over the rows that did not move. A day count in her own note
   that differs from the row's limit ("council says 20 days") is pointed
   out on the row and in the evidence note, so a rule she writes down is
   not missed.
4. **Compare (the pilot metric):** the Monday run does this itself (since
   9 Nov 2026). Her report from the archive is the next Monday's base, so
   that run scores last week's draft as written against it, when the two
   are for the same week (Monday to Sunday), and says the headline in its
   summary. The scorecard, `runtime\permit-officer\reports\compare-dd.mm.yyyy.md`
   (dated by the draft's Monday), holds matched / missed / extra items per
   pilot job and the "% correctly pre-populated" headline (criterion ≥ 90 %).
   Last week's draft is scored on the jobs it was made for (its
   `-evidence.json` in runtime outputs says which), so a job added to the
   pilot this week is first scored the week after; the summary says when
   the two lists differ. Record the officer's review time (target < 30 min) and "unapproved
   writes: 0" by hand in that file; a re-run keeps the file as it is. To
   score another pair by hand:

   ```
   python ../scripts/compare_ba_report.py
          --draft "runtime\permit-officer\outputs\delivered\BA REPORT DRAFT - dd.mm.yyyy.xlsx"
          --actual "runtime\permit-officer\reports\BA REPORT - dd.mm.yyyy.xlsx"
          --jobs 26029,26052,26001,26044
   ```
5. **Next base:** her next export from the archive (step 0), **keeping the
   `BA REPORT - dd.mm.yyyy.xlsx` name** — the date in the filename is what
   the drafter uses as "since"; without it, evidence freshness falls back
   to asof − 7 days.

### Week 1 restart (Monday 2 November 2026, agreed with the officer 27 Oct)

The first week starts clean: nothing from the September test is carried,
only the corrections she typed on the 22.10.2026 preview. From the repo
root, check first, then run:

```
python job-roles\permit-officer\scripts\ba_weekly_run.py --asof 2026-11-02 --restart september-test --dry-run
python job-roles\permit-officer\scripts\ba_weekly_run.py --asof 2026-11-02 --restart september-test
```

`--restart` renames the state to `ba-items-first-seen.september-test.json`
(nothing is deleted). Her 22.10.2026 edits are read from the drop folder
against `outputs\BA REPORT DRAFT - 22.10.2026.xlsx`.

**Done on 31 Oct 2026 at 10:49** (the merged v0.4 with engineering stages,
a same-day production snapshot): the 02.11.2026 draft is in the drop
folder, identical to the kept copy, and reads back cleanly. Running the
command again stops before any network step, saying the restart is done.
From Monday 9 November, run the plain command above.

Rehearsed on 27 Oct 2026 with the real archive, a copy of the drop folder
and state, and a same-day production snapshot: all 13 of her changed rows
were read back. Her renamed item kept its values, and the main sheet
differed from her export only where OSC filled a blank BA Received.

Regression: `python ../scripts/regress_ba_report.py` (synthetic data only).

## Build gates

1. **OSC access — CLEARED.** The `osc-api-prod` MCP server reads the
   production OnSite Companion (since 13 Oct 2026; before that the reads came
   from a dev copy frozen on 21 Aug 2026; see `.claude/skills/osc-api/`). This
   workflow makes no OSC change (`osc-updates.md` does, on the officer's yes). Still
   required before code: a **field-mapping pass** against real jobs —
   how to enumerate BA-stage jobs (the Executive Reporter filter's
   equivalent), activity completion semantics, alert recipients and
   timestamps, document naming — recorded de-identified in
   `../reference/osc-field-map.md`.
2. **Report template agreement — CLEARED (issue #29, 10 Sep 2026).** The
   owner confirmed the four per-item columns and the tiered business-day
   thresholds (PO-11a); the agreed layout is recorded in
   `../fixtures/ba-report-layout.md` and exercised by the synthetic
   regression. Six assumed defaults (Certifier and Client tiers, water
   authorities, NSW holidays, one-cycle RESOLVED display, row-level fill)
   are listed on #29 for confirmation; each is a config change, not a
   redesign.
3. **Mailbox access — CLEARED (14 Sep 2026); wiring PENDING.** The owner
   nominated the permits mailbox for NSW certifier correspondence, IT
   granted the AI account read-only access, and an `outlook_email_search`
   scoped to that mailbox was verified working on 22 Oct 2026. The pilot
   still runs from OSC alone: extending the snapshot with an `emails`
   array and adding `done_emails` evidence to `FAMILIES` is a separate PR.

## Success measure

Monday compilation time for the officer drops from hours to a review pass;
zero missed outstanding items versus the manual baseline over a 4-week
parallel run. Pilot acceptance (issue #29): at least 90 per cent of the
officer's outstanding items correctly pre-populated, officer review under
30 minutes, zero unapproved writes — scored each Monday by the run
(`../scripts/compare_ba_report.py`) on the pilot jobs.
