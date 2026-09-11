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
2. **Read OSC per job** (via the read-only `osc-api` MCP): job activities
   and their completion state, alerts raised/acknowledged during the week,
   Document Manager entries — including the energy application → energy
   report rename that encodes energy status (PO-8a).
3. **Read the nominated mailbox** for NSW jobs (read-only, once scope and
   consent are confirmed): match correspondence to jobs, note items sent to
   the certifier during the week. Mailbox evidence is additive — the draft
   works from OSC alone and improves when the mailbox lands.
4. **Draft the new report**: mark items evidenced complete as RESOLVED
   (shown once, then dropped), keep the rest, add newly detected items, and
   populate the four per-item columns L–O — *Assigned to*, *Date
   submitted*, *Date resolved*, *Days outstanding* in NSW business days —
   with the YELLOW/RED flag by tier (Internal 10, Energy 10, External
   consultants 20, Council 30; PO-11a, confirmed on issue #29).
5. **Evidence bundle**: for every removed or added item, cite the OSC
   activity/alert/document or email that justifies it. Low-confidence
   changes are flagged, not silently applied (org HITL rule).
6. **Human review**: the permit officer corrects the draft; the corrected
   version becomes next week's carry-forward base.

## Explicitly out of scope

- Writing anything to OSC.
- Reading or operating the QLD certifier portal (PO-14) — portal-only facts
  stay manual and are marked as such in the draft.
- Deciding whether an RFI item is satisfied when evidence conflicts —
  flag for the officer (PO-13).

## How to run (v0.2 — the pilot cycle)

Pilot jobs (issue #29, 10 Sep 2026): **26029, 26052, 26001**. Each Monday
for 3–4 weeks:

1. **Snapshot step (Claude + `osc-api` MCP, read-only).** For each pilot
   job: resolve the contract number to its `jobID`, read activities (add
   `jobActivityID` to the `$select`), alerts and documents (queries in
   `../reference/osc-field-map.md`), and save one JSON per job to
   `runtime\permit-officer\state\snapshots\<jobno>.json` (shape documented in
   `../scripts/ba_report_draft.py`). A pilot job that is not yet lodged
   (26052 until its *Submit … for Building Approval* activity completes) is
   not a row in the export; the draft notes it, never fabricates a row.
2. **Draft step (deterministic, no network):**

   ```
   python ../scripts/ba_report_draft.py
          --prev "runtime\permit-officer\reports\BA REPORT - dd.mm.yyyy.xlsx"
          --snapshots runtime\permit-officer\state\snapshots
          --out runtime\permit-officer\outputs
          --state runtime\permit-officer\state
          --jobs 26029,26052,26001
   ```

   Produces the draft workbook (A–K unchanged, plus L–O per item — layout
   in `../fixtures/ba-report-layout.md`) and the evidence bundle
   (`…-evidence.md` / `.json`). Pilot rows are aged and coloured; every
   other row is carried forward verbatim with L–O blank. Carried values are
   never overwritten; an item resolves only on fresh completion evidence and
   is shown once on a `RESOLVED` line; everything else is kept and flagged.
   Per-item state (first seen, date submitted, assigned-to, and what the AI
   wrote last time) persists in `state\ba-items-first-seen.json`.
3. **Review (the officer):** correct the draft — type the real *Assigned
   to* and *Date submitted* where the draft guessed (`⚠`, `(assumed)`) —
   and distribute as today. **Week 1 is a data-entry week**: every carried
   item's date is assumed from the base report and flagged until typed.
   Officer-typed values win and stick from then on, even if a later base is
   a plain A–K export.
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
5. **Next base:** the officer files the copy they want as next week's base
   into `runtime\permit-officer\reports\`, **keeping the
   `BA REPORT - dd.mm.yyyy.xlsx` name** — the date in the filename is what
   the drafter uses as "since"; without it, evidence freshness falls back
   to asof − 7 days.

Regression: `python ../scripts/regress_ba_report.py` (synthetic data only).

## Build gates

1. **OSC access — CLEARED.** The read-only `osc-api` MCP server is live
   (project-scoped, writes disabled; see `.claude/skills/osc-api/`). Still
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
3. **Mailbox access — PENDING IT.** The owner nominated the permits mailbox
   for NSW certifier correspondence (read-only). The AI account has no
   delegate access yet (Graph returns FORBIDDEN), so the pilot runs from OSC
   alone. When access lands: verify with an `outlook_email_search` scoped
   to that mailbox, then extend the snapshot with an `emails` array and add
   `done_emails` evidence to `FAMILIES` — a separate PR.

## Success measure

Monday compilation time for the officer drops from hours to a review pass;
zero missed outstanding items versus the manual baseline over a 4-week
parallel run. Pilot acceptance (issue #29): at least 90 per cent of the
officer's outstanding items correctly pre-populated, officer review under
30 minutes, zero unapproved writes — scored per Monday by
`../scripts/compare_ba_report.py` on the three pilot jobs.
