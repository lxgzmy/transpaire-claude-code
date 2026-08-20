# Permit Officer (Approvals) Job-Role & Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the second job-role in this repo — **Permit Officer (building approvals)** — with transcribed rules and workflow specs from the 20 Aug 2026 AI-consultation discovery meeting, so the three agreed automations (weekly BA report pre-population, pre-lodgement checklist, form pre-fill) can be built once their gates clear.

**Architecture:** Mirror the proven `job-roles/contract-admin/` layout: role `CLAUDE.md` + `README.md`, de-identified `rules/` transcribed from the discovery meeting, one spec per workflow in `workflows/`, `reference/` pointers to source material kept on `Z:` (never in the repo). No skill is built in this plan — the org guardrail requires proposing skills before creating them, and the two build-time gates (OSC API access, RFI training corpus) are not yet met. This plan is entirely documentation; every task is executable today.

**Tech Stack:** Markdown only in this plan. Downstream (gated, out of scope here): PowerShell 7 + Python on Windows Server 2022, OSC REST API (delivered to the AI team 21 Aug 2026), openpyxl for the BA-report Excel.

**Spec:** The discovery source is the meeting recording `AI consultation - Approval-20260820_040605UTC-Meeting Recording.mp4` (attendees: Tony Feng, Gaynor — permit officer, Lisa, Jason Li, Jason Liu / AI team; Fireflies recording). The recording contains client PII and stays out of the repo; the de-identified workflow extraction is embedded in the rules content of Task 2 below, which serves as the spec.

## Global Constraints

- No client PII, job numbers, site addresses, server names, or credentials in any repo file (org `CLAUDE.md`). All rule/workflow content below is de-identified; verification greps enforce it.
- Runtime/client data only ever under `Z:\CLAUDE CODE\transpire-claude-code\runtime\<job-role>\` (git-ignored); this plan creates `runtime/permit-officer/` usage by convention only — no runtime files are created here.
- HITL: read-only and draft-first. The permit-officer role starts with **zero** sanctioned auto-saves (unlike contract-admin's CD-7.7 exception). Every artefact is a draft for human review.
- Explicit non-goals fixed in the meeting: no AI judgement on RFI responses (stays with the permit officer); no automation of government or certifier portals (no credential handover); DataBuild is retiring and out of scope.
- Australian English in all docs; register per `shared/conventions/writing-style.md`.
- Propose skills before creating them: this plan documents *proposed* skills only.

---

### Task 1: Role scaffolding — `job-roles/permit-officer/` README + CLAUDE.md, index updates

**Files:**
- Create: `job-roles/permit-officer/README.md`
- Create: `job-roles/permit-officer/CLAUDE.md`
- Modify: `job-roles/README.md` (add the new role to the index)
- Modify: `README.md` (repo root — add the role to the job-roles list)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: the folder paths every later task writes into; the role name **permit-officer** used verbatim by Tasks 2–5.

- [ ] **Step 1: Create `job-roles/permit-officer/README.md`** with exactly this content:

```markdown
# Permit Officer — Building Approvals (job-role)

Builder-side permits and approvals for Transpire (QLD + NSW residential jobs).
Start with [CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the
repo-root `CLAUDE.md` also apply).

Discovery completed 20 Aug 2026 (AI-consultation session with the permit
officer). Proof-of-concept, read-only and draft-first. Three workflows, in
build order:

1. **Weekly BA report pre-population** (spec written; build gated on OSC API
   access) — draft the Monday building-approval status report by reading OSC
   job activities, alerts and documents, carrying forward last week's report,
   and flagging item age. Spec: `workflows/ba-weekly-report.md`.
2. **Pre-lodgement checklist** (spec written; build gated on the RFI corpus)
   — before a job is lodged, predict the certifier's likely RFI items and the
   orders the permit officer must place (energy assessment, 10.7, utility
   authority), from job attributes plus past RFIs. Spec:
   `workflows/pre-lodgement-checklist.md`.
3. **Council / certifier form pre-fill** (not started) — pre-fill recurring
   application forms from OSC job data. Flagged in the meeting as the easy
   win; needs the blank forms collected into the AI testing folder first.

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow (above). |
| `rules/` | De-identified, testable business rules transcribed from discovery (`PO-*`). |
| `reference/` | Pointers to source material (recording, RFI corpus) kept on `Z:` — never in the repo. |
| `skills/` | Role-only skills. None built yet; proposals listed in `skills/README.md`. |

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\permit-officer\{state,evidence,outputs,logs,reports}\`
(git-ignored) — see the org [CLAUDE.md](../../CLAUDE.md).
```

