# Job Details Rules — New Job Creation

Transcribed from `OSC new job manual.docx` (see `../reference/README.md`).
Screenshots and client examples stay in the source manual; only the decision
rules live here. Each rule is written to be testable.

## JD-0 Pre-creation check

- **JD-0.1** Trigger is a new EOI / contract request email. If the client ID is
  not attached, request it before proceeding.
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
- **JD-1.4** Create New Client using the **name exactly as on ID**.

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

- **JD-3.1** Stage number: from `Z:\ESTATES INFORMATION` or the request email.
- **JD-3.2** Design Type: from the request email. **Only a granny flat
  qualifies as an Auxiliary Dwelling.**
- **JD-3.3** Design & Façade: from the request email.
- **JD-3.4** Property type: most jobs are **investment** (confirm from EOI).
- **JD-3.5** Progress Payment Schedule: set per the EOI.
- **JD-3.6** Private Certifier: **all QLD projects are marked "Buildable"**
  (NSW rule: confirm — not stated in the manual).
- **JD-3.7** Local Council: web-search `suburb + state + Local Council`
  (do not omit any words). If the result is ambiguous (combination of two
  councils), check the Estimate folder for the project's storage location.
- **JD-3.8** Legal information: from the EOI.
- **JD-3.9** Marketer fields: Company in **ALL CAPITALS**; Contact Person with
  **SURNAME IN CAPITALS**; email as given.
- **JD-3.10** After any entry: click **Save and Refresh**.

## JD-4 Job activities

- **JD-4.1** Mark activities **1, 2 and 6** as completed.
- **JD-4.2** Items 1 and 2: double-click "Completion", then OK.
- **JD-4.3** Item 6: double-click "Completion" and tick the box in the pop-up.

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
  residence**, not the site.
- **JD-7.2** Client record: Add full name; Edit to fill Mobile + Email; Primary
  Comm = **Email**.
- **JD-7.3** Purchaser slots (per the manual): male clients → Primary; female
  clients → Secondary; individual (single) clients → Primary.
- **JD-7.4** Sales contact: **Add From Existing**; Relationship field =
  `SALES` (full uppercase, entered manually).
- **JD-7.5** Marketer contact: **Add From Existing**; Relationship field =
  `MARKETER_ cc in all emails` (exact string).
- **JD-7.6** Tick the Purchaser(s) as primary contact(s) unless the marketer
  has noted otherwise.
- **JD-7.7** Finish with **Save and Close**.

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
  right → `Right Hand Side`; behind → `Rear Lane`. Anything else →
  **escalate to the responsible manager (Michael)** — do not guess.
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

## Escalations

| Situation | Action |
|---|---|
| Client ID missing from EOI | Ask the sender (JD-0.1) |
| Existing job found for lot number | Stop; flag duplicate (JD-0.2) |
| Council lookup ambiguous | Check Estimate folder (JD-3.7) |
| DataBuild price ≠ request-email price | Flag; do not proceed (JD-6.2) |
| Garage side unclear | Escalate to Michael (JD-9.5) |
