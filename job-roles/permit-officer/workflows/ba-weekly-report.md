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
   confirmed on issue #29) or by the item's own limit (engineering and
   covenant 10, an amended DA 60; PO-11b). The main sheet and the RFI list
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

Pilot jobs (issue #29, 10 Sep 2026): **26029, 26052, 26001**. Each Monday
for 3–4 weeks, from the repo root:

```
python job-roles\permit-officer\scripts\ba_weekly_run.py --dry-run
python job-roles\permit-officer\scripts\ba_weekly_run.py
```

It does steps 0 to 2 below and delivers the draft and its evidence note to
the drop folder. It stops, with nothing half done, when last week's export
is not in the archive yet (it never falls back to an older one), when the
snapshot fails, or when the draft for that Monday in the drop folder has been
changed since it was delivered (she may be working on it; `--force` only once
you know it can go). Re-running a Monday is fine while the draft there is
still exactly what was delivered. It keeps a copy of what it delivered in `outputs\delivered\`, so next
week her edits are read against exactly what she was given. The steps, for
reference or to run by hand:

0. **Base report.** Copy the officer's latest export from the BA REPORTS
   archive under `Z:\ADMINISTRATION` into `runtime\permit-officer\reports\`
   as `BA REPORT - dd.mm.yyyy.xlsx` (the archive's own spacing varies; the
   date in the name is what matters). Copy last week's draft as she left it
   in the drop folder (`Z:\AI test\Permit Officer\BA Report test`) into the
   same folder as `BA REPORT DRAFT - dd.mm.yyyy (officer-edited).xlsx`.
1. **Snapshot step (read-only, production OSC):**

   ```
   "shared\mcp\osc-api\.venv\Scripts\python.exe" ../scripts/osc_snapshot.py
          --jobs 26029,26052,26001
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
          --jobs 26029,26052,26001
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
   submitted* where the draft guessed (`⚠`, "assumed"); empty *Date
   submitted* for an item that has not gone out yet (NOT SUBMITTED, no
   days counted); type *Date resolved* to close an item; write anything
   she wants kept in *Notes* (hers, carried week to week); *Draft notes*
   are rewritten every run. One row per item, no merged or multi-line
   cells. Her values win and stick from then on.
4. **Compare (the pilot metric):** once the officer's real Monday report
   exists,

   ```
   python ../scripts/compare_ba_report.py
          --draft "runtime\permit-officer\outputs\BA REPORT DRAFT - dd.mm.yyyy.xlsx"
          --actual "runtime\permit-officer\reports\BA REPORT - dd.mm.yyyy.xlsx"
          --jobs 26029,26052,26001
   ```

   writes `runtime\permit-officer\reports\compare-dd.mm.yyyy.md` with
   matched / missed / extra items per pilot job and the "% correctly
   pre-populated" headline (criterion ≥ 90 %). Record the officer's review
   time (target < 30 min) and "unapproved writes: 0" by hand in that file.
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
30 minutes, zero unapproved writes — scored per Monday by
`../scripts/compare_ba_report.py` on the three pilot jobs.