- [ ] **Step 2: Create `job-roles/permit-officer/CLAUDE.md`** with exactly this content:

```markdown
# CLAUDE.md — Permit Officer / Building Approvals (job-role)

Scoped context for the Permit Officer job-role. The org-wide guardrails in the
repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Secures council approvals, covenant (developer) approvals, and the building
approval issued by the private certifier, for QLD and NSW jobs. Prepares and
lodges approval packages, works certifier RFIs to completion, orders
role-owned items (energy assessment, insurances, planning certificates,
utility-authority approvals), and coordinates every other RFI item to the
staff member who owns it. Claude assists by reading, tracking, drafting and
reporting — never by deciding an RFI response or touching a portal.

## Scope

1. **Weekly BA report pre-population** (spec written, build gated on OSC API
   access — the API was scheduled for delivery to the AI team on 21 Aug 2026).
   Draft the Monday report from OSC + last week's report; flag item age.
   Spec: `workflows/ba-weekly-report.md`; rules `PO-9`–`PO-11`.
2. **Pre-lodgement checklist** (spec written, build gated on collecting the
   RFI corpus into the AI testing folder on `Z:`). Once per job, before
   lodgement. Spec: `workflows/pre-lodgement-checklist.md`; rule `PO-12`.
3. **Form pre-fill** (not started; needs blank council/certifier forms
   collected). No spec yet — write one before building.

## Systems

OnSite Companion (OSC) is the primary record: job activities/milestones,
alerts (the internal communication channel), and the per-job Document
Manager. Microsoft 365 / Outlook carries all external correspondence.
QLD jobs: the certifier's online portal holds lodgement + all certifier
communication (notifications land in the mailbox). NSW jobs: no certifier
portal — everything is email — plus the NSW Planning Portal for CDC/CC
lodgement and council/utility-authority portals for role-owned orders.
DataBuild (purchase orders) is retiring and **out of scope**.

## Rules & knowledge

- `rules/approval-workflow.md` — the transcribed discovery rules (`PO-*`):
  lodgement preconditions and package, QLD/NSW differences, RFI intake and
  triage, communication conventions, report content, non-goals.

> `rules/approval-workflow.md` is **transcribed from the 20 Aug 2026
> discovery meeting** (pending business review by the permit officer). Do
> not author skills against guessed rules; where a rule carries an open
> question, settle it with the business first.

## Hard limits fixed at discovery

- **No portal automation.** Certifier, council, NSW Planning Portal and
  utility portals are operated by humans only; no credentials to AI.
- **No RFI judgement.** Analysing an RFI and deciding the response is the
  permit officer's job. Claude tracks, drafts and reports around it.
- **DataBuild out of scope** (retiring; estimating replacement pending).

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\permit-officer\{state,evidence,outputs,logs,reports}\`
— git-ignored.

## Human-in-the-loop

Every artefact (report draft, checklist, alert text, form fill) is a draft
with an evidence bundle for the permit officer to review. Nothing is sent,
lodged, uploaded, or written to OSC without explicit human approval. This
role has **no** sanctioned auto-save exception.
```

- [ ] **Step 3: Update `job-roles/README.md`** — read the file first; add a Permit Officer row/entry alongside the existing Contract Administration entry, linking to `permit-officer/README.md`, described as: "Building approvals (QLD certifier portal + NSW email/planning portal), RFI tracking, weekly BA report. Discovery 20 Aug 2026; docs-first, no skills built yet." Match the file's existing format exactly (table row if it is a table, list item if a list).

- [ ] **Step 4: Update repo-root `README.md`** — read it first; where it indexes job-roles (it currently names Contract Administration as the first role), add Permit Officer as the second role with a one-line description and link. Match existing format.

- [ ] **Step 5: Verify no PII leaked**

Run: `grep -rniE '(blundell|acosta|denham|casuarina|logan reserve|yarrabilba|2[56][0-9]{3}|192\.168|58\.96)' job-roles/permit-officer/ README.md job-roles/README.md`
Expected: no output (exit code 1).

