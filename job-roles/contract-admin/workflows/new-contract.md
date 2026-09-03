# Workflow — New Contract Template (contract request → filled templates)

Assists the manual's **RAISING CONTRACTS** procedure. Claude selects the correct
blank template, fills the fields it can source, and **saves the finished
documents in the same pass** — to the job folder for a genuine first draft, or
to the template-testing folder when the job already exists in production
(CD-7.7; the preview/approval stop was removed 17 Aug 2026). Issuing, sending,
signing and every flagged field stay with a person. All field rules live in
[`../rules/contract-docs.md`](../rules/contract-docs.md) (referenced as `CD-*`);
address, CAPS and garage-side rules stay in
[`../rules/job-details.md`](../rules/job-details.md) (`JD-*`).

This is the stage the retired new-job workflow marked as *"contract docs — NOT
in this manual"* in its chain diagram. It has a source procedure, so it is
built. The HIA licence held since 17 Aug 2026 makes the docx+PDF pair the
target for the HIA build contract (CD-5.2a), and since 18 Aug 2026 the driver
fills it in the same pass whenever a usable Word template exists (CD-5.2b:
approved blank in the region's CONTRACT folder → real name; staged template →
TEST runs only; otherwise data sheet only). Staged: NSW is the team's own
Word build (23 Aug 2026); QLD is the v2.1 LAND TABLES interim (3 Sep 2026)
— the team's v2 of 1 Sep (value-cell tables, e-sign anchors at source) plus
the same table fix for the land block v2 missed, filled in cell mode;
filled exports hold the licensed 37 pages. Every routed save runs
`hia_probe.py` and reports BLOCKED or CANDIDATE; the remaining human steps
in both regions (read-through of a filled test output against the licensed
PDF → MCR files the blank; for QLD one flagged item rides along — the moved
`/i1/\signer1_sig` — see the staging README) are defined in the skill and
the template map.

## Trigger

A **Build Contract Request** email reaches the Contract-Admin mailbox, usually
forwarded marketer → sales manager → contract admin.

## Inputs

