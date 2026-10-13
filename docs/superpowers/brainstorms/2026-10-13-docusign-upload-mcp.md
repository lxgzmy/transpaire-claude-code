# DocuSign draft with the job's own PDFs: the `docusign-upload` MCP server

Design, 13 October 2026. Agreed section by section with the Contract-Admin
owner in a brainstorming session. The answers that shaped it are recorded in
[Decisions](#decisions) so they are not re-argued later.

## Goal

When a job's documents are final, a DocuSign **draft** envelope is created from
the right company template with the job's own PDFs in it, the buyers filled in,
and the template's tabs on every document whose layout matches the template.
Staff open the draft, tag any document the report flags, check it and send.
Nothing in this design can send, sign, void or delete an envelope.

This builds on PR #49
([`2026-10-13-docusign-draft-envelope.md`](2026-10-13-docusign-draft-envelope.md)).
Its draft carries the template's placeholder PDFs, because the hosted
`docusign-demo` MCP accepts documents only by public URL. This server is
local, reads the PDFs itself and sends them base64-encoded through the
eSignature REST API.

## What the templates hold (checked 13 October 2026)

Read-only checks on the sandbox account through `docusign-demo`: the template
list with documents and recipients, and each template's tab detail. No
personal data from the templates is recorded here.

**No anchor tabs.** Every tab on all six templates is fixed to a page and an
x/y position: 60 to 145 tabs per template, none anchored. PR #49's spec says
the tabs are anchored; they are not. The `/bs1/\builder_sig`, `/na/` and
`/i1/\signer1_sig` codes in the filled contracts come from the licensed HIA
PDF, and these templates do not use them.

Pages of each placeholder document:

| Template | Build contract | Inclusions | Preliminary agreement | Plans |
|---|---|---|---|---|
| `NSW Build _ Single Buyer` | 45 | 16 | 3 | 3 |
| `NSW Build _ 2 Buyers` | 45 | 16 | 3 | 12 |
| `NSW Build _ Company` | 45 | 18 | 3 | 5 |
| `QLD Build _ Single Buyer` | 37 | 15 | none | 4 |
| `QLD Build _ 2 Buyer` | 37 | 16 | none | 4 |
| `QLD Build _ Company` | 37 | 16 | none | 5 |

Document ids are not 1 to n on every template (some are eight-digit ids), and
NSW Single Buyer's preliminary agreement is named
`EXECUTED-PRELIMINARY AGREEMENT...`, so document kinds are matched by name.

The tab pattern is the same on all six templates:

- Build contract: buyer initials on the body pages and signatures on fixed
  pages (NSW pages 12 and 35, plus 15 on Company; QLD pages 3 and 13, plus 16
  on Company). The builder signs on NSW page 12 or QLD page 13; NSW also has
  the witness block on page 12, a date text field on page 4 and checkboxes on
  page 35.
- Inclusions: buyer initials on every page except the last three, signature
  and date on the last three, builder signature and date on the third-last.
- Preliminary agreement (NSW only): buyers sign each of the three pages; the
  builder and the date field are on page 3.
- Plans: a buyer signature on every page.

So a job PDF with the same page count and layout as the placeholder gets
correct tabs when it replaces it. The contract (45 or 37 pages) and the
preliminary agreement (3 pages) are fixed forms. Inclusions (15 to 18 pages)
and plans (3 to 12 pages) vary from job to job.

## DocuSign behaviour this relies on

- **Composite templates.** Each composite contributes exactly one document. A
  document given at composite level supersedes the server template's
  documents in that composite. A replacement takes the `documentId` of the
  template document it replaces, so that document's tabs land on it (the fix
  DocuSign's community gives for tabs landing on the wrong document; the
  prototype confirms it).
- **Custom fields.** With composites, envelope custom fields belong in the
  inline template. Root-level custom fields are ignored.
- **Roles on a draft.** A draft built from several composites needs
  `merge_roles_on_draft=true` on Envelopes:create so each role appears once
  (the prototype confirms it).
- **Size.** The request body is capped at about 34 MiB, and base64 adds about
  a third to each PDF.
- **JWT Grant.** An RS256 assertion (`iss` the integration key, `sub` the
  user id, `aud` `account-d.docusign.com` or `account.docusign.com`, scope
  `signature impersonation`) is exchanged at `/oauth/token`, and
  `/oauth/userinfo` gives the account's base URI. Each user consents once.