- [ ] **Step 6: Commit**

```bash
git add job-roles/permit-officer/README.md job-roles/permit-officer/CLAUDE.md job-roles/README.md README.md
git commit -m "permit-officer: scaffold second job-role from 20 Aug discovery"
```

---

### Task 2: Transcribed rules — `rules/approval-workflow.md` (PO-1 … PO-14)

**Files:**
- Create: `job-roles/permit-officer/rules/README.md`
- Create: `job-roles/permit-officer/rules/approval-workflow.md`

**Interfaces:**
- Consumes: folder from Task 1.
- Produces: rule IDs `PO-1`…`PO-14` referenced verbatim by Tasks 3 and 4.

- [ ] **Step 1: Create `job-roles/permit-officer/rules/README.md`**:

```markdown
# Rules — Permit Officer

| File | Prefix | Status |
|---|---|---|
| [approval-workflow.md](approval-workflow.md) | `PO-*` | Transcribed from the 20 Aug 2026 discovery meeting; pending business review. |

Rules are de-identified: no client names, job numbers, addresses, or
certifier/company names. The source recording stays outside the repo
(see `../reference/README.md`).
```

- [ ] **Step 2: Create `job-roles/permit-officer/rules/approval-workflow.md`** with exactly this content:

```markdown
# Approval workflow rules (`PO-*`)

Transcribed from the 20 Aug 2026 AI-consultation discovery meeting with the
permit officer. **Pending business review.** Each rule is written to be
testable; open questions are marked ❓.

## Role and preconditions

- **PO-1 — Role scope.** The permit officer secures (a) council approvals,
  (b) covenant approvals from the developer, and (c) the building approval
  issued by the private certifier, and performs lodgements for both QLD and
  NSW jobs.
- **PO-2 — Lodgement preconditions.** A job is lodged only when the land has
  settled **and** the owner has signed the working drawings. The trigger is
  an OSC alert from the customer liaison that the job is ready to lodge; the
  OSC workflow tracks the preconditions.
- **PO-3 — Lodgement package.** The initial package is compiled from the
  job's OSC Document Manager and at minimum comprises the soil report,
  contour plans, registered plans, and (when present) the contract. Document
  hunting is *not* a pain point at lodgement — it starts at RFI stage.

## State differences

- **PO-4 — QLD.** The certifier operates an online portal: the job is
  created and documents uploaded there, and **all** certifier communication
  happens in the portal (each side gets email notifications). The certifier
  also places council/covenant/QLD-specific orders on the builder's behalf.
  QLD status can therefore be read at a glance from the portal.
- **PO-5 — NSW.** No certifier portal — all certifier correspondence is by
  email, which makes NSW status the hard tracking case. The permit officer
  additionally orders what the QLD certifier would order: the s10.7 planning
  certificate (before lodgement — the certifier will not assess without it;
  a colleague notifies the permit officer ahead of lodgement so it can be
  ordered early; some councils take a day, others need chasing), plus
  utility-authority (water) approvals where the job's region requires them,
  and lodges the CC/CDC through the NSW Planning Portal.

## RFI lifecycle

- **PO-6 — RFI is universal.** Every job receives at least one RFI
  (request for information) from the certifier after lodgement; first
  assessment turnaround is typically 2–3 weeks (extremes to 4). One RFI per
  job is the norm; a further RFI appears only to correct a certifier error
  or to reset the statutory assessment clock on long-running jobs, and
  substantially repeats the outstanding items.
- **PO-7 — RFI intake.** On receipt: update the OSC milestones (RFI
  received) and upload the RFI document to the job, then work the item list.
- **PO-8 — RFI triage.** Each RFI item is either **own-action** (the permit
  officer orders/supplies it: insurances such as home-warranty and
  long-service levies, purchase orders, the energy-efficiency assessment,
  certificates) or **coordination** (another team decides: e.g. a
  non-compliant setback goes by OSC alert to the GM and the drafting manager
  with the options — amend plans or lodge a council referral — and their
  decision comes back before the certifier is notified). Judgement about
  what each item needs **stays human** (see PO-13).
- **PO-8a — Energy efficiency.** Ordered for every job (QLD and NSW) at or
  shortly after lodgement. The assessment almost always returns required
  upgrades; upgrades trigger an OSC alert with the options, a GM
  cost-efficiency decision, then drafting + contracts raise a variation.
  The Document Manager description encodes state: an *energy application*
  document means not yet assessed (or upgrades pending); an *energy report*
  means completed/approved.

## Communication conventions

- **PO-9 — Internal = OSC alerts.** All internal RFI communication is an OSC
  alert on the job activity (never plain email): alerts are visible to
  everyone on the job, carry history, and let others pick up a stalled item.
  Follow-up on an unanswered alert is face-to-face or email. External
  parties (engineers, energy assessor, certifier in NSW) are emailed;
  engineering emails sent *from* OSC save to the job automatically, and all
  other external email must be dragged into OSC manually as `.msg`.

## Weekly BA report

- **PO-10 — Cadence and base.** The report is produced every Monday as the
  whole-of-business status view of jobs in the approval stage. Last week's
  report is the base; items completed during the week are removed and new
  ones added.
- **PO-11 — Content and sources.** One row per job: job number, client,
  site, key dates, and the **outstanding RFI items** (currently typed
  manually in red). Sources, in order: OSC (job activities, alerts,
  Document Manager descriptions per PO-8a) → QLD certifier portal → the
  mailbox (NSW especially). Items live outside OSC workflow activities
  today, which is why compilation is manual. Wanted additions from the
  meeting: per item, **who it is with, the date it was handed to them, and
  days outstanding**, with an age flag — ❓ default from the meeting:
  amber within 5 days, red past 5 days; confirm thresholds with the
  business.

## Pre-lodgement checklist

- **PO-12 — Predicted checklist.** Once per job, before lodgement (timing ❓
  — the more Transpire documentation is ready, the better), produce a
  job-specific checklist of (a) items the certifier's RFI is likely to
  raise, learned from past RFIs — NSW RFIs are near-standard forms, ideal
  training material — and (b) role-owned orders the job's attributes
  trigger (energy assessment always; s10.7 for NSW; utility-authority
  approval when the job falls in an applicable water region). Purpose: a
  head start and a forget-proof reminder across many simultaneous jobs.

## Non-goals (fixed at discovery)

- **PO-13 — No RFI judgement by AI.** Analysing the RFI and deciding
  responses is the permit officer's role.
- **PO-14 — No portal automation, no DataBuild.** No AI access or
  credentials to certifier/council/NSW-Planning/utility portals. DataBuild
  is retiring and out of scope.
```