| Input | Source | Needed for |
|---|---|---|
| Contract request email (full chain) | Shared mailbox | Instruction, design, façade, price (CD-0.1) |
| Signed EOI | Attachment — often a photo, no text layer | Client names, dual-key flag (CD-0.2) |
| Client ID documents | Attachment | Name spelling (CD-0.3) |
| Inclusions document | Attachment or `Z:` | Which template the sender intends (CD-0.4) |
| Blank template | `Z:\PROCEDURES & FORMS\CONTRACTS\` | The document itself (CD-1) |
| PLANS | Job folder / drafting | House size, garage side (CD-2.7, CD-2.9) |
| DataBuild | — | GST split, progress payments (CD-5.4, CD-5.6) |
| Estate information | `Z:\ESTATES INFORMATION\<state>\<region>\<estate>\` | Lot-specific facts |

## Phase 1 — Draft the documents

| # | Step | Actor | Rules |
|---|---|---|---|
| 1 | Read the whole chain + attachments; read the EOI as an image; note missing client ID | Claude | CD-0 |
| 2 | Locate the job folder (all lifecycle levels); check for existing contract docs — any hit means **TEST MODE** (the job already exists in production; output goes only to the template-testing folder) — and any cancelled twin; **confirm the required contract from the folder's own documents** (fingerprint vs the blank) — unclear or multiple candidates → stop and present options | Claude (via `z-drive-ops`) | CD-7.6, CD-7.7, CD-1.6 |
| 3 | **Select the template**, state its full path + reason, and confirm it agrees with the job's existing documents | Claude | CD-1 |
| 4 | Assemble field values with a source per field; flag what the plans have to supply | Claude | CD-2, CD-3 |
| 5 | **`draft_contract.py --job-dir`** — one timed command ending in the save: anchor checks (a miss aborts that document), fills, blank-vs-filled diffs, complete PDF exports through a single Word launch, then automatic routing — TEST → finals + `temp\` to `template-testing\<job>\`; PRODUCTION → the docx+PDF pair into the job's `CONTRACT DOCUMENTATION`, never overwriting. `--prelim` only after the CD-4.4 decision (standard $30,000 fee unless the request names another, CD-4.3); in TEST mode `--real-dir` defaults to the job folder for REAL_ exports + word-level diffs, every differing block classified. A failed stage blocks the save | Claude | CD-1.3, CD-2–4, CD-7.7 |
| 6 | Draft the build contract **data sheet** (the person-keyed values: price split and Part B as `FROM DATABUILD` placeholders — never computed — guarantors, special conditions, resident-owner), carrying the run's `hia contract:` status; it complements the driver's filled build contract and is the whole deliverable only when PRODUCTION is BLOCKED | Claude | CD-5 |
| 7 | Report destination + mode, field table, flags; send the final PDFs inline. Evidence bundle stays in `runtime\contract-admin\outputs\<job>\` (job JSON, check/fill reports, diffs, timings) | Claude | — |

## Phase 2 — Issue and execute (human)

Not automated, and not attempted. Listed so the handover is complete (CD-8):
key in and assemble the contract pack; attach in OnSite Companion
under `CONTRACT`; email the contract to the marketer, cc Tony Feng, with the
internal colour options; check initials and signatures; Michael Cronk signs;
scan the six executed documents separately; manila folder to the filing cabinet.

## Decision points

- **Price in email ≠ price on EOI** → hard stop (CD-2.5).
- **Plans not received** → produce everything else, name the unfilled fields.
- **Auxiliary / dual key** → fill fields, route for review before issue (CD-6).
- **Anchor missing on `--check`** → template revised; stop.
- **Contract docs already in the folder** → TEST MODE: the run saves only to the
  template-testing folder; a genuine amendment is promoted by a person
  (CD-7.6/7.7).
- **Prelim agreement requirement unclear** → ask (CD-4.4).

## HITL gates

The preview/approval gates that used to sit at the old steps 6 and 8 were
**removed on 17 Aug 2026 by explicit instruction** (they had been declared
permanent on 12/16 Aug — the removal supersedes that). Saving is now automatic
and bounded by CD-7.7's routing: test runs can never touch a job folder, and
production saves never overwrite. What stays with a person, permanently: every
outward-facing act — email, signature, DocuSign, OSC write — plus resolving
flagged fields, aux inclusions wording, and promoting test/amendment output
into a job folder.

## Outputs

Saved automatically to the routed destination (CD-7.7): the job's
`CONTRACT DOCUMENTATION` for a first draft, or
`Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\` when
the job already exists in production.

- Completed inclusions `.docx` + `.pdf` export (CD-2, CD-3, CD-7.4)
- Completed preliminary agreement `.docx` + `.pdf` export, where required (CD-4)
- Build contract data sheet (CD-5)
- Pack checklist: general conditions, concept plan, consumer guide, colour options
- Fill report + blank-vs-filled diff as the evidence bundle

## Where this sits in the full chain

```
EOI email ─> OSC job ─> Z: job folders ─> [wait: PLAN] ─> plan updates ─> contract docs ─> DocuSign issue
             [human, manual]               [JD-8]         [JD-9]          [THIS WORKFLOW]   [human, always]
```

## Relies on

- [`../rules/contract-docs.md`](../rules/contract-docs.md) — `CD-*`
- [`../rules/job-details.md`](../rules/job-details.md) — `JD-2`, `JD-9`
- [`../scripts/draft_contract.py`](../scripts/draft_contract.py) — the one-command pipeline (check → fill → diff → PDF export → real-comparison → routed save), timed
- [`../scripts/fill_inclusions.py`](../scripts/fill_inclusions.py) — inclusions filler (`regress_inclusions.py` guards it)
- [`../scripts/fill_prelim.py`](../scripts/fill_prelim.py) — preliminary agreement filler (`regress_prelim.py` guards it)
- [`../scripts/msg_extract.py`](../scripts/msg_extract.py) — `.msg` → text + attachments, stdlib only (`msg_to_text.py` is the superseded fallback)
- `new-contract-template` skill — orchestrates this workflow
- `z-drive-ops` skill — locating the job folder and the template
- `transpire-writing` skill — any drafted email
