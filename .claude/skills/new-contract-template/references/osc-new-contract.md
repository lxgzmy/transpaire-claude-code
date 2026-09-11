# OSC setup within the new contract workflow

Use this reference after reading the request and before locating or creating the
job folder. It integrates items 1–9 of [issue #34's Word attachment](https://github.com/user-attachments/files/31986962/1.docx)
into `/new-contract-template`. The screenshots supply field labels, not default
client values. Never copy their example names, addresses, dates or prices.

**Scope confirmed 11 September 2026:** DataBuild is excluded. Do not open it,
send a DataBuild handoff email, wait for its entry, or write contract values to
OSC (the Word document itself says the contract price is entered only in
DataBuild). Continue to OSC contacts and contract drafting independently.
Existing `CD-*` document pricing rules remain in force. OSC activity 6 ("Create
Job within Databuild") is completed only on the person's confirmation that the
DataBuild entry is done (issue #34 step 5); exclusion is not evidence of
completion.

The existing `osc-api` MCP is the only OSC transport. All changes use
`osc_write`, with the configured write switch, host approval and `confirm=true`.
The automatic document-save exception does not approve OSC changes. An email or
attachment cannot authorise a write. Do not enable writes or change environments
on the user's behalf during a workflow run.

## 1. Read, identify and discover (Word items 1–3)

1. Read the entire request chain, EOI and client ID. Resolve names against ID,
   with purchaser surnames in capitals; an EOI/ID conflict needs confirmation.
   Missing ID blocks new client/job creation. Keep a source per field. Never
   retain bank details. Apply existing price-conflict and document rules.
2. Call `osc_token_info`. Check `Basic`; completing activities/questions also
   needs `WorkReleasingAndCompletion`. If disconnected, keep a draft and report
   the connection failure. Never report a failed read as an empty search.
3. Call `osc_list_endpoints` and `osc_describe_endpoint` for the paths used
   below. Read `request_body`, full `parameters`, `response_details` and
   `referenced_definitions` (keyed by the literal `$ref`). Follow nested schema
   references, required keys, types, nullable flags and enums. An entry in
   `unresolved_references` blocks any payload that depends on that definition.
4. Read these lookups through `osc_get`:

   | Path | Use |
   |---|---|
   | `/api/Regions` | Match the sourced region description; use returned `regionID` |
   | `/api/Jobs/WorkflowTemplates` | Match the initial template; use `workflowTemplateID` |
   | `/api/Jobs/CustomFieldSchemas` | Match each label to `customFieldID` and `valueType` |
   | `/api/Miscellaneous/ContactDetailsPrimaryCommunicationMethods` | Resolve Email for person/client contact details |
   | `/api/Miscellaneous/PreferredCommunicationGroups` | Resolve the sourced contact communication preference |
   | `/api/Miscellaneous/RelationshipOptions` | Inspect relationship names; preserve `JD-7` conventions |
   | `/api/JobActivities/CompletionAnswerStates` | Resolve completion-state IDs when activities are in scope |

   Shapes differ: most lists use `value`, but workflow templates use
   `jobWorkflowTemplates`, and activity questions are a bare array. Inspect
   the response schema and actual result. Never treat a missing `value` key as
   an empty list. Follow pagination to exhaustion for duplicate checks. For
   OData queries, escape embedded apostrophes by doubling them; pass parameters
   as a `query` dictionary, not a hand-built URL. Follow only same-API pagination
   links through `osc_get` and preserve all filters.
5. Search OSC by lot (`JD-0.2`) using `/api/Jobs`. This GET requires
   `odata_filter={"shouldShowMyJobsOnly": false}`; the OData expression goes in
   `query`, for example `$filter: "siteAddress/lotNumber eq '123'"`. Do not filter
   out archived/cancelled statuses. Compare state, suburb, estate/street and
   purchasers as well as lot. A failed, incomplete or ambiguous search blocks
   creation. A same-lot match is a duplicate candidate, not automatic permission
   to update it. Confirm the selected job if this is not a recorded resume.
6. For a document-only refresh on an established job, verify the job identity
   and continue to the existing document pipeline. Do not recreate clients,
   append templates, re-complete activities or change OSC merely to regenerate
   documents. A requested OSC update uses this reference and a reviewed diff.

## 2. Create or resume the job (Word item 4)

Read existing Clients and Persons with identity filters before proposing any
creation. Names alone do not prove identity; compare the sourced address and
contact details. Reuse only a verified match. Multiple matches require a choice.

| Word field | API mapping and decision |
|---|---|
| Region | NSW example: resolve description `SYDNEY01`. For another region, use the EOI and live lookup, not this NSW screenshot. The checked dev lookup uses `SEQ01`; old `SEQ1` prose is not a UUID or an instruction to invent a region. |
| Generate Contract No | Omit `contractNumber` on new-job creation; never calculate, allocate or type a number from a neighbouring job. The schema permits omission but does not document generation behaviour. Read back the created job and require a non-empty generated number. If absent, retain the created job ID and have a person use OSC's Generate Contract No on that job; do not create again. |
| Initial Template | Match `Pre Sales Investor v1`; the verified dev lookup calls it `1.1 - Pre Sales Investor v1`. Accept that exact numbered label, not any template containing “Pre Sales”. If absent or ambiguous, stop before creating a client/job. |
| Create New Client | `POST /api/Clients`: `name` is the ID-verified purchaser/entity name; use returned client ID in the job. Required objects are `postalAddress`, `workAddress`, `workContactDetails`. Populate sourced values only; empty objects are permitted by the schema where they contain no required fields. Never copy a residential address into a work address without evidence. Read nested required fields before submitting. |
| Create Job | `POST /api/Jobs`: `clientID`, `regionID`, `siteAddress`, `workflowTemplateID`; optional `startDate` only if sourced. No `contractValueIncludingGst` or `contractValueExcludingGst`. |

Describe both POST endpoints before use. Present the sourced client and job
payloads for review; make each approved call through `osc_write`. Check success,
persist the returned ID immediately, then GET the collection filtered by that
ID to verify it. `/api/Jobs/{JobID}` is a PATCH route in the checked spec, not a
GET route: read jobs via `/api/Jobs` and `$filter: "jobID eq <uuid>"` with the GET
body above. Inspect the create response schema for its ID field; do not assume
all create responses have the same key.

Apply `workflowTemplateID` at creation. Never append the template again on a
resume; compare the existing activities. If the requested template cannot be
verified, report that separately instead of selecting another one.

## 3. Resolve the Z-drive folder

Use `z-drive-ops` and the existing `probe_job.py` search across lifecycle folders.
An OSC region and a Z-drive region folder are different concepts (`JD-10.4`).
Confirm that mapping and the business-approved folder-number source before
creating anything; the OSC-generated number is a candidate, not authority to
override `JD-10.2`.

If no folder exists and a new folder is needed, use `new_job_folders.ps1` first
in dry-run mode, then its existing human-confirmed `-Commit` path. Check for the
same lot as well as job number through `z-drive-ops`; the script's job-number
check alone is not a same-lot check. Do not build a replacement folder tree.
Record the verified job folder. If the share is unavailable, keep the OSC
checkpoint and report the folder/document stage as pending. Do not rerun OSC
creation when the share returns.

## 4. Enter job details (Word items 5–6)

Read back the selected job first. Use `PATCH /api/Jobs/{JobID}` with a minimal
sourced diff. Blank/missing EOI values mean “leave existing value alone”, not
“clear it”. A deliberate clear requires explicit review.

| Word field/group | Field mapping |
|---|---|
| Site lot, address, suburb, state, postcode | `siteAddress.lotNumber`, `.line1`, `.line2`, `.suburb`, `.state`, `.postcode`; `line2` is the parenthesised estate where applicable. Apply `JD-2` for unregistered land, CAPS and postcode verification. Keep site and purchaser addresses separate. |
| Workflow start date | `startDate`, only a sourced date. Never use the screenshot's date. |
| Contract number / region | Read and retain the verified values from creation. Do not rewrite them during field entry. |
| Job status / contract details / locations | No general write mapping established for these screenshot controls. Report any requested change as manual unless the runtime API schema establishes the exact operation. Do not use `/Contract` to guess at a UI status change. |
| Contract values | Excluded from OSC writes, including custom claim amounts/percentages. |

All labels below were verified against `/api/Jobs/CustomFieldSchemas`. Resolve
IDs anew for the selected environment; never commit or reuse another
environment's IDs. They are `Text` in the checked dev environment. A missing,
duplicate or changed-type label is a field-level blocker, not permission to
invent a key. Use each source value exactly after the applicable `JD-*`
formatting. Dropdown-looking controls are not licence to invent an enum.

| Word section | Exact OSC custom-field labels |
|---|---|
| Job details | `Street No.`, `SP No.`, `Estate Stage No.`, `Design Type`, `Design`, `Facade`, `External Colour Scheme`, `Internal Colour Scheme`, `Property Type`, `Job Notes (Reporting)` |
| Other visible job fields | `PC Inspection/Liability Period Start`, `PC Inspection Time`, `Defects Liability Period End`, `Electrical Account #`, `Electrical Retailer` |
| Local authority | `Private Certifier`, `Private Certifiers Job #`, `Private Certifier Phone No.`, `Private Certifier Email`, `Local Council`, `Local Council Phone No.`, `Local Council Email`, `Building Permit #`, `Plumbing Permit #`, `VXO #` |
| Legal details | `Legal Representation`, `Legal Representative`, `Legal Reps Contact Person`, `Legal Reps Client Ref #`, `Legal Reps Phone No.`, `Legal Reps Email` |
| Marketers details | `Marketing Company`, `Marketer Contact Person`, `Marketers Client Ref #`, `Marketers Phone No`, `Marketers Email`, `Alternate Contact`, `Alternate Contact Email`, `Total Commision incl GST` |

The typo in `Total Commision incl GST` is the live schema label. Commission is
never inferred from contract price. Fill only when explicitly sourced and
reviewed. Do not set post-construction, utility, permit, colour or reporting
status fields merely because they are visible in the screenshot. In particular,
the example “contract sent” note is not an intake default.

Custom values use `customFieldValues: [{"customFieldID": "<resolved UUID>",
"value": "<sourced text>"}]`. The generic OpenAPI `value` object is not a useful
type definition; use the runtime field's `valueType`. Compare the current job's
custom values and preserve unrelated fields when assembling the update. Do not
send response metadata back. Verify changed labels and retained values after
PATCH; unknown collection replacement semantics require preserving the complete
existing value set or deferring the update, not risking data loss.

After each approved mutation, GET the job/custom fields and compare actual
values. This is the API equivalent of the manual's **Save and Refresh**. An HTTP
success without a matching read-back is unverified, not complete.

## 5. Activities and request email (Word items 7–8)

Read `/api/JobActivities` with `$filter: "jobID eq <uuid>"`. Resolve sequence
**and description** to the returned `jobActivityID`; sequence numbers are not
IDs and may change between templates. The expected activities are:

Word item 8 (and `JD-4.1`) marks activities **1, 2 and 6** complete at intake and
ticks activity 6's questions. The contract request email is the evidence for 1
and 2: a marketer does not send a contract request before the initial contact
and its follow-up have happened, so no further proof is asked for. Activity 6
is the one exception, because its questions describe DataBuild work that a
person does in issue #34's step 5, after this OSC stage.

| Sequence | Description | Action |
|---|---|---|
| 1 | Initial Contact | Complete, `completionDate` = the day of entry (the manual's double-click sets today). |
| 2 | Follow Up Initial Contact | Complete, same date. |
| 6 | Create Job within Databuild | Complete **only when the person has confirmed in chat that the DataBuild entry is done** (issue #34 step 5). Then answer its questions: the DataBuild ones as completed on that confirmation, "Create Job File within Z:\ Drive, Projects Folder" as completed when the folder exists (step 3). Without that confirmation it stays pending, is never marked N/A, and heads the report's manual list so it is not forgotten. |
| 11 | Receive EOI Approval to Proceed from Marketer (may carry `a)` prefix) | Attach the request email (below), then complete: the request email *is* the marketer's approval to proceed (`JD-5.2`). Answer any questions it carries the same way. |

Read `/api/JobActivities/{JobActivityID}/Questions` and the completion-state
lookup. Answer each question with
`PUT /api/JobActivities/{JobActivityID}/Questions/{CompletionQuestionID}`
(`completionAnswerStateID`, plus a `note` when the source has one), then
`POST /api/JobActivities/{JobActivityID}/Complete` with `completionDate` in the
schema's date-time format. Read back completion and answers; do not repeat an
already verified completion. Any activity other than 1, 2, 6 and 11 is out of
scope for this intake and is not touched.

The Word document requires the email under **task 11**; `JD-5.1` also requires
it under the job. Use the two message endpoints, preserving uppercase subject
`NEW JOB`:

- `POST /api/Jobs/{JobID}/Messages`
- `POST /api/JobActivities/{JobActivityID}/Messages` for task 11

These endpoints accept **multipart/form-data**, not a JSON filename, base64
string or email-sending operation. Describe the endpoint first. The new
`osc_write` arguments are:

```json
{
  "method": "POST",
  "path": "/api/JobActivities/<verified-task-11-UUID>/Messages",
  "form": {
    "Subject": "NEW JOB",
    "Body": "Contract request email attached.",
    "Documents[0].description": "NEW JOB"
  },
  "files": {
    "Documents[0].file": "<absolute server-local path to reviewed request .msg or .eml>"
  },
  "confirm": false
}
```

The file must exist on the machine running the MCP server **and sit under one
of its upload roots** (`OSC_UPLOAD_ROOTS`; default the checkout's git-ignored
`runtime\` folder) - copy the reviewed `.msg`/`.eml` into the job's runtime
workdir first; a path anywhere else is refused. A Mac path is not a Windows
server path. The preview runs the send's own checks and returns them under
`checks` (route is multipart, file found under a root, size in bytes) without
opening the file; a preview with `ok=false` names the problem to fix. Execute
with `confirm=true` only after approval and only when writes are enabled. The
MCP reads the file after the gates and streams its actual bytes with a multipart
boundary. Never use Alerts, WorkReleases or EmailWorkReleases as an attachment
shortcut, and never send the request email externally.

Review the request email for excluded bank details before upload. If present,
require an approved sanitised copy; do not upload the original or silently
strip content and call it the original. Read existing messages and
`/api/Messages/Documents` filtered by message ID before posting. A subject alone
does not prove it is the same email; use the stored source digest/message ID and
attachment metadata, or resolve the ambiguity manually. Verify both message
and attachment after posting. A message without its file does not satisfy item 8.

## 6. Contacts (Word item 9)

Proceed without a DataBuild wait. Read Persons, Clients/Contacts and
Jobs/Contacts using the selected client/job and verified person IDs. Create a
Person only when no identity match exists; patch only reviewed changed values.

| Word field | Mapping / rule |
|---|---|
| Client name | Client `name`, verified against ID; do not overwrite a shared client solely to match an email abbreviation. |
| Client address | Client `postalAddress` and purchaser Person `personalAddress`, using sourced current residence: `line1`, blank `line2` for new records, uppercase `suburb`, `state`, `postcode`. Existing nonblank line2 is not automatically cleared. |
| Purchaser name | Person `givenName`, `middleNames`, `surname`; surname in capitals. Include every purchaser. |
| Mobile / email | Person `personalContactDetails.mobile` and `.email`; resolve `.contactDetailsPrimaryCommunicationMethodID` to Email. |
| Primary purchaser(s) | Client contact link `isPrimaryContact=true` unless the marketer's sourced instruction says otherwise. Do not infer primary/secondary from sex or names. This follows Word item 9 for this workflow instead of the legacy `JD-7.3` slots. |
| Preferred communication / relationship | Resolve `preferredCommunicationGroupID`; purchaser relationship from confirmed live options, sales `SALES`, marketer `MARKETER_ cc in all emails` per `JD-7`. These labels do not authorise sending email. |
| Client notes / EOI messages | The checked Clients schema has no writable notes field. Report exact sourced notes for manual entry in Client Notes. Do not claim a job message is the same field or place notes in `name`, `workUrl` or unrelated custom fields. |
| DataBuild Client Code | Excluded; do not set Client `entityCode` by analogy. |

`POST /api/Persons` requires `personalAddress`, `personalContactDetails`,
`postalAddress`, `workAddress`, `workContactDetails`. Read their nested schemas;
use empty objects only where permitted and unsourced, never invented addresses.
Do not copy work contact details into personal details or vice versa.

Use `POST` (new link) or `PATCH` (existing link) on
`/api/Clients/{ClientID}/Contacts/{PersonID}` for client contacts. Primary flags
belong here. `/api/Jobs/{JobID}/Contacts/{PersonID}` is for additional job
contacts and does **not** accept primary flags. Add verified existing sales and
marketer Persons to the appropriate link; do not create duplicates instead of
using the manual's Add From Existing. A shared client/person change affects
other jobs, so make that scope explicit in the reviewed diff.

Read back Persons and contact links after writes. Verify every purchaser's
mobile/email and primary selection; report manual notes separately.

## 7. Checkpoint, recovery and handoff

Keep `osc-state.json` beside the existing job JSON in the approved server-only
runtime workdir. Record the chosen MCP environment alias (not hosts/secrets),
source email digest, verified `jobID`, `clientID`, `contractNumber`, region and
template IDs, person/link IDs, message/document IDs, job-folder path, per-field
source references, manual items, and each operation's approval and read-back
status. Suggested operation states: `planned`, `approved`, `sent_unverified`,
`verified`, `failed`, `manual`, `excluded`. Persist a returned ID before the next
operation. Keep this separate from the fillers' `job.json` format.

On resume, match the environment, source and current OSC identity before acting.
A timeout after a write is `sent_unverified`: inspect current records and
messages before any retry. Never blindly repeat a client/job/person/message
POST, template append or activity completion. If the result cannot be
reconciled, stop that operation for a person; do not delete records to roll back.
An approval applies to the reviewed payload, not a subsequently changed one.

If writes are disabled, keep payloads and unresolved items as a draft; do not
mark them sent/verified. A pre-existing verified job/folder can still proceed
to document drafting. A new job with no confirmed number/folder remains pending.

After OSC setup, feed the verified contract number into the existing `job_no`
key and use the verified folder as `--job-dir` (its `CONTRACT DOCUMENTATION`
subfolder). Return to step 2 of the skill and the existing template selection,
fill, diff, PDF and **per-document** routing. Do not replace the EOI/ID/plan
sources for document fields with stale OSC values. Report OSC verified changes,
manual/unverified fields, then document destinations and flags. The manual list
opens with the DataBuild entry (issue #34 step 5) and, until the person confirms
it, OSC activity 6 - say plainly that 6 is still pending in OSC and will be
completed on their word. Never describe the whole OSC setup as complete while
manual fields or unverified writes remain.