- [ ] **Step 3: Verify no PII leaked**

Run: `grep -rniE '(blundell|acosta|gaynor|rusford|denham|casuarina|logan|yarrabilba|gables|westdale|pallara|2[3-6][0-9]{3}|192\.168|58\.96)' job-roles/permit-officer/rules/`
Expected: no output. (Staff first names are deliberately excluded from the rules files; the meeting attendees are named only in this plan.)

- [ ] **Step 4: Commit**

```bash
git add job-roles/permit-officer/rules/
git commit -m "permit-officer: transcribe PO-* approval workflow rules from discovery"
```

---

### Task 3: Workflow spec — `workflows/ba-weekly-report.md`

**Files:**
- Create: `job-roles/permit-officer/workflows/README.md`
- Create: `job-roles/permit-officer/workflows/ba-weekly-report.md`

**Interfaces:**
- Consumes: rule IDs `PO-9`–`PO-11`, `PO-13` from Task 2.
- Produces: the workflow name `ba-weekly-report` and its gate list, referenced by Task 5's skill proposal.

- [ ] **Step 1: Create `job-roles/permit-officer/workflows/README.md`**:

```markdown
# Workflows — Permit Officer

| Spec | Status | Build gate |
|---|---|---|
| [ba-weekly-report.md](ba-weekly-report.md) | Spec written | OSC API access + field mapping session |
| [pre-lodgement-checklist.md](pre-lodgement-checklist.md) | Spec written | RFI corpus collected into the AI testing folder |

Form pre-fill (third automation from discovery) has no spec yet — write one
before building.
```

- [ ] **Step 2: Create `job-roles/permit-officer/workflows/ba-weekly-report.md`** with exactly this content:

