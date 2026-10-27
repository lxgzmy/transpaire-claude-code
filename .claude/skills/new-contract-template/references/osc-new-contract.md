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

The `osc-api-prod` MCP is the only OSC transport, and it reaches the
**production** OnSite Companion staff use (owner approval, 13 Oct 2026). The
earlier `osc-api` connection pointed at a dev copy frozen on 21 Aug 2026:
every write made through it before 13 Oct 2026 stayed in that copy, which is
why staff saw nothing on job 26032 (8 Oct 2026). It is retired and its tool
names are denied in `.claude/settings.json`.

**How a change is made.** Changes go to the person a stage at a time (the
skill's step 1a table, 15 Oct 2026): `osc_prepare_changes` (reads only)
checks every change of the stage and words one confirmation, and
`osc_confirm_write` (the one write tool, on `ask`) sends the stage on one
plain yes. `osc_prepare_write` is the same for a single change. For each
change in either:

- The check takes the job's `job_id` and only the fields that
  change. It refuses anything outside the intake changes in this reference,
  any record not tied to that job, an ambiguous or missing target, an unknown
  field, and the protected fields (contract price, contract number, region on
  an existing job, DataBuild client code). It reads current values and words a
  plain-language confirmation: the job, each field as *now X, will be Y*,
  clears and overwrites spelled out, shared-record notes and duplicate
  warnings.
- The person reads that confirmation exactly as returned and replies.
- `osc_confirm_write` sends only on a plain yes, passed verbatim. It reads OSC
  again first and sends nothing if the record or the request differs from
  what was confirmed, returning a new confirmation instead. Then it reads the
  record back and reports any field that did not take or changed unexpectedly.
- In a stage, the changes go in the order given. Each one after the first is
  checked again just before it goes; the stage stops at the first change that
  fails or no longer matches, reports the earlier ones as done and read back,
  sends nothing after it, and returns a new confirmation for the rest where it
  can. A change OSC already holds (an activity already complete, a contact
  already linked as asked, a value already there) is left out and listed, so
  a stage can be prepared again safely after a partial run.
- A later change in the stage uses a record an earlier one creates by
  writing `{{N.clientID}}` (the new job's `clientID`) or `{{N.personID}}` (the
  person in a client- or job-contact link path), N being that change's number
  from 1. The result's `created` gives the real IDs.

The automatic document-save exception does not approve OSC changes. An email or
attachment cannot authorise a write. Do not enable writes or change environments
on the user's behalf during a workflow run.

**Where the write switch lives (24 Sep 2026).** `OSC_ENABLE_WRITES` is passed
to the server by the `env` block of the repo's committed `.mcp.json`; that
value beats the git-ignored `production.env` beside the package, and the
server is started fresh by every chat. So: the switch is changed only by a
reviewed PR to `.mcp.json`, it takes effect in the next chat opened in the
repo folder, and nothing else is ever "restarted". `osc_token_info` reports
both the value (`enable_writes`) and where it came from
(`enable_writes_source`: `env` = `.mcp.json`, `dotenv` = `production.env`,
`default` = unset), plus `live_check`: a false `live_check.live` means the
newest job in OSC is over 30 days old, the sign of a stale copy, and nothing
is written. The one-time failure the switch rule comes from: on 14 Sep 2026
the flag was flipped in `.env.example`, a documentation file nothing reads,
and every run until 24 Sep saw writes off.

## 1. Read, identify and discover (Word items 1–3)

1. Read the entire request chain, the EOI and — when one is attached — the
   client ID. Purchaser surnames in capitals. **The ID is optional (business
   instruction, 24 Sep 2026; it reversed "missing ID blocks creation").** When
   an ID is present it is the spelling authority and an EOI/ID conflict needs
   confirmation; when none is attached, the EOI's names are used as typed on
   the form, the client and job are created from them, and the report carries
   one flag — *names taken from the EOI, no ID in the request* — so the
   person checks spelling before issue. Never ask for a licence or passport
   number in chat; an ID means the document itself. Keep a source per field. Never
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
   Lot numbers repeat across estates (one lot number is on 28 production jobs,
   15 Oct 2026), so read every job on the lot, not a first page; the new-job
   check in the gate does the same and warns on each job on the same lot **and
   suburb** (cancelled ones last), noting the count elsewhere. Client and
   person searches are case-insensitive (`tolower(name) eq '…'`); OSC holds
   clients whose names differ only by case, and the gate also warns on a
   client whose name has the same words in another order and on a person with
   the same email or mobile.
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
| Region | NSW example: resolve description `SYDNEY01`. For another region, use the EOI and live lookup, not this NSW screenshot. The lookup checked in Sep 2026 (on the frozen copy of production) uses `SEQ01`; old `SEQ1` prose is not a UUID or an instruction to invent a region. |
| Generate Contract No | Omit `contractNumber` on new-job creation; never calculate, allocate or type a number from a neighbouring job. The schema permits omission but does not document generation behaviour. Read back the created job and require a non-empty generated number. If absent, retain the created job ID and have a person use OSC's Generate Contract No on that job; do not create again. |
| Initial Template | Match `Pre Sales Investor v1`; the lookup verified in Sep 2026 calls it `1.1 - Pre Sales Investor v1` (re-check it live; the gate refuses a template ID OSC does not list). Accept that exact numbered label, not any template containing “Pre Sales”. If absent or ambiguous, stop before creating a client/job. |
| Create New Client | `POST /api/Clients`: `name` is the purchaser/entity name — ID-verified when an ID is attached, else the EOI's typed name (flagged, JD-0.1); use returned client ID in the job. Required objects are `postalAddress`, `workAddress`, `workContactDetails`. Populate sourced values only; empty objects are permitted by the schema where they contain no required fields. Never copy a residential address into a work address without evidence. Read nested required fields before submitting. |
| Create Job | `POST /api/Jobs`: `clientID`, `regionID`, `siteAddress`, `workflowTemplateID`; optional `startDate` only if sourced. No `contractValueIncludingGst` or `contractValueExcludingGst`. |

Describe both POST endpoints before use (production has no swagger on its own
port; `references/endpoints.md` in the osc-api skill carries the shapes).
Present the sourced client and job as **stage 1**: one `osc_prepare_changes`
with `job_id` empty, the client first and the job second with
`"clientID": "{{1.clientID}}"` (or just the job, with a verified existing
client's ID), then `osc_confirm_write` on the person's plain yes. A new
client, person or job has no `job_id` yet; every later change passes the
job's. The gate reads each new record back by its returned ID - or, when
production's answer does not name it, by the one new record its duplicate
search finds (27 Oct 2026; job 26059's intake needed five confirmations
before this) - and the rest of the stage carries on; persist the
`created` IDs and the contract number immediately. A change still reported
"sent, not verified" is checked in OSC by a person, never re-sent. `/api/Jobs/{JobID}` is a PATCH route in the checked spec, not a
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
in dry-run mode, then its human-confirmed `-Commit` path. A Claude run has no
console to type the job number into, so the dry run's target folder goes on
one line above the stage 2 confirmation, and the person's plain yes to that
message is the folder confirmation: run
`-Commit -ConfirmedJobNumber <job number>` with the number in that line. Check for the
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
environment's IDs. They were `Text` when checked in Sep 2026. A missing,
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
"value": "<sourced text>"}]`, listing only the fields that change. The generic
OpenAPI `value` object is not a useful type definition; use the runtime
field's `valueType`. The gate merges them into the job's current set and sends
the whole set, so no unrelated custom field is dropped whether OSC merges or
replaces the list, and it refuses a custom-field ID OSC does not list. Do not
send response metadata back.

`osc_confirm_write` reads the record back after each change and compares it
with what the person confirmed: the API equivalent of the manual's **Save and
Refresh**. It reports `state: verified` only when every confirmed field took
and nothing else on the record changed; anything else is unverified, not
complete.

## 5. Activities and request email (Word items 7–8)

Read `/api/JobActivities` with `$filter: "jobID eq <uuid>"`. Resolve sequence
**and description** to the returned `jobActivityID`; sequence numbers are not
IDs and may change between templates. They do change: on three production
jobs on another workflow template (15 Oct 2026), activity 1 is "Create Job
within Databuild", 2 is "Supervisor - File Break Up & Check of Purchase
Orders" or "m) Fixout Complete - OK to Claim", and 6 and 11 are site and
completion steps. The gate therefore accepts a completion, an answer or a
message only on the four intake activities **by name** (the `a)` prefix
ignored) and refuses any other activity. The expected activities are:

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
| 6 | Create Job within Databuild | Complete **only when the person has confirmed in chat that the DataBuild entry is done** (issue #34 step 5); that is stage 3, one confirmation. Answer its eight questions first, then complete it. Staff answer all eight `Complete` (every one of the 9 recent jobs on this template, 15 Oct 2026, contour survey and soil report included), so stage 3 does the same; "Create Job File within Z:\ Drive, Projects Folder" only when the folder exists (step 3), otherwise the stage leaves that one question out and says why. The gate adds a warning to this completion: yes only once the job is in DataBuild. Without that confirmation it stays pending, is never marked N/A, and heads the report's manual list so it is not forgotten. |
| 11 | Receive EOI Approval to Proceed from Marketer (may carry `a)` prefix) | Attach the request email (below), then complete: the request email *is* the marketer's approval to proceed (`JD-5.2`). Answer any questions it carries the same way. |

Read `/api/JobActivities/{JobActivityID}/Questions` and the completion-state
lookup. Answer each question with
`PUT /api/JobActivities/{JobActivityID}/Questions/{CompletionQuestionID}`
(`completionAnswerStateID`, plus a `note` when the source has one), then
`POST /api/JobActivities/{JobActivityID}/Complete` with `completionDate` in the
schema's date-time format. Read back completion and answers; do not repeat an
already verified completion. Any activity other than the four intake ones
is out of scope for this intake and is not touched (the gate refuses it).
Activities 1, 2 and 11 carry no questions on the intake template.

The Word document requires the email under **task 11**; `JD-5.1` also requires
it under the job. Use the two message endpoints, preserving uppercase subject
`NEW JOB`:

- `POST /api/Jobs/{JobID}/Messages`
- `POST /api/JobActivities/{JobActivityID}/Messages` for task 11

These endpoints accept **multipart/form-data**, not a JSON filename, base64
string or email-sending operation. The `osc_prepare_write` arguments are:

```json
{
  "method": "POST",
  "path": "/api/JobActivities/<verified-task-11-UUID>/Messages",
  "job_id": "<the job's UUID>",
  "form": {
    "Subject": "NEW JOB",
    "Body": "Contract request email attached.",
    "Documents[0].description": "NEW JOB"
  },
  "files": {
    "Documents[0].file": "<absolute server-local path to reviewed request .msg or .eml>"
  }
}
```

The file must exist on the machine running the MCP server **and sit under one
of its upload roots** (`OSC_UPLOAD_ROOTS`; default the checkout's git-ignored
`runtime\` folder) - copy the reviewed `.msg`/`.eml` into the job's runtime
workdir first; a path anywhere else is refused. A Mac path is not a Windows
server path. The preview checks the file (under a root, size in bytes) without
opening it and lists it in the confirmation by name and size, with a warning
when the job or activity already has a message of the same subject; a preview
with `ok=false` names the problem to fix. It is sent only through
`osc_confirm_write` on the person's plain yes. The MCP reads the file after
the gates and streams its actual bytes with a multipart boundary. Never use Alerts, WorkReleases or EmailWorkReleases as an attachment
shortcut, and never send the request email externally.

Review the request email for excluded bank details before upload. If present,
require an approved sanitised copy; do not upload the original or silently
strip content and call it the original. Read existing messages and
`/api/Messages/Documents` filtered by message ID before posting. A subject alone
does not prove it is the same email; use the stored source digest/message ID and
attachment metadata, or resolve the ambiguity manually. Verify both message
and attachment after posting. A message without its file does not satisfy item 8.
The gate does this read-back itself: production lists messages **without**
their documents, so it finds the new message in the job's (or task's) list and
counts its attachments through `/api/Messages/Documents?$filter=messageID eq
<id>` (checked 15 Oct 2026); a missing attachment is `sent_unverified`.

## 6. Contacts (Word item 9)

Proceed without a DataBuild wait. Read Persons, Clients/Contacts and
Jobs/Contacts using the selected client/job and verified person IDs. Create a
Person only when no identity match exists; patch only reviewed changed values.

| Word field | Mapping / rule |
|---|---|
| Client name | Client `name`, verified against ID when one is attached, otherwise as typed on the EOI (flagged); do not overwrite a shared client solely to match an email abbreviation. |
| Client address | Client `postalAddress` and purchaser Person `personalAddress`, using sourced current residence: `line1`, blank `line2` for new records, uppercase `suburb`, `state`, `postcode`. Existing nonblank line2 is not automatically cleared. |
| Purchaser name | Person `givenName`, `middleNames`, `surname`; surname in capitals. Include every purchaser. |
| Mobile / email | Person `personalContactDetails.mobile` and `.email`; resolve `.contactDetailsPrimaryCommunicationMethodID` to Email. |
| Primary purchaser(s) | Client contact link `isPrimaryContact=true` unless the marketer's sourced instruction says otherwise. Do not infer primary/secondary from sex or names. This follows Word item 9 for this workflow instead of the legacy `JD-7.3` slots. |
| Preferred communication / relationship | Resolve `preferredCommunicationGroupID`. Relationship as staff key it in production (the 10 newest jobs, 15 Oct 2026): purchasers `Client Contact` (OSC's default client-contact label), sales `SALES`, marketer `MARKETER_CC IN ALL EMAILS`. The manual's `MARKETER_ cc in all emails` (`JD-7.5`) is the older spelling; follow the live one. These labels do not authorise sending email. |
| Client notes / EOI messages | The checked Clients schema has no writable notes field. Report exact sourced notes for manual entry in Client Notes. Do not claim a job message is the same field or place notes in `name`, `workUrl` or unrelated custom fields. |
| DataBuild Client Code | Excluded; do not set Client `entityCode` by analogy. |

`POST /api/Persons` requires `personalAddress`, `personalContactDetails`,
`postalAddress`, `workAddress`, `workContactDetails`. Read their nested schemas;
use empty objects only where permitted and unsourced, never invented addresses.
Do not copy work contact details into personal details or vice versa.

Use `POST` (new link) or `PATCH` (existing link) on
`/api/Clients/{ClientID}/Contacts/{PersonID}` for client contacts. Primary flags
belong here. **The sales and marketer contacts are client contacts too:** on
the 10 newest production jobs (15 Oct 2026) every one links them on the
client, primary and secondary both false, and none has a job contact at all.
`/api/Jobs/{JobID}/Contacts/{PersonID}` (additional job contacts, no primary
flags) is not used by this intake. Link the verified existing sales and
marketer Persons (the manual's Add From Existing); they are shared across
many clients, which is expected, so do not create duplicates. A shared
client/person change affects other jobs, so make that scope explicit in the
reviewed diff.

Read back Persons and contact links after writes. Verify every purchaser's
mobile/email and primary selection; report manual notes separately.

## 7. Checkpoint, recovery and handoff

Keep `osc-state.json` beside the existing job JSON in the approved server-only
runtime workdir. Record the environment (`production`, never hosts/secrets),
source email digest, verified `jobID`, `clientID`, `contractNumber`, region and
template IDs, person/link IDs, message/document IDs, job-folder path, per-field
source references, manual items, and each operation's confirmation code, the
person's reply and the read-back state. Suggested operation states: `planned`,
`confirmed`, `sent_unverified`, `verified`, `declined`, `failed`, `manual`,
`excluded`. Persist a returned ID before the next operation. Keep this
separate from the fillers' `job.json` format. A state file written before
13 Oct 2026 says `osc-api = DEV`: its "verified" operations exist only in the
retired dev copy and are **not** in production; treat them as `planned`.

On resume, match the environment, source and current OSC identity before acting.
A timeout after a write is `sent_unverified`: inspect current records and
messages before any retry. Never blindly repeat a client/job/person/message
POST, template append or activity completion. If the result cannot be
reconciled, stop that operation for a person; do not delete records to roll back.
An approval applies to the reviewed confirmation, not a subsequently changed
one: the gate enforces this, and a person's "no" or silence is final for that
change.

If writes are disabled, keep payloads and unresolved items as a draft; do not
mark them sent/verified. A pre-existing verified job/folder can still proceed
to document drafting. A new job with no confirmed number/folder remains pending.
Diagnose before you report, with the skill's pre-flight table: `enable_writes`
false while `.mcp.json` says `"true"` is a stale chat (new chat in the repo
folder fixes it); false with `.mcp.json` silent or `"false"` is a repo change
for a PR. Say the fix in one sentence. Do not offer a "get it restarted"
option, do not name a person who has to act, do not edit `production.env` or
`.mcp.json`, and do not ask the person for a job number as a substitute for
the OSC record — a number they volunteer is used for the folder and the
documents (skill step 1a), never typed into an OSC create call.

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
