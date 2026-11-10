# Job Details Rules — New Job Creation

Transcribed from `OSC new job manual.docx` (see `../reference/README.md`).
Screenshots and client examples stay in the source manual; only the decision
rules live here. Each rule is written to be testable.

## OSC integration scope (11 September 2026)

For `/new-contract-template`, issue #34's Word items 1–9 are implemented through
the [OSC MCP execution reference](../../../.claude/skills/new-contract-template/references/osc-new-contract.md).
Its field map uses live API schemas and IDs. The user's scope excludes DataBuild:
`JD-6` and its wait do not block this intake, and contract values are not
written to OSC. `JD-4.1` stands as written: activities 1, 2 and 6 are
completed at intake (the request email is the evidence for 1 and 2). Activity
6 goes with the job's set-up whether or not DataBuild has the job yet,
because DataBuild work can only start once it is complete (job 26061
feedback sheet, 9 Nov 2026 row 2; until then it waited for the person's word
that the DataBuild entry was done). `JD-7.3`'s legacy sex-based slots are
not used: Word item 9 makes purchasers primary contacts unless the marketer's
sourced instruction says otherwise. Read `JD-8` as the later plan-update stage,
not a prohibition on completing this intake's OSC contacts or contract drafts.
These scoped changes leave the other field rules and document pricing rules intact.

## JD-0 Pre-creation check