```markdown
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

## Target flow

1. **Carry forward.** Read last week's report from the runtime reports
   folder (`runtime\permit-officer\reports\`); parse rows (job number,
   client, site, dates, outstanding items).
2. **Read OSC per job** (via the OSC API once available): job activities
   and their completion state, alerts raised/acknowledged during the week,
   Document Manager entries — including the energy application → energy
   report rename that encodes energy status (PO-8a).
3. **Read the shared mailbox** for NSW jobs (read-only): match
   correspondence to jobs, note items sent to the certifier during the
   week.
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

## Build gates (both must clear before any code)

1. **OSC API access** — promised to the AI team from the OSC upgrade of
   21 Aug 2026. Needs: auth model, and read endpoints for jobs, activities,
   alerts, documents. A field-mapping session against a real job follows.
2. **Report template agreement** — confirm the added columns and age
   thresholds with the permit officer and management, and capture a
   sanitised copy of the current report layout as a fixture (synthetic
   data only) under `fixtures/`.

## Success measure

Monday compilation time for the officer drops from hours to a review pass;
zero missed outstanding items versus the manual baseline over a 4-week
parallel run.
```

- [ ] **Step 3: Verify links and rule references**

Run: `grep -oE 'PO-[0-9]+[a-z]?' job-roles/permit-officer/workflows/ba-weekly-report.md | sort -u`
Expected: every listed ID exists in `rules/approval-workflow.md` (cross-check with `grep -oE '\*\*PO-[0-9]+[a-z]?' job-roles/permit-officer/rules/approval-workflow.md`).

- [ ] **Step 4: Commit**

```bash
git add job-roles/permit-officer/workflows/README.md job-roles/permit-officer/workflows/ba-weekly-report.md
git commit -m "permit-officer: spec the weekly BA report pre-population workflow"
```

---

### Task 4: Workflow spec — `workflows/pre-lodgement-checklist.md`

**Files:**
- Create: `job-roles/permit-officer/workflows/pre-lodgement-checklist.md`

**Interfaces:**
- Consumes: rule `PO-12` (Task 2); listed in `workflows/README.md` (Task 3).
- Produces: the workflow name `pre-lodgement-checklist` referenced by Task 5.

- [ ] **Step 1: Create the file** with exactly this content:

```markdown
# Workflow: pre-lodgement checklist (predicted RFI)

Give the permit officer a job-specific head start before lodgement: what
the certifier will likely ask for, and which role-owned orders this job
needs. Rule `PO-12`; draft-only per the role `CLAUDE.md`.

## Why

RFI items repeat heavily across jobs (NSW certifiers effectively issue a
standard form with only the applicable lines kept). Certifier first
response takes 2–3 weeks; items known in advance can be ordered during
that dead time instead of after. With many simultaneous jobs, orders
(water authority, s10.7) get forgotten — the checklist is the reminder.

## Target flow

1. **Trigger**: the pre-lodgement notification the customer liaison already
   sends (the same heads-up used today for early s10.7 ordering), or the
   officer invoking the workflow on a named job. Runs **once per job**.
2. **Read the job**: state (QLD/NSW), region, estate/covenant flags, and
   the Document Manager inventory (what is already in the package vs the
   PO-3 minimum).
3. **Apply deterministic triggers** first: energy assessment (always,
   PO-8a); NSW → s10.7 + planning-portal lodgement items (PO-5); water
   authority when the region applies (PO-12); insurances/levies.
4. **Predict from the corpus**: match the job against past RFIs to list
   likely certifier items beyond the deterministic set, each with the
   source RFI pattern it came from.
5. **Output**: a checklist draft (own-action vs coordination per PO-8),
   saved to `runtime\permit-officer\outputs\`, for the officer to adopt.

## Build gates

1. **RFI corpus** — past RFIs (QLD and NSW) collected into the AI testing
   folder agreed at discovery (per-role folder on the server the AI team
   can read). NSW standard-form RFIs are the priority training material.
2. **Trigger wiring** — confirm how the pre-lodgement notification reaches
   the workflow (mailbox rule vs manual invocation) with the officer.

## Out of scope

Ordering anything, contacting anyone, or lodging — the checklist is advice.
```

- [ ] **Step 2: Verify PII grep** (same command as Task 2 Step 3, scoped to `workflows/`)