- **What a key can do.** A JWT key acts as the impersonated user with all of
  that user's rights, sending included. "Draft only" is a property of this
  server's code, not of the credential, so the key is guarded like a password
  (see [Key custody](#key-custody)).
- **Sandbox plan.** The restricted developer plan rejected a five-recipient
  envelope with `RECIPIENT_LIMIT_EXCEEDED` on 13 October 2026, so sandbox
  tests use a two-recipient template.

## Where it sits

```text
docusign_payload.py (PR #49, plus a documents list)  ->  docusign_envelope.json
    Claude passes its values as arguments to:
docusign_draft_preview   read-only, allow  -> the plan: template, roles, documents,
                                              carry or flag, duplicates, stops
docusign_create_draft    write, ask        -> the same checks again, one POST
                                              (status created), then a read-back
    Claude writes docusign_result.json and the report lines (PR #49's format)
```

While the server points at the sandbox it takes synthetic jobs only (see
[Sandbox data rule](#sandbox-data-rule)), so step 8 of `/new-contract-template`
is not changed by this design. Real runs keep PR #49's placeholder draft until
production DocuSign is connected; a later PR then switches step 8 to
`docusign_create_draft`.

## Components

### `shared/mcp/docusign-upload/` (package `docusign_upload`)

Laid out like `shared/mcp/osc-api/`. The server never imports contract-admin
code: the role rules stay in the payload script, so `shared/` does not depend
on a job-role.

| Module | Job |
|---|---|
| `config.py` | Reads `DOCUSIGN_*` variables (and a git-ignored `.env`), validates them, reports where the write switch came from |
| `auth.py` | Builds and signs the JWT assertion, exchanges it for a token, reads userinfo, caches the token until shortly before expiry |
| `client.py` | The only HTTP calls the server can make (list below); nothing else exists in the code |
| `pdfcheck.py` | Upload-root, file-type, size and page-count checks |
| `draft.py` | Plain functions: match template documents to kinds, decide carry or flag, build the request, summarise the read-back |
| `server.py` | The three tools |
| `selftest.py` | Read-only connectivity check from the command line |
| `tests/` | Unit tests, no network and no credentials |

`client.py` knows exactly these calls:

- `POST /oauth/token` and `GET /oauth/userinfo` on the auth server;
- `GET .../templates` (list with documents and recipients) and
  `GET .../templates/{id}/recipients?include_tabs=true` (the template's tab
  pages, which the read-back compares against);
- `GET .../envelopes` (list, for the duplicate check);
- `POST .../envelopes?merge_roles_on_draft=true`, which refuses any body whose
  `status` is not `created`;
- `GET .../envelopes/{id}` and its `/documents`, `/recipients?include_tabs=true`
  and `/custom_fields`, for the read-back.

There is no PUT, no DELETE, and no tool that takes a raw request.

Dependencies (approved with this design): `mcp>=1.2,<2` and `httpx`, as
osc-api; `PyJWT[crypto]` for RS256 signing (it brings in `cryptography`);
`pypdf` for page counts.

### Tools

| Tool | Kind | Permission | What it does |
|---|---|---|---|
| `docusign_token_info` | read | `allow` | Environment (SANDBOX or PRODUCTION), account and user names, token expiry, write switch and its source, number of upload roots |
| `docusign_draft_preview` | read | `allow` | Runs every check the create runs and returns the plan; creates nothing |
| `docusign_create_draft` | write | `ask` | Runs the checks again, creates the draft, reads it back |

The preview and the create take the same arguments:

- `template_name`: the exact template name from the payload;
- `recipients`: a list of `{role, name, email}`, buyer-side roles only;
- `email_subject` and `email_blurb`;
- `job_no`: written to the `JobNo` custom field and used for the duplicate check;
- `documents`: a list of `{kind, path}`, where `kind` is `BUILD CONTRACT`,
  `INCLUSIONS`, `PRELIMINARY AGREEMENT` or `PLANS`.

They are explicit arguments rather than a path to the JSON, so the approval
prompt shows exactly what will be created. The preview replaces osc-api's
`confirm=false` step, which keeps PR #49's one prompt per draft.

Three gates: `DOCUSIGN_ENABLE_WRITES` is off by default (as osc-api's
switch); the create tool is on `ask`; and `status` is a constant in the code,
never an argument.

### Changes outside the package

- `job-roles/contract-admin/scripts/docusign_payload.py`: adds a `documents`
  list to `docusign_envelope.json` and the `.txt` report. Each entry is the
  CD-7.2 file `<KIND>_<suffix>.pdf` in the job's `CONTRACT DOCUMENTATION`
  folder, where that file exists. The build contract is required, as today.
  Plans are included only when a file with exactly that name exists; the
  script never guesses at another file. `test_docusign_payload.py` gains the
  matching cases.
- `.mcp.json`: a project-scope `docusign-upload` entry (the server's Windows
  venv, as osc-api) with `DOCUSIGN_ENVIRONMENT=demo` and
  `DOCUSIGN_ENABLE_WRITES=true` in its `env` block, so both change only by PR.
- `.claude/settings.json`: `docusign-upload` in `enabledMcpjsonServers`; the
  token and preview tools on `allow`; `docusign_create_draft` on `ask`, plus
  an `ask` entry ready for a future `docusign-upload-prod`. Never a
  server-wide `ask` entry, which would beat the `allow` entries.
- `.gitignore`: `*.pem` and `*.key` as a backstop.
- `docs/mcp-servers.md`: a row in the register and a section for the server.
- Root `CLAUDE.md`: one sentence in the DocuSign gated-write paragraph naming
  the new create tool, sandbox only until production.

## Building the draft

### Carry or flag

For each job document, in the order contract, inclusions, preliminary
agreement, plans:

- **Carry** when the template has a document of that kind and the page counts
  match. The template's tabs for that document land on the job's file.
- **Flag** when the template has no document of that kind or the page count
  differs. The document goes into the draft with no tabs, and the report says
  so, for example "PLANS: 5 pages, template has 4. No tabs; tag before
  sending."

The build contract must carry. If its page count is not the template's (45 for
NSW, 37 for QLD), the run stops instead of flagging: a different count means
the fill changed the layout, and the internal roles and template settings
reach the draft through the carried composites.

Template documents with no job file are left out, so no past job's PDF reaches
the draft.

### The request

One `POST .../envelopes?merge_roles_on_draft=true`:

```json
{
  "status": "created",
  "emailSubject": "<from the payload>",
  "emailBlurb": "<from the payload>",
  "compositeTemplates": [
    {
      "compositeTemplateId": "1",
      "serverTemplates": [{"sequence": "1", "templateId": "<resolved by name>"}],
      "inlineTemplates": [{
        "sequence": "2",
        "recipients": {"signers": [
          {"recipientId": "<template's id for the role>", "roleName": "Buyer",
           "routingOrder": "<template's>", "name": "<payload>", "email": "<payload>"}
        ]},
        "customFields": {"textCustomFields": [
          {"name": "JobNo", "value": "<job_no>", "show": "false", "required": "false"}
        ]}
      }],
      "document": {"documentId": "<template's BUILD CONTRACT id>",
                   "name": "<job file name>", "fileExtension": "pdf",
                   "documentBase64": "<job PDF>"}
    },
    {
      "compositeTemplateId": "2",
      "inlineTemplates": [{"sequence": "1", "recipients": {"signers": ["<same buyers>"]}}],
      "document": {"documentId": "<id no template document uses>",
                   "name": "<flagged job file>", "fileExtension": "pdf",
                   "documentBase64": "<job PDF>"}
    }
  ]
}
```

A carried document repeats the first composite's shape with its own template
document id (only the first composite carries `JobNo`). A flagged document
uses the second shape: no server template, so no tabs. Each buyer role takes
the template's own recipient id and routing order, and must be a signer role
on the template; role names match case-sensitively, as DocuSign does. Builder,
Builder Witness, Date Contract, Signer 1 and Buyer Witness are never sent, so
they keep the template defaults, as in PR #49.

### Stops

The preview and the create run the same list. Nothing is created on any stop.

1. Not configured, consent not granted (the message includes the consent URL),
   or the token request refused.
2. The configured account is not one of the user's accounts.
3. The template name, trimmed, matches zero templates or more than one.
4. A template document whose name matches no known kind (the template has
   changed and a person needs to look).
5. A recipient role not on the template or not a signer, a role given twice,
   or a malformed email.
6. A document path that is not absolute or lies outside the upload roots; a
   file that is not a regular `.pdf` starting with `%PDF-`; a page count that
   cannot be read (including password-protected files); a file over 25 MB; a
   kind given twice; no build contract.
7. The build contract's page count differs from the template's.
8. The estimated request body is over 30 MiB.
9. An envelope from the last 180 days already has this `JobNo` and is not
   voided, declined or deleted. The stop names its id and status.
10. DocuSign returns an error on the create call. It is reported verbatim,
    never retried, and the request is never edited to make it pass. A
    transport failure reports the outcome as uncertain: run the preview, which
    repeats the duplicate check, before trying again.

### Read-back

After a successful create, the tool reads the draft back and reports. These
are findings, not stops: the draft exists and a person decides what to do with
it. Nothing is deleted automatically.

- the status is `created`;
- the draft's documents are the job's files, matched by name (DocuSign may
  renumber ids);
- each carried document has the same tab count per role and page as the
  template document it replaced, and each flagged document has none;
- `JobNo` is present and the buyer emails are as sent;
- any role left with no tab at all is listed.

The tool returns the envelope id, status, documents, tab counts per document
by role and page, and the flags. Claude writes them to
`docusign_result.json` in the workdir and adds them to the step 7 report.

## Config and secrets

### Environment variables

Read from the environment, or from a git-ignored `.env` beside the package (or
the file `DOCUSIGN_ENV_FILE` names). A real environment variable always beats
the `.env`, as in osc-api.

| Variable | Required | Purpose |
|---|---|---|
| `DOCUSIGN_ENVIRONMENT` | yes | `demo` or `production`; no default. Sets the auth server and labels every result SANDBOX or PRODUCTION |
| `DOCUSIGN_INTEGRATION_KEY` | yes | The integration key |
| `DOCUSIGN_USER_ID` | yes | The template owner's user id (the impersonated user) |
| `DOCUSIGN_ACCOUNT_ID` | yes | The API account id; must appear in that user's userinfo |
| `DOCUSIGN_PRIVATE_KEY_PATH` | yes | Absolute path to the private key; refused inside the checkout or on `C:` |
| `DOCUSIGN_UPLOAD_ROOTS` | production only | `;`-separated folders documents may be read from, e.g. `Z:\PROJECTS` |
| `DOCUSIGN_ENABLE_WRITES` | no | Write switch, default `false`; set in `.mcp.json` |
| `DOCUSIGN_CONSENT_REDIRECT_URI` | no | Used to print the consent URL in stop 1 |
| `DOCUSIGN_TIMEOUT` | no | Seconds per request, default 60 |

The `.env` holds ids, the environment and the key path. It never holds key
material.

### Sandbox data rule

With `DOCUSIGN_ENVIRONMENT=demo` the upload root is always the checkout's
`runtime\` folder, and any other entry in `DOCUSIGN_UPLOAD_ROOTS` is a config
error. The sandbox only ever receives synthetic jobs; real job folders under
`Z:\PROJECTS` are read only by a production server. This follows the org rule
of synthetic samples first and no real client data in prototypes.

### Key custody

- The key pair is generated locally with openssl (RSA 2048). Only the public
  key goes to DocuSign, through **Upload RSA**. If that screen offers only
  Generate RSA, the private key it shows goes straight into the key file and
  never into chat, email, a document or a ticket.
- The key file lives on `Z:` outside the checkout, in a folder only the
  accounts that run Claude Code can read. It is named `*.pem`, so the existing
  `Z:` deny rules in `.claude/settings.json` keep Claude's own file tools off
  it; the server process still reads it.
- Never on `C:`, never in Dropbox, never in a prompt, log or commit. The
  server never returns or logs key material.
- Rotation: upload a new public key, swap the file, delete the old pair in
  DocuSign (an integration key holds at most five).
- On the macOS dev clone, for the sandbox prototype only, the `.env` and the
  key sit in the home folder outside the repo, reached through
  `DOCUSIGN_ENV_FILE`.

## Prerequisites for the DocuSign admin

### Sandbox (now)

1. In the sandbox account's **Apps and Keys**, add an integration key, for
   example "Transpire contract drafts".
2. Turn on Authorization Code Grant and add one https redirect URI. The browser
   only lands there after the consent step; nothing runs at that address.
3. Under Service Integration, **Upload RSA** with the public key generated for
   this server.
4. Note three values for the `.env` on the server, never the repo: the
   integration key, the template owner's API Username (user id) and the API
   Account ID.
5. The template owner signs in to the sandbox once, opens
   `https://account-d.docusign.com/oauth/auth?response_type=code&scope=signature%20impersonation&client_id=<integration key>&redirect_uri=<redirect URI>`
   and clicks Accept.

### Production (later, a separate decision)

DocuSign runs a Go-Live review of the integration key's sandbox API calls
before promoting it. Production then needs its own key pair, redirect URI and
consent at `account.docusign.com`, the production user and account ids, a
second server `docusign-upload-prod` (`DOCUSIGN_ENVIRONMENT=production`,
`DOCUSIGN_UPLOAD_ROOTS=Z:\PROJECTS`), and the PR that switches step 8 and
rewrites CD-10.5 and the staff list.

## Testing

### Unit tests

`python -m unittest discover -s tests -v` in the package, with
`httpx.MockTransport`, no network and no credentials. Synthetic PDFs are
written by the tests.

- Config: key-path rules (relative, inside the checkout, on `C:`), demo
  locked to `runtime\`, production roots required, missing variables, the
  write switch and its source.
- Auth: the assertion's claims and RS256 signature checked against a
  throwaway key pair made in the test; `consent_required` returns the consent
  URL; the token is reused until shortly before expiry.
- Client: no PUT or DELETE path exists; the create call refuses any status
  other than `created`.
- Draft: kind matching (including `EXECUTED-...` names and eight-digit ids),
  carry or flag by page count, the contract-must-carry stop, and the request
  shape (sequences, document ids, the merge flag, `JobNo` in the inline
  template, no internal roles).
- Server: preview and create run the same checks; the switch off refuses the
  create; size and duplicate stops; DocuSign errors returned verbatim.
- `test_docusign_payload.py`: the `documents` list follows CD-7.2 names, the
  build contract stays required, plans appear only under the exact name.

### Sandbox prototype

After the implementation plan is approved and the admin prerequisites are
done:

1. A synthetic `QLD Build _ Single Buyer` job in `runtime\`: the buyer at an
   `@example.com` address, and the template's own builder, which makes two
   recipients. Its synthetic PDFs are a 37-page contract (carries), 15-page
   inclusions (carries) and 5-page plans (the template's has 4, so they are
   flagged).
2. `docusign_token_info`, then the preview, then the create, approved per
   call.
3. The read-back must show status `created`; the three job files; the
   template's tab count per role and page on the contract and inclusions, and
   none on the plans; two recipients, not duplicates; `JobNo`, subject and
   message as sent.
4. A second preview must stop on the duplicate, which proves the `JobNo` check
   sees drafts.
5. A person deletes the draft in the DocuSign web UI.

This proves the mechanics, which replaces "anchor tabs landed" in the original
brief: the templates have no anchor tabs, so the check is that carried tabs
sit on the expected pages. Blank stand-in pages cannot show that a tab sits on
the real signature line. That check needs a synthetic job filled from the real
templates on the server (Word and `Z:`), and it is listed below as a check
before production. If the restricted plan rejects even two recipients, the
prototype needs an unrestricted sandbox account, which a person sets up.

## Rollout

- Branch `docusign-upload-mcp`, stacked on PR #49 (its PR targets
  `docusign-integration`, because it extends `docusign_payload.py`), and
  retargeted to `main` once #49 merges. The reviewer merges; the branch is
  never merged by Claude.
- Step 8 and CD-10 stay as they are in this PR.

## Out of scope

- The step 8 switch, production registration and Go-Live (a later PR).
- Re-basing inclusions and plans tabs to the job's page count, using the
  pattern above, once the contract-admin team confirms it holds for every
  inclusions range.
- Anchor tabs in the templates and their Word sources.
- The visual check that carried contract tabs sit on the signature lines of a
  contract filled from the current interim templates (before production).
- Correcting PR #49's spec, which says the template tabs are anchored.
- Sending, reminders, voiding, deleting and correcting envelopes.

## Decisions

| Question | Answer | Why |
|---|---|---|
| How do tabs reach a document whose page count differs from the template's? | Carry or flag: template tabs only where page counts match; anything else goes in untagged and flagged | Every template tab is fixed-position. Safest first version, and it shows how often inclusions and plans differ |
| Whose DocuSign identity creates the drafts? | The user who owns the six templates | Drafts land in the folder staff already use, nothing to share, recipients see the same sender; the key is guarded closely because it can act as that user |
| Which approach? | One compositeTemplates call from a local server | One approval prompt, nothing half-made on failure, no past job's PDF in the draft |
| Preview and approval | Read-only preview on `allow`; the create on `ask` | One prompt per draft, as PR #49 intended |
| Real client PDFs in the sandbox? | No: demo is locked to `runtime\` | Org rule: synthetic samples first, no client data in prototypes |
| Build contract page count differs? | Stop | A fixed form whose layout changed needs a person, and it carries the template's internal roles |
| Does the server import contract-admin code? | No; Claude passes the payload's values as arguments | `shared/` stays role-agnostic, and the prompt shows what will be created |
| Dependencies | `mcp<2`, `httpx`, `PyJWT[crypto]`, `pypdf` | The osc-api pair plus JWT signing and page counts |
| Step 8 now? | No, at production go-live | The sandbox server takes synthetic jobs only |
