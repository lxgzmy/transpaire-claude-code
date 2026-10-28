# DocuSign draft envelope at the end of `/new-contract-template`

Design, 13 October 2026. Decided in a brainstorming session with the
Contract-Admin owner; the answers that shaped it are recorded in
[Decisions](#decisions) so they are not re-argued later.

> **Superseded in part, 13 October 2026.** Step 8 no longer calls the hosted
> `createEnvelope`. It creates the draft through the local `docusign-upload`
> server with the job's own PDFs, so staff no longer swap placeholder PDFs
> ([design](2026-10-13-docusign-upload-mcp.md), CD-10). The template pick,
> recipients, subject, message, `JobNo` and the payload script below still
> hold. The tab statement under "What the MCP can and cannot do" was wrong
> and is corrected there.

## Goal

When the run has saved a real build contract into a job's folder, it also
creates a **draft** envelope in DocuSign from the right company template, with
the buyers filled in and a job-specific subject and message. Staff open the
draft in DocuSign, put the job's PDFs in, check it, and send. The run never
sends.

## What the MCP can and cannot do (verified 13 Oct 2026)

- The `docusign-demo` MCP server (sandbox) exposes `createEnvelope`, which
  takes a `templateId`, `templateRoles`, `emailSubject`, `emailBlurb`,
  `customFields` and a `status` of `created` or `sent`.
- It takes **no local file and no base64**. A document can only be attached
  by a public HTTPS `remoteUrl`. A PDF on `Z:` therefore cannot be attached by
  the MCP, and publishing client PDFs to a public link is against the org
  rules in `CLAUDE.md`.
- `createEnvelopeFromTemplate` is an agentic tool that takes only an account
  id, runs find → fill → send itself, and has no `status` control. It cannot
  be held at draft, so it is not used.
- The account holds **six** templates, three per region:
  `NSW Build _ Single Buyer`, `NSW Build _ 2 Buyers`, `NSW Build _ Company`,
  `QLD Build _ Single Buyer`, `QLD Build _ 2 Buyer`, `QLD Build _ Company`
  (three of the stored names carry a trailing space, so matching trims
  whitespace at both ends). Each carries a past job's PDFs
  as its documents and that job's people as role defaults, plus that job's
  subject and message. A draft made from a template inherits all of it until
  it is overwritten or replaced.
- Buyer-side role names differ per template: `Buyer 1` + `Buyer 2` (NSW 2
  Buyers), `BUYER 1` + `Buyer 2` (QLD 2 Buyer), `Buyer` (both Single Buyer),
  `Buyer - Company Guarantor` (both Company). The NSW Single Buyer template
  also has a `Buyer Witness` role holding a past job's solicitor.
- Internal roles: `Builder` on every template; `Builder Witness` and a
  sales-admin date role (`Date Contract`, or `Signer 1` on NSW 2 Buyers) on
  the NSW templates.
- **Corrected 13 October 2026:** the templates' tabs are **not anchored**.
  Every tab on all six templates is fixed to a page and an x/y position
  (checked read-only through the sandbox; see
  [What the templates hold](2026-10-13-docusign-upload-mcp.md#what-the-templates-hold-checked-13-october-2026)).
  The `/bs1/\builder_sig`, `/na/` and `/i1/\signer1_sig` strings in the
  filled contracts come from the licensed HIA PDF, and these templates do
  not use them. A job PDF gets the template's tabs in the right place only
  when its page count and layout match the template's placeholder; the
  staff check that every tab sits on its line stays.

## Where it sits

A new **step 8** in `.claude/skills/new-contract-template/SKILL.md`, after
step 7 (report). It runs only when the **build contract routed PRODUCTION in
step 5** (it saved into the job's `CONTRACT DOCUMENTATION`). A
template-testing refresh produces the payload files for inspection but makes
no DocuSign call.

```text
step 5 save  ->  step 7 report (now includes the envelope proposal)
             ->  step 8 docusign_payload.py  ->  getUserInfo / getTemplates /
                 getEnvelopes (read)  ->  createEnvelope status=created
                 [approval prompt on the call is the human yes]
```

## Components

### `job-roles/contract-admin/scripts/docusign_payload.py`

Pure function over the job JSON and the workdir. No network, no DocuSign.

- Input: `--job <workdir>/job.json`, `--workdir`, `--route PRODUCTION|TEST`
  (the build contract's route from step 5), `--server docusign-demo|docusign`.
- Output in the workdir:
  - `docusign_envelope.json`: the exact `envelopeDefinition` to pass to
    `createEnvelope`, with `templateName` (not id) and `status: "created"`.
  - `docusign_payload.txt`: template chosen and why, each recipient with the
    job JSON field it came from, roles left as template defaults, flags, and
    the "staff must do before sending" list.
- Exit non-zero with a one-line reason on any stop condition below, writing
  `docusign_payload.txt` with that reason.

### `.claude/skills/new-contract-template/references/docusign-draft.md`

The MCP procedure, in the style of `references/osc-new-contract.md`: tools in
order, what to check in each response, stop conditions, and what never to
call. Holds the **template map** and **role map** (below) so a template rename
is a doc edit, mirrored in the script's table.

### Skill, rules and docs

- `SKILL.md`: step 8, a few paragraphs pointing at the reference; step 7
  gains the report lines; the Safety rules keep "never issue to DocuSign" and
  gain the sentence that a `created` draft through the gated call is not an
  issue.
- `job-roles/contract-admin/rules/contract-docs.md`: new `CD-10` block,
  DocuSign draft rules (template pick, recipients, subject, custom field,
  status, stop conditions).
- `job-roles/contract-admin/workflows/new-contract.md`: Phase 1 gains the
  step; the HITL section says the draft is created behind the tool prompt and
  sending stays human.
- `job-roles/contract-admin/CLAUDE.md` and root `CLAUDE.md` (HITL section):
  one paragraph each, same wording: draft creation is a gated external write,
  approved per call at the prompt; it is **not** an extension of the
  automatic document-save exception.
- `docs/mcp-servers.md`: the read-only tools moved to `allow`, as that file
  already anticipated.
- `.claude/settings.json`: `mcp__docusign-demo__getUserInfo`,
  `mcp__docusign-demo__getTemplates`, `mcp__docusign-demo__getEnvelopes` to
  `allow`; everything else on the server stays under `ask`.

## Rules

### Template pick (region × buyer type)

| Region (as `hia_probe.py` maps the job folder) | Owners | Company / trust owner | Template name |
|---|---|---|---|
| NSW | 1 | no | `NSW Build _ Single Buyer` |
| NSW | 2 or more | no | `NSW Build _ 2 Buyers` |
| NSW | any | yes | `NSW Build _ Company` |
| QLD | 1 | no | `QLD Build _ Single Buyer` |
| QLD | 2 or more | no | `QLD Build _ 2 Buyer` |
| QLD | any | yes | `QLD Build _ Company` |

Three or more owners → the 2 Buyers template, owners 1 and 2 filled, the rest
flagged, the same as the contract fill (CD-3.8). Company / trust is the same
condition `fill_inclusions.py` uses for CD-3.9 (`company_signatory` present or
the owner entity is a company or trust). The template is resolved **by exact
name after trimming whitespace** through `getTemplates(search_text=...)`;
zero or more than one match stops the step. No template id is stored anywhere, so the map is valid on the
production server too once it is connected.

### Recipients

Only buyer-side roles are set, through `templateRoles`:

| Template | Role names set | Source |
|---|---|---|
| Single Buyer | `Buyer` | owner 1 name; `owner_email` |
| NSW 2 Buyers | `Buyer 1`, `Buyer 2` | owner 1 / owner 2 names; `owner_email`, `owner_2_email` |
| QLD 2 Buyer | `BUYER 1`, `Buyer 2` | same |
| Company | `Buyer - Company Guarantor` | `guarantor_name`; `guarantor_email` (new job JSON key, sourced like the other guarantor fields) |

Names are the purchaser names as they ride on the contract (surname in
capitals, per the fill). `Builder`, `Builder Witness`, `Date Contract`,
`Signer 1` and `Buyer Witness` are **not** passed, so they keep the template
defaults; `Buyer Witness` (NSW Single Buyer) is listed in the report as a role
staff must change or remove before sending, because its default is a past
job's solicitor.

The sender cannot be chosen per envelope: it is always the signed-in DocuSign
account. "Sender" therefore shows only as the sign-off in the message.

### Subject, message, custom field, status

- `emailSubject`: `Complete with DocuSign: BUILD CONTRACT - LOT <lot>, <SUBURB>`
  (the pattern the existing templates use; suburb in capitals per JD rules).
- `emailBlurb`: `Dear <first names joined with " & ">,` blank line, `Please
  find the building contract for review and signing.` blank line, `Thank you`,
  `Sales Admin`. Fixed wording taken from the templates' own messages, run
  through `transpire-writing` once when the reference is written, never
  re-generated per job.
- `customFields.textCustomFields`: `{ name: "JobNo", value: <job_no>, show: "false" }`.
- `status`: always `created`.

### Stop conditions (nothing created, one line in the report)

1. DocuSign server not connected or not signed in (`getUserInfo` fails).
2. Template name matches zero or more than one template.
3. A buyer role has no sourced email, or the Company variant has no sourced
   guarantor name and email.
4. `getEnvelopes` already holds an envelope whose `JobNo` custom field equals
   this job's and whose status is not `voided` or `declined`: the report names
   that envelope id instead.
5. The create call is declined at the prompt: reported as "not created,
   declined", a normal outcome.

The saved documents are never affected by a stop.

### Never

Never `status: sent`; never `updateEnvelope` to send; never a `remoteUrl`;
never set internal roles; never void; never `createEnvelopeFromTemplate`.

## Evidence and report

Workdir files: `docusign_envelope.json`, `docusign_payload.txt`,
`docusign_result.json` (envelope id, status, server name, timestamp, or the
stop reason). In a template-testing run only the first two exist. None of
them go into the job folder on `Z:` (the folder root holds only final files);
in TEST mode they ride to `temp\` with the other working files.

Report lines (step 7): server with **SANDBOX** or **PRODUCTION**, template
chosen, recipients set with sources, roles left as template defaults, and the
staff list before sending: replace the template's placeholder PDFs with the
job's PDFs from the job folder, fix any witness or date role, read the
fields, send.

## Testing

- `job-roles/contract-admin/scripts/test_docusign_payload.py` with synthetic
  job JSONs: all six template picks, three-owner flag, missing-email stop,
  missing-guarantor stop, subject and message text, `JobNo` custom field,
  `status: created`, TEST route produces files and marks "no call".
- One sandbox end-to-end by hand with a synthetic job: confirm the role names
  are accepted, the draft lands as `created`, the custom field is readable
  through `getEnvelopes`; then void the draft in the DocuSign web UI.
- Existing `regress_*` scripts untouched.

## Out of scope

- Getting the PDFs into the envelope automatically (would need a REST client
  with base64 upload, or a time-limited share link; both parked). Since done
  by the `docusign-upload` server, a REST client with base64 upload.
- Production DocuSign (`docs/mcp-servers.md` has the promotion steps).
- Envelope tracking, reminders, voiding.
- Replacing the sample PDFs inside the DocuSign templates with blank
  placeholders (recommended; a DocuSign admin job).

## Decisions

| Question | Answer | Why |
|---|---|---|
| How does the PDF reach the envelope? | Draft from template; staff swap the PDFs in the DocuSign UI | MCP takes no local file; public links expose PII |
| Which template? | Region × buyer type from the job JSON | Six templates exist, not two; the fillers already know owner count and company flag |
| Which recipients? | Buyers from the job; internal roles untouched | Internal people are template defaults, no staff emails in the repo |
| When, and what gate? | After a PRODUCTION save; the approval prompt on `createEnvelope` is the yes | One prompt per real contract, none for test refreshes |
| Implementation | Payload script + Claude transports through MCP | Deterministic, testable; same pattern as the OSC intake |