Run: `grep -rniE '(blundell|acosta|gaynor|rusford|denham|casuarina|logan|yarrabilba|2[3-6][0-9]{3})' job-roles/permit-officer/workflows/`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add job-roles/permit-officer/workflows/pre-lodgement-checklist.md
git commit -m "permit-officer: spec the pre-lodgement checklist workflow"
```

---

### Task 5: Reference pointers and skill proposals

**Files:**
- Create: `job-roles/permit-officer/reference/README.md`
- Create: `job-roles/permit-officer/skills/README.md`

**Interfaces:**
- Consumes: workflow names from Tasks 3–4.
- Produces: the proposed-skill names `ba-weekly-report` and `pre-lodgement-checklist` (final names to be confirmed at proposal time, per the org propose-before-create rule).

- [ ] **Step 1: Create `job-roles/permit-officer/reference/README.md`**:

```markdown
# Reference — Permit Officer

Source material lives outside the repo (it contains client PII); this file
only points at it.

| Source | Where | Notes |
|---|---|---|
| Discovery recording, 20 Aug 2026 | Downloads / to be filed on `Z:` in the AI testing folder | `AI consultation - Approval-20260820_040605UTC-Meeting Recording.mp4`; the substantive session ends when the guests leave the call. |
| AI testing folder (per-role) | `Z:` — location to be created per the discovery agreement | Destination for past RFIs (NSW standard forms prioritised), blank council/certifier application forms, and a sanitised copy of the current weekly report layout. |
| Current weekly BA report | Maintained by the permit officer (Excel, updated Mondays) | Never copy into the repo; a **synthetic** layout fixture may go under `../fixtures/` once the template is agreed. |
```

- [ ] **Step 2: Create `job-roles/permit-officer/skills/README.md`**:

```markdown
# Skills — Permit Officer

None built. Per the org rule, skills are **proposed before creation**; the
proposals below are queued behind their workflow build gates.

| Proposed skill | Backing spec | Gate status |
|---|---|---|
| `ba-weekly-report` | `../workflows/ba-weekly-report.md` | Waiting on OSC API access + report template agreement. |
| `pre-lodgement-checklist` | `../workflows/pre-lodgement-checklist.md` | Waiting on the RFI corpus in the AI testing folder. |
| Form pre-fill (unnamed) | No spec yet | Waiting on blank forms collected; write the spec first. |
```

- [ ] **Step 3: Verify the tree is complete**

Run: `find job-roles/permit-officer -name '*.md' | sort`
Expected exactly:
```
job-roles/permit-officer/CLAUDE.md
job-roles/permit-officer/README.md
job-roles/permit-officer/reference/README.md
job-roles/permit-officer/rules/README.md
job-roles/permit-officer/rules/approval-workflow.md
job-roles/permit-officer/skills/README.md
job-roles/permit-officer/workflows/README.md
job-roles/permit-officer/workflows/ba-weekly-report.md
job-roles/permit-officer/workflows/pre-lodgement-checklist.md
```

- [ ] **Step 4: Commit**

```bash
git add job-roles/permit-officer/reference/ job-roles/permit-officer/skills/
git commit -m "permit-officer: reference pointers and gated skill proposals"
```

---

## Deferred (do NOT build in this plan — recorded so the gates are visible)

1. **OSC API integration layer** — blocked until the API lands (21 Aug 2026)
   and a field-mapping session confirms endpoints for jobs, activities,
   alerts, documents. First code will be a read-only probe under
   `job-roles/permit-officer/scripts/`, TDD'd against recorded fixtures,
   planned separately once the API surface is known.
2. **OSC workflow expansion** (adding the missing approval activities to OSC
   so status is machine-readable) — a business change Tony took away to
   raise with management, staged permits-section-first. Not a repo change.
3. **Form pre-fill** — spec after blank forms are collected.

## Self-review notes

- Spec coverage: PO-1…PO-14 cover role scope, preconditions, package, QLD/NSW
  split, RFI lifecycle/triage/energy, comms, report, checklist, non-goals —
  each discovery topic maps to a rule; both agreed near-term automations have
  a spec task; the third (form pre-fill) is deliberately spec-less and gated.
- No placeholders: the two genuine unknowns (age thresholds, checklist
  timing) are marked ❓ with the meeting's stated default — they are business
  confirmations, not engineering TBDs.
- Naming: `permit-officer`, `PO-*`, `ba-weekly-report`,
  `pre-lodgement-checklist` used consistently across all tasks.
