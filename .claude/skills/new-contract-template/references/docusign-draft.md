# DocuSign draft within the new contract workflow (step 8)

Use this reference after step 7's report, and only when
`docusign_payload.txt` says `CALL: yes` (the build contract routed PRODUCTION
in step 5). The envelope is a **draft** (`status: created`) that the local
`docusign-upload` server builds from the company template with the **job's
own PDFs** in it. Sending, voiding, the witness and date roles, and the tabs on
any document the draft report flags are a person's acts in the DocuSign web UI.

## Which server

| Job folder | Server | Report label |
|---|---|---|
| A real job's `CONTRACT DOCUMENTATION` | `docusign-upload-prod` | PRODUCTION |
| A synthetic job under the checkout's `runtime\docusign-sandbox\` | `docusign-upload` | SANDBOX: no legal effect |

The payload script picks it from the job folder and writes it to `server`.
Call that server's tools and no other. The sandbox server reads documents only
from `runtime\docusign-sandbox\`, so a real job's PDFs never reach it, and a
synthetic job never goes to production. `docusign-upload-prod` is registered
at production Go-Live (`docs/mcp-servers.md`); until then a real run ends at
stop 1 with no draft, and the report says so. What happens beyond that stop is
an open decision (CD-10.8).

**The approval prompt on `docusign_create_draft` is the human yes.** Do not ask
a second time in chat; do not proceed past a decline. `docusign_token_info`
and `docusign_draft_preview` are read-only and on `allow`.

## 1. Build the payload

```
python job-roles/contract-admin/scripts/docusign_payload.py --job <workdir>/job.json --job-dir "<job's CONTRACT DOCUMENTATION>"
```

A sandbox job's folder is not under `Z:\PROJECTS`, so add `--region NSW|QLD`.

Exit 2 = stop 3; put its `REASON:` line in the report and finish.
`CALL: no` = a template-testing refresh; mention the payload files and finish.
Otherwise read `docusign_envelope.json`: `server`, `templateName`,
`draftArgs`, `sources`, `defaultRoles`, `documentsMissing` and
`staffBeforeSending`.

`draftArgs` holds exactly the six tool arguments (`template_name`,
`recipients`, `email_subject`, `email_blurb`, `job_no`, `documents`). Pass it
unchanged to both calls below, so the preview and the create see the same
draft. There is no status argument: `created` is fixed in the server.

## 2. Connection (read-only)

`docusign_token_info` on the payload's server. If the server's tools are not in
this session, or the call returns `ok: false`, that is stop 1. The
`environment` it returns must be PRODUCTION for `docusign-upload-prod` and
SANDBOX for `docusign-upload`; anything else is stop 2.

## 3. Preview (read-only)

`docusign_draft_preview` with `draftArgs`. It runs every check the create
runs: the template by exact trimmed name, the template's documents by kind,
the buyer roles against the template's signer roles, each PDF (inside the
server's upload roots, a real PDF, page count readable, 25 MB at most), the
build contract's page count against the template's, the request size, and any
envelope from the last 180 days that already carries this `JobNo`.

`ok: false` with `stop: true` is stop 4. `ok: true` returns the `plan`: per
document, `carried from the template` or `none, flagged: <reason>`, and the
template documents left out because the job has no file of that kind.

## 4. Create the draft (gated)

`docusign_create_draft` with the same `draftArgs`. The prompt appears here; a
decline is stop 5 (a normal outcome). `ok: false` is stop 6.

On success the result holds `envelopeId`, `status` (`created`),
`environment`, the `plan`, and the read-back: `documents` (per kind: tabs
carried or flagged, tab count, pages per role), `roles_without_tabs`,
`findings` and a `check` line. If it carries `read_back: failed (...)`
instead, the draft still exists: report the id and add "Check the draft in
DocuSign before sending" to the staff list.

## 5. Record and report

Write `<workdir>/docusign_result.json`:

```json
{"server": "docusign-upload-prod", "environment": "PRODUCTION",
 "envelopeId": "...", "status": "created", "templateName": "...",
 "jobNo": "...", "created": "<ISO timestamp>", "documents": [],
 "rolesWithoutTabs": [], "findings": [], "stop": null}
```

`docusign_result.json` is written on every path that reaches section 2,
success or stop. On a stop, the same file with `envelopeId: null` and
`stop: "<reason>"`. For `CALL: no` and for a payload exit 2 it is written
with `envelopeId: null` and the reason.

Report lines (added to the step 7 table):

- the server and its environment, PRODUCTION or SANDBOX (a SANDBOX draft has
  no legal effect; say so);
- the template, the recipients set with their sources (`sources`), and the
  roles left as template defaults (`defaultRoles`);
- per document: carried, or flagged with its reason; the kinds in
  `documentsMissing` that the template has a place for;
- the envelope id, and the read-back `check` line with any `findings`
  verbatim;
- headed "Before sending, in DocuSign:", the `staffBeforeSending` list
  verbatim, then one line per flagged document (for example "PLANS: 5 pages,
  the template's has 4. No tabs: place them before sending.") and one line
  per read-back finding.

When no draft was created (a stop, a decline, or `CALL: no`), say
"No DocuSign draft was created" with the reason and finish, as for any stop.
What the step does beyond that (a hand-made envelope from the payload, or
another route) is the owner's open decision, CD-10.8: build nothing for it
until the owner decides.

## Stops

Every stop is listed once here. Report the reason in the step 7 table, write
`docusign_result.json` with `stop`, and finish.

1. The payload's server is not connected: its tools are not in this session,
   or `docusign_token_info` returns `ok: false` (not configured, consent not
   granted, token refused). Report its error. For `docusign-upload-prod`
   before Go-Live: "production DocuSign upload is not connected yet; no draft
   created".
2. The server's environment does not fit the job: SANDBOX for a real job, or
   PRODUCTION for a sandbox job.
3. The payload script exits 2: report its `REASON:` line.
4. The preview stops: report its error verbatim. A duplicate names the
   existing envelope's id and status; report it as the existing draft.
5. The create call was declined at the prompt: "not created, declined".
6. The create call returns `ok: false`: report `error`, `errorCode` and
   `message` verbatim. Never retry, never edit the arguments to make it pass,
   never call another tool to work around it. When the error says the outcome
   is uncertain, run `docusign_draft_preview` once with the same arguments: a
   duplicate stop means the draft exists (report its id); anything else is
   reported as "no draft found; nothing more was tried".

## Never

Any `docusign-demo` write in this step (`createEnvelope` put the template's
placeholder PDFs in the draft and is no longer part of it; whether it comes
back as a fallback is the open CD-10.8 decision);
`createEnvelopeFromTemplate` (it sends and cannot be held at draft); a real
job's documents on the sandbox server, or a synthetic job's on production;
changing `draftArgs` between the preview and the create; a document that is
not in the payload's `documents`; setting Builder, Builder Witness, Date
Contract, Signer 1 or Buyer Witness; voiding or deleting; a second create for
the same job in one run.
