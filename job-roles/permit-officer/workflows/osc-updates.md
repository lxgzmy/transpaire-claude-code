# Workflow: OSC record-keeping for building approvals

Claude keeps the routine building-approval record in OnSite Companion (OSC)
up to date for the permit officer: it ticks the step, posts the note and files
the certifier's email, and the officer says yes once per job update. Sanctioned
on 23 Oct 2026 (issue #ISSUE, owner sign-off; root `CLAUDE.md`). Rules `PO-7`,
`PO-9`, `PO-13`, `PO-14`.

The weekly BA report (`ba-weekly-report.md`) still writes nothing. This
workflow is separate, and the report reads its ticks like any other.

## What Claude may change

Only on **NSW jobs in `3. Pre-Construction`** (or `20. Test Job`), and only
through the `osc-api-prod` gate with `workflow="permit-officer"`:

1. **Tick one of ten activities complete**, matched by exact name, never by
   number (Receive RFI from Certifier is activity 60 on two pilot jobs and 61
   on the third).
2. **Add a message** to the job, or to one of those ten activities.
3. **Attach a certifier or council email or document** to that message,
   exactly as received.

| Activity (exact OSC name) | Must be complete (or N/A) first | BA report column |
|---|---|---|
| Submit Covenant Application | none | Covenant Ordered |
| Receive Covenant Approval & Upload to OSC | Submit Covenant Application | Received Covenant Approval |
| Forward Covenant Application Approval to Private Certifier | Receive Covenant Approval & Upload to OSC | |
| Receive RFI from Certifier | Submit Documents to Private Certifier for Building Approval Application | Received RFI |
| Return RFI Information to Certifier | Receive RFI from Certifier | Submit all RFI Items |
| Pay Q Leave / Long Service Levy | none | |
| Pay QBCC Home Warranty Insurance / Home Building Compensation Fund | none | |
| Pay Construction Works Insurance | none | |
| Email Copy of Relevant Insurances to Certifier | the three Pay steps | |
| h) Building Approval Received from Certifier | Submit Documents to Private Certifier for Building Approval Application | BA Received |

*Email Copy of Relevant Insurances to Certifier* carries three completion
questions (one per insurance) on every pilot job, checked 23 Oct 2026. The
gate refuses a tick on any activity with completion questions, so in practice
the officer ticks that one in OSC.

Left off on purpose: *Review RFI Information Request from Certifier* (ticking
it says the RFI has been analysed, the officer's call, PO-13), *Submit
Documents to Private Certifier…* (lodgement is a portal step, PO-14), the
engineering chains, *Upload Building Approval Documents to OSC* and *Check
Building Approval Documents*. Adding any is a sign-off and a code change.

## How a run goes

1. **Pre-flight.** `osc_token_info`: `environment` is `production` and
   `live_check.live` is true, or stop.
2. **Find the job.** Contract number → `jobID` (`osc-api` skill, golden rule
   3). Read its activities and documents.
3. **Gather the evidence** for each change: the certifier's or council's
   email (the permits mailbox once wired in), a document already on the job,
   or the officer's own words. If the email names a lot or address rather
   than our job number, say what it was matched on.
4. **Prepare one update per job**: `osc_prepare_changes(job_id, changes,
   workflow="permit-officer")`, changes in workflow order, for example:

   ```
   [{"method": "POST", "path": "/api/JobActivities/<id>/Complete",
     "body": {"completionDate": "2026-10-20"},
     "note": "date from the certifier's email received 20 Oct 2026"},
    {"method": "POST", "path": "/api/JobActivities/<id>/Messages",
     "form": {"Subject": "RFI RECEIVED",
              "Body": "RFI received from the certifier, 6 items. The RFI is attached.",
              "Documents[0].description": "RFI"},
     "files": {"Documents[0].file": "<checkout>\\runtime\\permit-officer\\evidence\\<job>\\RFI.msg"}}]
   ```

   Every tick needs a `note` saying where its date comes from. An
   attachment must sit under `runtime\` (the officer saves the `.msg` there;
   the Outlook connector cannot export one). A tick earlier in the same
   update counts as the step before.
5. **Show `confirmation_text` exactly as written** and wait. Nothing else in
   the same message competes with it.
6. **The officer's reply goes to `osc_confirm_write` verbatim.** Only a plain
   yes sends. "No" cancels. Anything else sends nothing: prepare what they
   asked for instead and show its confirmation.
7. **Relay `result_text`.** `verified` means it is in OSC and read back.
   `sent_unverified` means look in OSC before anything else. `stopped` comes
   with a fresh confirmation for the rest.

## Completion dates

`completionDate` is the day the event happened, as a Sydney calendar date
(`YYYY-MM-DD`). It is what the BA report prints. OSC records when the tick was
entered separately (`completionDateLastUpdatedOnUtc`), so the audit trail
stays. Today the officer ticks on the day; a date before today is new
behaviour, so the confirmation always says how far back it is.

## What stops a change, and what is only a line in the confirmation

The gate refuses only what would be wrong. Everything else is one line inside
the same confirmation, never a second question.

| Refused (nothing is sent) | One line in the confirmation |
|---|---|
| Activity not one of the ten, or on another job | The date is before today: a note, and a warning past 14 days |
| The job is not NSW, or not in pre-construction (or test) | A Pay tick: "say yes only if this has been paid" |
| The step before is still open | Building Approval Received while Return RFI is still open |
| Date after today (Sydney time), before the job was created, or before the step before was completed | A message with the same subject is already there |
| Completion questions on the activity | The job has no activity for the step before |
| Two open activities with the same name | |
| No `note` on a tick, or a date not written `YYYY-MM-DD` | |

## Messages

- Facts only: what arrived or went out, when, and who an item now sits with.
  Never what an RFI item needs or how to answer it (PO-13).
- Subjects in CAPS. Proposed, to settle with the officer: `RFI RECEIVED`,
  `RFI ITEM SENT`, `RFI RETURNED`, `COVENANT APPROVED`, `BA RECEIVED`.
- The text goes through `transpire-writing` (staff read it).
- A message is not an alert: it may not notify anyone (to confirm on the test
  job). Coordination that needs someone to act still goes by an OSC alert the
  officer sends (PO-9).

## Who answers

Only the permit officer, in their own Claude session. Whoever else operates
Claude never answers for the officer, and Claude never answers its own
confirmation. `osc_confirm_write` stays on `ask` in `.claude/settings.json`.

## The record

Every answered confirmation, sent or not, is a line in
`runtime\permit-officer\logs\osc-writes.jsonl` (git-ignored, on `Z:`): the
time, job, each change as shown, the reply exactly as typed, and what
happened. It is how the pilot counts "zero unapproved writes", and how the BA
drafter can tell Claude's ticks from the officer's.

## Stays with a person

RFI judgement and responses (PO-13); every portal (PO-14); payments; email to
the certifier, council, developer or consultants; staff alerts; marking an
activity not applicable; and undoing a mistake (the API cannot un-tick an
activity or delete a message, so a person fixes it in OSC).

## Before the first real job

No job sat in `20. Test Job` on 23 Oct 2026, so a person sets one up (NSW
site, a pre-construction template). On it, settle:

1. Does completing any of the ten email anyone, create an inspection, or
   start another activity?
2. Does a message notify anyone, and who?
3. Does a message attachment also appear in the job's Document Manager?
   If not, filing straight into Document Manager (`POST
   /api/Jobs/{JobID}/Documents`) is a separate change, once the API spec is
   reachable on the server.
4. With the officer: the message subjects, and the attachment descriptions
   they want.

Then real NSW jobs, one update at a time.
