# Workflow — Z-Drive Adviser (read-only search, save-location advice, duplicate/stale reporting)

The first Contract-Admin deliverable (see [`../CLAUDE.md`](../CLAUDE.md) scope #1
and [`../README.md`](../README.md)). Read-only: this workflow never moves,
renames, or deletes a business file. It answers questions and produces
reports; a human acts on them.

## Trigger

Ad hoc, in chat: a contract-admin user (or another workflow, e.g. `new-job.md`
step 11's duplicate check) asks Claude to find a file, confirm the latest
version, get save-location advice, or check a job/region for duplicate or
misfiled documents.

## Scope

`Z:\PROJECTS` only (region → job → document-type), per
[`../skills/README.md`](../skills/README.md)'s `ca-zdrive` plan — not the
wider `Z:` share. Runs as the requesting user, so NTFS permissions are
honoured: it can only see what that person could already see in Explorer.

## Observed structure (indexed 4 Aug 2026 — descriptive, not yet a confirmed rule)

- **Regions** under `Z:\PROJECTS\`: `CUDGEN`, `GUNNEDAH`, `SEQ`, `SYDNEY`,
  `TAMWORTH`, plus `CANCELLED CONTRACTS` and `COMPLETED CONTRACTS` sitting
  alongside the regions as lifecycle states (not nested inside them), and two
  miscellaneous folders (`MARK UP'S`, `z.SS`).
- **Every region contains `00000 - LOT MASTER FOLDER`** — the canonical
  document-type template that [`../scripts/new_job_folders.ps1`](../scripts/new_job_folders.ps1)
  copies for every new job (already noted in [`../rules/job-details.md`](../rules/job-details.md)
  JD-10.1). Observed branches:

  ```
  COLOUR SCHEMES
  CONSTRUCTION
  CONTRACT / CONTRACT DOCUMENTATION
  COUNCIL / APPLICATION FORMS, COVENANT, INSURANCES
  DRAFTING / ADDITIONAL INFORMATION & CONTOURS, CONTRACT-PRELIM PLANS,
            WORKING DRAWINGS / BASIX Report
  ESTIMATING / 1. SALES / 1. CONTRACT PRICING, 2. VARIATIONS / VAR-001,
                          3. QUOTES, 4. CUSTOMER SELECTIONS
              / 2. PRODUCTION / ORDERS, QUOTES
  MAINTENANCE
  ```

  This is the taxonomy save-location advice should map against — e.g. "a
  signed variation for job 26049" → `ESTIMATING\1. SALES\2. VARIATIONS\`. If a
  described document doesn't fit any branch, say so; do not invent one.
- **Job folder naming** (JD-10.2, confirmed again on this pass): `<5-digit job
  number> - LOT <lot> <STREET>, <SUBURB> <STATE>`, e.g. `26049 - LOT 5 (12)
  PEARSON STREET, GUNNEDAH NSW`.
- **`Z:\Z. SUPERSEDED`** (top-level, outside `PROJECTS`) is a general archive,
  not a per-job lifecycle stage — it holds mixed material (an old DA search, a
  named council application, a region folder, stray non-document files). Its
  intended relationship to a job's lifecycle, if any, is unconfirmed; don't
  assume superseded job documents belong there.

## What it does

| # | Action | Notes |
|---|---|---|
| 1 | **Search** — find files by job number, address/lot, region, or document type | Read-only listing, per `windows-fileops` recipes |
| 2 | **Latest-version candidate** — surface the most recently modified match(es) | Flag as an mtime heuristic, not proof of business authority — confirm with a human before anything price- or contract-sensitive relies on it |
| 3 | **Save-location advice** — map a described document to a branch of the master-folder taxonomy above | If no confident match, say so rather than guessing |
| 4 | **Duplicate report** — same content (hash) and/or same/near-identical name in more than one place | `Get-FileHash` recipe from `windows-fileops` |
| 5 | **Stale/misfiled report** — items sitting outside the master-folder taxonomy, or (once a threshold is confirmed) untouched for a long time in an active job | Threshold and "misfiled" criteria need business sign-off — see Open questions |

## Decision points

- **No confident document-type match** → report "no matching bucket," do not
  guess (same principle as the `ca-zdrive` constraint in
  [`../rules/README.md`](../rules/README.md)).
- **Duplicates disagree** (same name, different content, or vice versa) →
  report both candidates side by side; a human decides which is authoritative.
- **Region folder name vs OSC region code** — `Z:\PROJECTS` uses `GUNNEDAH` /
  `SEQ` / `SYDNEY` / `TAMWORTH` / `CUDGEN`; OSC uses `SEQ1` / `SYDNEY01`
  (JD-10.4). Report using the `Z:` names a person would recognise in Explorer.

## HITL gates

Every gate here is the same gate: **nothing is written.** This workflow only
answers questions and writes reports — never business files — to
`runtime\contract-admin\reports\`. Moving, renaming, or deleting a business
file is always a separate, explicitly approved instruction naming the exact
file(s); see the org [`CLAUDE.md`](../../../CLAUDE.md) Human-in-the-loop
section and the [`windows-fileops`](../../../.claude/skills/windows-fileops/SKILL.md)
skill's "Do not" section.

## Outputs

- Direct chat answers to ad hoc questions.
- Optional written report (Markdown/CSV) for a broader sweep (e.g. "duplicates
  across all of GUNNEDAH"), saved under `runtime\contract-admin\reports\`.

## Open questions (need business input — do not guess these)

- **Staleness threshold.** How long untouched, for which document types,
  before something is worth flagging in an *active* job?
- **Authority tie-breaks.** When two versions of the same document genuinely
  disagree (not just one older), what decides which is authoritative beyond
  "ask a human"?
- **`Z. SUPERSEDED`'s role**, if any, in the job lifecycle.
- **Job-number source** — OSC contract no. vs DataBuild — is still open per
  JD-10.2; this workflow inherits that same open question when naming a job
  folder in advice or reports.

## Relies on

- [`windows-fileops`](../../../.claude/skills/windows-fileops/SKILL.md) skill —
  all search, hashing, and reporting recipes.
- The observed master-folder taxonomy above, until the business confirms or
  corrects it.
- [`../rules/job-details.md`](../rules/job-details.md) JD-10 — the only
  already-confirmed `Z:` job-folder rules.
- The planned `ca-zdrive` skill (see [`../skills/README.md`](../skills/README.md))
  to invoke this workflow from a slash command — proposed, not yet built.
