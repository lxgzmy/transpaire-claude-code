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
4. **Draft the new report**: remove items evidenced complete, keep the
   rest, add newly detected items, and populate the new ageing columns —
   *with whom*, *date handed over*, *days outstanding*, age flag (default
   amber ≤5 days / red >5 days, pending confirmation — PO-11 ❓).
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

## How to run (v0.1)

1. **Snapshot step (Claude + `osc-api` MCP, read-only).** For each job row in
   last week's report: resolve the contract number to its `jobID`, read
   activities, alerts and documents (queries in
   `../reference/osc-field-map.md`), and save one JSON per job to
   `runtime\permit-officer\state\snapshots\<jobno>.json` (shape documented in
   `../scripts/ba_report_draft.py`).
2. **Draft step (deterministic, no network):**

   ```
   python ../scripts/ba_report_draft.py
          --prev "runtime\permit-officer\reports\BA REPORT - <last>.xlsx"
          --snapshots runtime\permit-officer\state\snapshots
          --out runtime\permit-officer\outputs
          --state runtime\permit-officer\state
   ```

   Produces the draft workbook (columns A–K unchanged plus a proposed
   ageing column) and the evidence bundle (`…-evidence.md` / `.json`).
   Carried values are never overwritten; items are dropped only on fresh
   completion evidence; everything else is kept and flagged. First-seen
   dates persist in `state\ba-items-first-seen.json` so ageing accumulates
   across weeks.
3. **Review (the officer):** correct the draft, distribute as today; file
   the corrected copy into `runtime\permit-officer\reports\` as next week's
   base. Corrections worth keeping become evidence-rule fixes in
   `../scripts/ba_report_draft.py` (`FAMILIES`).

Regression: `python ../scripts/regress_ba_report.py` (synthetic data only).

## Build gates

1. **OSC access — CLEARED.** The read-only `osc-api` MCP server is live
   (project-scoped, writes disabled; see `.claude/skills/osc-api/`). Still
   required before code: a **field-mapping pass** against real jobs —
   how to enumerate BA-stage jobs (the Executive Reporter filter's
   equivalent), activity completion semantics, alert recipients and
   timestamps, document naming — recorded de-identified in
   `../reference/osc-field-map.md`.
2. **Report template agreement** — confirm the added columns and age
   thresholds with the permit officer and management, and capture a
   sanitised copy of the current report layout as a fixture (synthetic
   data only) under `../fixtures/`. The export procedure document is
   already in the AI testing folder; a recent export + final + marked-up
   copy are still to be dropped.

## Success measure

Monday compilation time for the officer drops from hours to a review pass;
zero missed outstanding items versus the manual baseline over a 4-week
parallel run.
