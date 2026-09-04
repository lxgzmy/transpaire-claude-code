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
   folder agreed at discovery (`Z:\AI test\Permit Officer`; the folder
   exists and holds procedure documents, but no past RFIs yet). NSW
   standard-form RFIs are the priority training material.
2. **Trigger wiring** — confirm how the pre-lodgement notification reaches
   the workflow (mailbox rule vs manual invocation) with the officer.

## Out of scope

Ordering anything, contacting anyone, or lodging — the checklist is advice.