- **JD-0.1** Trigger is a new EOI / contract request email. The client ID is
  **optional** (business instruction, 24 Sep 2026 — the manual's "request it
  before proceeding" no longer gates creation): with an ID attached, names
  follow the ID; without one, names follow the EOI and the run flags them for
  a spelling check before issue. Never request or record an ID *number*.
- **JD-0.2** Before creating a job, **search OSC by lot number** to confirm no
  existing job. Only create if the search returns nothing.

## JD-0A Reading the request email (observed, not from the manual)

- **JD-0A.1** Request emails arrive as **forwarded chains** (sales manager to
  contract admin, forwarded marketer email, e-sign notifications). Read the
  whole chain, not just the top message.
- **JD-0A.2** Read the **attachments**, not only the body. Most fields the body
  lacks live in the EOI PDF: site address and spelling, land / building /
  package prices, both clients' names, mobiles, emails and residential address,
  deposit, solicitor. Note the inclusions document. Skip signature images
  (`image*.jpg`, `Outlook-*.png`).
- **JD-0A.3** **The EOI is authoritative over the email body** where they
  disagree. Cite the page.
- **JD-0A.4** **Never record bank or deposit account details** in any output,
  draft, log, or evidence bundle, even though the EOI contains them.

## JD-1 Job creation defaults

- **JD-1.1** Region: `SEQ1` or `SYDNEY01` (pencil icon; choose per the EOI).
- **JD-1.2** Contract No: always use **Generate Contract No** — never typed manually.
- **JD-1.3** Initial Template: always **Pre Sales Investor v1**.
- **JD-1.4** Create New Client using the **name exactly as on ID** when an ID
  is attached; otherwise exactly as typed on the EOI (JD-0.1), flagged.

## JD-2 Site address

- **JD-2.1** Address 1, unregistered land: enter `New Road`; replace with the
  accurate address after the PLAN is received (see JD-9).
- **JD-2.2** Address 1, registered land: full address (street number + street
  name). Registered-land details (street number/name/type, locality) come from
  the **DP & 88B document**.
- **JD-2.3** Address 2: estate name in parentheses, e.g. `(Scenic Rise Estate)`,
  only if applicable.
- **JD-2.4** Suburb: from the EOI, **ALL CAPITALS**, spelling verified by web
  search.
- **JD-2.5** State: `QLD` or `NSW` only.
- **JD-2.6** Postcode: verify by searching "suburb + state".
- **JD-2.7** Job name format: `LOT number.(Street).SUBURB Postcode(s)`.

## JD-3 Job details fields

The fixed values below (JD-3.4 to 3.7, 3.11) fill an **empty** field only. A
value already in OSC is a person's, and is never overwritten by a default
(issue #94 follow-up, 31 Oct 2026).

- **JD-3.1** Stage number: from `Z:\ESTATES INFORMATION` or the request email.
- **JD-3.2** Design Type: the job's storeys, as staff key them: `Single
  Storey`, `Double Storey`, and `Single Storey with AUX Dwelling` / `Double
  Storey with AUX Dwelling` (29 of the 32 newest jobs, 5 Nov 2026). The storeys
  come from the request email, else the SA / EOI's Storey tick, else the plans.
  **Only a granny flat qualifies as an Auxiliary Dwelling.** Written at intake
  wherever OSC has no value yet; not known is left blank with a flag.
  *(Feedback sheet 5 Nov 2026 row 2, job 26060: the rule read "from the request
  email" only, so a Double Storey ticked on the SA went to the manual list.
  On the SA the tick is an ink mark, not a form field: read it off the
  rendered page.)*
- **JD-3.3** Design: from the **plans** - their title block's design, as the
  documents' HOUSE TYPE takes it (CD-2.6, team rule 10 Nov 2026: 26061's email
  said Hyams 145, its plans Custom, and OSC's `Custom + 60` was right); the
  request email's only until the plans arrive, and a later run that reads a
  different design on them flags OSC's Design to check. Façade: the same -
  the plans', as the documents' FAÇADE takes it (CD-2.8). Until the plans
  are out, both come from the request email or the SA / EOI; they usually
  agree with the plans (the team, 10 Nov 2026: 26061 was a rare exception).
  An auxiliary dwelling's
  Design reads `<design> + 60` (`Hyams 145 + 60`, `Breamlea 205 Mod + 60`,
  `Custom + 60`): every one of the 11 aux jobs in OSC since 26027, read
  9 Nov 2026. The inclusions' `<design> + Auxiliary Unit` (CD-6.2) is the
  documents' wording, not OSC's - 26061's intake sent it (feedback sheet
  9 Nov 2026 row 1); the gate warns on it.
- **JD-3.4** Property type: **`Investment`**, unless the request or EOI says
  the buyer will live in it (owner-occupier, or an Owner Occupier template):
  then **`Owner Occupied`**. Never left blank. *(Job 26059 review, issue #94:
  the run left it blank. The sheet says "always Investment", but 6 of the 10
  newest OSC jobs read `Owner Occupied` (29 Oct 2026), so the exception stays.)*
- **JD-3.5** Progress Payment Schedule: the stage names only. `CLAIM 1 - Stage`
  to `CLAIM 6 - Stage` = `Deposit`, `Base`, `Frame`, `Enclosed`, `Fixing`,
  `Practical Completion`; `CLAIM 7` stays blank. Every recent job in both
  regions reads exactly this (29 Oct 2026). The sheet's "Fixed" is OSC's
  `Fixing`. Claim amounts and percentages are contract values and stay out of
  OSC.
- **JD-3.6** Private Certifier: **QLD `Buildable`**; **NSW left blank**
  (issue #94).
- **JD-3.7** Local Council: web-search `suburb + state + Local Council`
  (do not omit any words) and enter the council's name in **CAPITALS**. If
  the result is ambiguous (combination of two councils), check the Estimate
  folder for the project's storage location. Never left blank: a search
  that fails is a flag, not a skip.
- **JD-3.8** Legal information: from the EOI.
- **JD-3.9** Marketer fields: Company in **ALL CAPITALS**; Contact Person with
  **SURNAME IN CAPITALS**; email as given.
- **JD-3.10** After any entry: click **Save and Refresh**.
- **JD-3.11** Job Notes (Reporting): **`CONTRACT SENT, AWAITING EXECUTION`**
  at intake (issue #94).

## JD-4 Job activities

- **JD-4.1** Mark activities **1, 2 and 6** as completed.
- **JD-4.2** Items 1 and 2: double-click "Completion", then OK.
- **JD-4.3** Item 6: double-click "Completion" and tick the box in the pop-up.
  Every question is ticked **Complete**. The only thing to ask the person is
  whether the job is in DataBuild yet. Never ask for DataBuild details
  (issue #94).
- **JD-4.4** Activity 10 "Send EOI (Expression of Interest) to Marketer":
  **N/A**. The marketer sent the EOI, so Transpire never sends one. It is N/A
  on all of the 12 newest jobs (29 Oct 2026, issue #94).

## JD-5 Request-email attachments

- **JD-5.1** Attach the contract request email under **JOB → ADD** with Subject
  `NEW JOB`.
- **JD-5.2** Attach the same email under **Item 11 → ADD**, Subject `NEW JOB`,
  then mark Completion.
- **JD-5.3** All Subject-field text is **UPPERCASE**.

## JD-6 DataBuild handoff

- **JD-6.1** Email the DataBuild administrator (Lisa) to set up the new job,
  stating the **full project name** and the **contract price**.
- **JD-6.2** When the confirmation email returns, **double-check the DataBuild
  price against the price in the request email** before proceeding.

## JD-7 Contact details

- **JD-7.1** Client address: Address 1 only, Address 2 blank; suburb in
  **ALL CAPITALS**; State `QLD`/`NSW`. This is the client's **current
  residence**, not the site. In the API it is the client's **`workAddress`**,
  the address OSC shows on the client and the one staff fill (10 of 10
  staff-created clients, 5 Nov 2026). *(Feedback sheet 5 Nov 2026 row 4: the
  integration wrote `postalAddress`, so 26059's and 26060's client address
  showed blank until a person typed it.)*
- **JD-7.2** Client record: Add full name; Edit to fill Mobile + Email; Primary
  Comm = **Email**.
- **JD-7.3** Purchaser slots (per the manual): male clients → Primary; female
  clients → Secondary; individual (single) clients → Primary.
- **JD-7.4** Sales contact: **Add From Existing**; Relationship field =
  `SALES` (full uppercase, entered manually).
- **JD-7.5** Marketer contact: **Add From Existing**; Relationship field =
  `MARKETER_ cc in all emails` (exact string). *Observed in production
  (15 Oct 2026, the 10 newest jobs):* staff key `MARKETER_CC IN ALL EMAILS`,
  and both the sales and the marketer contact sit on the **client** (no job
  contacts at all); purchasers carry OSC's default `Client Contact`. The
  integrated intake follows the live practice. The contact is the **Marketer
  Contact Person's own record** (the person the request names), never a
  record for the marketing company. That person's Primary Comm is
  **Email** (issue #94).
- **JD-7.6** Tick the Purchaser(s) as primary contact(s) unless the marketer
  has noted otherwise.
- **JD-7.7** Finish with **Save and Close**.
- **JD-7.8** Phone numbers - Legal Reps, Marketers, every person's mobile -
  are typed **4-3-3**: `0412 345 678`, a landline `0290 000 000`, `1300 123
  456`, whatever spacing the source uses. An overseas number stays as given.
  *(Feedback sheet 5 Nov 2026 row 3: the run copied the SA's `02 9000 0000`.
  All 19 Legal Reps and 19 Marketers numbers on the 32 newest jobs read 4-3-3;
  older landlines were keyed 2-4-4 until 2026, so the change is recent
  practice, not the manual.)*

## JD-8 Wait state

- **JD-8.1** After the price check (JD-6.2), the job **waits for the PLAN**.
  No further OSC edits until it arrives.

## JD-9 Post-plan updates

- **JD-9.1** Item 12: attach the plan email, Subject `PLAN FROM XXX`
  (XXX = sender), mark done.
- **JD-9.2** Update Job Details from the PLANS: street name, design type,
  design name, façade.
- **JD-9.3** Update Inclusions from the PLANS: street, house type, house size,
  house façade, garage side.
- **JD-9.4** Modified designs: Kent MOD → `Modified Kent Façade`;
  Macquarie 160 MOD → `Modified Macquarie 160`.
- **JD-9.5** Garage side, judged facing the house: left → `Left Hand Side`;
  right → `Right Hand Side`; behind → `Rear Lane`. **Sydney:** a corner block
  or a lot whose driveway uses a lane → `Via <that street or lane>`, as the
  site plan spells it (`Via Lane` when the lane has no name) — CD-2.9, issue
  #59. Anything the drawing does not show clearly → blank and **flagged for
  the reviewer**, naming the streets the site plan carries; the reviewer
  confirms it or asks the responsible manager (Michael). Never guessed.
- **JD-9.6** Update the street address in **Inclusions**, **Build Contract**
  (also update the SITE) and **Preliminary Contract**.

## JD-10 Z: job folders (observed on the share, not from the manual)

- **JD-10.1** Every region folder under `Z:\PROJECTS\` contains
  `00000 - LOT MASTER FOLDER` — the template tree (~24 folders + seeded
  template documents). A new job = that tree copied within the same region.
- **JD-10.2** Job folder naming (observed): `<job-number> - LOT <lot>
  <STREET>, <SUBURB> <STATE>` with a 5-digit job number (YY0NN style).
  **Job-number source (OSC contract no vs DataBuild) — confirm with the
  business.**
- **JD-10.3** Never overwrite: if any folder for the job number or the same
  lot already exists, stop and flag a duplicate.
- **JD-10.4** Region folder ≠ OSC Region code: `Z:\PROJECTS\` uses
  GUNNEDAH / SEQ / SYDNEY / TAMWORTH / CUDGEN; OSC uses SEQ1 / SYDNEY01.
  Map per job.
- **JD-10.5** The contract request email goes into the job's `CONTRACT
  DOCUMENTATION` as a `.msg`, named as Outlook's Save As names it (the
  subject, `:` and `,` written `_`). Every Sydney job checked holds one
  (26011, 26019, 26032, 26058), and the team added 26060's by hand
  (feedback sheet 5 Nov 2026 row 1). `draft_contract.py` saves it with the
  first drafts on any run that saves into the job folder (CD-7.8).

## Escalations

| Situation | Action |
|---|---|
| Client ID missing from EOI | Not a stop (JD-0.1, 24 Sep 2026): create from the EOI names, flag "no ID — check spelling" in the report |
| Existing job found for lot number | Stop; flag duplicate (JD-0.2) |
| Council lookup ambiguous | Check Estimate folder (JD-3.7) |
| DataBuild price ≠ request-email price | Flag; do not proceed (JD-6.2) |
| Garage side unclear on the rendered site plan | Blank + flag for the reviewer, who confirms or asks Michael (JD-9.5) |
