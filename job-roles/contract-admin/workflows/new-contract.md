# Workflow — New Contract Template (contract request → filled templates)

Assists the manual's **RAISING CONTRACTS** procedure. Claude is **read-and-draft
only**: it selects the correct blank template, fills the fields it can source,
and hands a draft to a person. All field rules live in
[`../rules/contract-docs.md`](../rules/contract-docs.md) (referenced as `CD-*`);
address, CAPS and garage-side rules stay in
[`../rules/job-details.md`](../rules/job-details.md) (`JD-*`).

This is the stage that [`new-job.md`](new-job.md) marks as *"contract docs — NOT
in this manual"* in its chain diagram. It now has a source procedure, so it is
built — but only to the boundary in CD-5: the build contract PDF is not fillable,
so that part is a data sheet, not a document.

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
| 2 | Locate the job folder (all lifecycle levels); report existing contract docs and any cancelled twin | Claude (via `z-drive-ops`) | CD-7.6 |
| 3 | **Select the template** and state its full path + reason | Claude | CD-1 |
| 4 | Assemble field values with a source per field; flag what the plans have to supply | Claude | CD-2, CD-3 |
| 5 | `fill_inclusions.py --check` — confirm every anchor still exists | Claude | CD-1.3 |
| 6 | Fill the inclusions; diff filled vs blank and show it | Claude | CD-2, CD-3 |
| 7 | Fill the preliminary agreement, if the job needs one | Claude | CD-4 |
| 8 | **HITL GATE** — field table + flags reviewed; approve or correct | Human | — |
| 9 | Draft the build contract **data sheet** (cover, price from DataBuild, building period, Part B) | Claude | CD-5 |
| 10 | **HITL GATE** — save to the job folder under the naming convention; never overwrite | Human approves, Claude copies | CD-7 |
| 11 | Evidence bundle to `runtime\contract-admin\outputs\<job>\` | Claude | — |

## Phase 2 — Issue and execute (human)

Not automated, and not attempted. Listed so the handover is complete (CD-8):
key in and assemble the contract pack; export PDFs; attach in OnSite Companion
under `CONTRACT`; email the contract to the marketer, cc Tony Feng, with the
internal colour options; check initials and signatures; Michael Cronk signs;
scan the six executed documents separately; manila folder to the filing cabinet.

## Decision points

- **Price in email ≠ price on EOI** → hard stop (CD-2.5).
- **Plans not received** → produce everything else, name the unfilled fields.
- **Auxiliary / dual key** → fill fields, route for review before issue (CD-6).
- **Anchor missing on `--check`** → template revised; stop.
- **Contract docs already in the folder** → amendment, not a first draft (CD-7.6).
- **Prelim agreement requirement unclear** → ask (CD-4.4).

## HITL gates

Two: after the draft is assembled (step 8) and before anything is written into a
job folder (step 10). Beyond those, every outward-facing act — email, signature,
DocuSign, OSC write — stays with a person permanently.

## Outputs

- Completed inclusions `.docx` (CD-2, CD-3)
- Completed preliminary agreement `.docx`, where required (CD-4)
- Build contract data sheet (CD-5)
- Pack checklist: general conditions, concept plan, consumer guide, colour options
- Fill report + blank-vs-filled diff as the evidence bundle

## Where this sits in the full chain

```
EOI email ─> OSC job ─> Z: job folders ─> [wait: PLAN] ─> plan updates ─> contract docs ─> DocuSign issue
             [new-job.md]                  [JD-8]         [JD-9]          [THIS WORKFLOW]   [human, always]
```

## Relies on

- [`../rules/contract-docs.md`](../rules/contract-docs.md) — `CD-*`
- [`../rules/job-details.md`](../rules/job-details.md) — `JD-2`, `JD-9`
- [`../scripts/fill_inclusions.py`](../scripts/fill_inclusions.py) — template filler
- [`../scripts/msg_to_text.py`](../scripts/msg_to_text.py) — `.msg` → text + attachments
- `new-contract-template` skill — orchestrates this workflow
- `z-drive-ops` skill — locating the job folder and the template
- `transpire-writing` skill — any drafted email
