# DocuSign draft within the new contract workflow (step 8)

Use this reference after step 7's report, and only when
`docusign_payload.txt` says `CALL: yes` (the build contract routed PRODUCTION
in step 5). The envelope is a **draft** (`status: created`). Sending, document
replacement, witness/date roles and voiding are a person's acts in the DocuSign
web UI. The `docusign-demo` server is the **sandbox**: its envelopes have no
legal effect, and the report must say SANDBOX. A production server, when one is
registered, is named `docusign` (see `docs/mcp-servers.md`).

**The approval prompt on `createEnvelope` is the human yes.** Do not ask a
second time in chat; do not proceed past a decline. Every other call below is
read-only.

## 1. Build the payload

```
python job-roles/contract-admin/scripts/docusign_payload.py --job <workdir>/job.json --job-dir "<job's CONTRACT DOCUMENTATION>"
```

Exit 2 = a stop condition; put its `REASON:` line in the report and finish.
`CALL: no` = a template-testing refresh; mention the payload files and finish.
Otherwise read `docusign_envelope.json`: `templateName`, `envelopeDefinition`.

## 2. Account and template (read-only)

1. `getUserInfo` → `accounts[0].account_id` (the `accountId` for every later
   call) and the `mcpSessionId` to pass along. A failure is stop 1: "DocuSign
   not connected or not signed in - open `/mcp`, select the server, sign in".
2. `getTemplates(accountId, search_text=<templateName>, user_filter="all")`.
   Keep the templates whose `name.strip()` equals `templateName.strip()`.
   Exactly one → its `templateId`. Zero or more than one is stop 2: report
   the names returned and finish.

## 3. Duplicate check (read-only)

`getEnvelopes(accountId, custom_field="JobNo=<job_no>", from_date=<today minus 180 days, YYYY-MM-DD>, count=40)`.
(The tool's own description asks for `getEnvelopeVsAgreementSkill` first; call
it, it only returns guidance.) An envelope whose status is anything other than
`voided` or `declined` is stop 4: report its `envelopeId` and `status` as the
existing draft, and finish. Nothing found → continue.

## 4. Create the draft (gated)

`createEnvelope(accountId, envelopeDefinition=<envelopeDefinition from the
JSON with templateId set>)`. Pass the definition exactly: `status` stays
`created`; do not add `documents`, `remoteUrl`, `compositeTemplates` or any
role not in `templateRoles`. The prompt appears here; a decline is stop 5,
reported as "not created, declined" (a normal outcome).

The response carries `envelopeId`, `status` (`created`) and `uri`.

## 5. Record and report

Write `<workdir>/docusign_result.json`:

```json
{"server": "docusign-demo", "envelopeId": "...", "status": "created",
 "templateId": "...", "templateName": "...", "jobNo": "...",
 "created": "<ISO timestamp>", "stop": null}
```

On a stop, the same file with `envelopeId: null` and `stop: "<reason>"`.

Report lines (added to the step 7 table): server (SANDBOX/PRODUCTION),
template, recipients set with their sources (`sources` from the JSON), roles
left as template defaults (`defaultRoles`), the envelope id, and the
`staffBeforeSending` list verbatim, headed "Before sending, in DocuSign:".
Say plainly that the draft holds the template's placeholder PDFs until staff
replace them.

## Never

`status: sent`; `updateEnvelope` to send or change status; `remoteUrl`
documents; setting Builder, Builder Witness, Date Contract, Signer 1 or Buyer
Witness; voiding; `createEnvelopeFromTemplate` (it sends and cannot be held at
draft); a second create for the same job in one run.
