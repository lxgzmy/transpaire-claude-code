# Workflow — New Job Creation (EOI intake → job setup)

Assists the OSC new-job procedure. Claude is **read-and-draft only**: it
extracts, validates and pre-fills; a human performs every OSC/DataBuild write.
All field rules live in [`../rules/job-details.md`](../rules/job-details.md)
(referenced as `JD-*`).

## Trigger

A new EOI / contract request email arrives in the Contract-Admin mailbox.

## Inputs

| Input | Source | Needed for |
|---|---|---|
| EOI / contract request email | Shared mailbox | Everything (JD-0.1) |
| Client ID document | Email attachment | Client name (JD-1.4) |
| DP & 88B document | Email / `Z:` | Registered-land address (JD-2.2) |
| Estate stage info | `Z:\ESTATES INFORMATION` or email | Stage number (JD-3.1) |
| PLANS (later) | Email, after setup | Phase 2 updates (JD-9) |

## Phase 1 — Job setup

| # | Step | Actor | Rules |
|---|---|---|---|
| 1 | Check EOI completeness; request client ID if missing | Claude drafts the request → human sends | JD-0.1 |
| 2 | Search OSC by lot number for an existing job | Human (Claude reminds; flags the duplicate risk) | JD-0.2 |
| 3 | **Draft the job-creation sheet**: region, template, client name, site address, job name | Claude | JD-1, JD-2 |
| 4 | **HITL GATE** — human reviews the sheet against the EOI, then creates the job in OSC | Human | — |
| 5 | Draft the job-details sheet: stage, design type/façade, payment schedule, certifier, council, legal, marketer | Claude (with lookup evidence: council search result, postcode check) | JD-3 |
| 6 | **HITL GATE** — human enters details, Save and Refresh | Human | JD-3.10 |
| 7 | Complete activities 1, 2, 6; attach request email (JOB + Item 11, Subject `NEW JOB`) | Human (Claude checklists) | JD-4, JD-5 |
| 8 | **Draft the DataBuild email** (full project name + contract price) | Claude drafts → **HITL GATE** → human sends | JD-6.1 |
| 9 | Enter contact details (client, sales, marketer) from Claude's pre-filled sheet | Human | JD-7 |
| 10 | On DataBuild confirmation: **compare price vs request email**; mismatch = stop and flag | Claude compares, human resolves | JD-6.2 |

Then the job **waits for the PLAN** (JD-8).

## Phase 2 — Plan received

| # | Step | Actor | Rules |
|---|---|---|---|
| 1 | Attach plan email to Item 12, Subject `PLAN FROM XXX` | Human (Claude drafts the subject) | JD-9.1 |
| 2 | **Draft the plan-diff sheet**: current OSC values vs PLAN values for street, design type/name, façade, house type/size, garage side | Claude | JD-9.2–9.5 |
| 3 | Garage side unclear → escalate, do not guess | Claude flags → human escalates | JD-9.5 |
| 4 | **HITL GATE** — human applies updates across Job Details, Inclusions, Build Contract (+ SITE), Preliminary Contract | Human | JD-9.6 |

## Decision points

- **Duplicate job exists** → stop; report and hand to a human (JD-0.2).
- **Unregistered vs registered land** → address logic branches (JD-2.1/2.2).
- **Council lookup ambiguous** → Estimate-folder check (JD-3.7).
- **Price mismatch** → hard stop until resolved (JD-6.2).
- **Garage side not left/right/rear** → escalation (JD-9.5).

## HITL gates (summary)

Every OSC/DataBuild write and every outbound email sits behind a human
approval. Claude's outputs are **draft sheets + evidence bundles** (source
email excerpts, lookup screenshots/results, diffs), saved to
`Z:\CLAUDE CODE\transpaire-claude-code\runtime\contract-admin\outputs\`.

## Outputs

- Job-creation draft sheet (Phase 1 step 3)
- Job-details draft sheet with lookup evidence (step 5)
- DataBuild email draft (step 8) — through the `transpaire-writing` skill
- Contact-details pre-fill sheet (step 9)
- Price-check report (step 10)
- Plan-diff sheet (Phase 2 step 2)

## Relies on

- [`../rules/job-details.md`](../rules/job-details.md) — all `JD-*` rules
- [`../scripts/extract_eoi.py`](../scripts/extract_eoi.py) — email → draft-sheet
  JSON (tested by `../scripts/test_extract_eoi.py` against the fixtures)
- [`../scripts/osc_entry.py`](../scripts/osc_entry.py) — OSC entry **skeleton**;
  dry-run only until the technical session maps the control IDs
- `transpaire-writing` skill — any drafted email
- `windows-fileops` skill — `Z:` lookups (estates info, Estimate folder)
