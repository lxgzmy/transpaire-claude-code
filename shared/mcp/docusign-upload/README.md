# docusign-upload MCP server

A local (stdio) MCP server that creates a DocuSign **draft** envelope from one
of the six company templates with the job's own PDFs in it. It never sends:
staff check the draft, tag anything the report flags and send it in DocuSign.
Design and decisions: [`docs/superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md`](../../../docs/superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md).

This is code only. Ids, the key path and the environment come from
`DOCUSIGN_*` variables (see [`.env.example`](.env.example)); nothing that
identifies an account or a server is in the repo.

## Tools

| Tool | Kind | Permission | What it does |
|---|---|---|---|
| `docusign_token_info` | read | `allow` | Environment (SANDBOX or PRODUCTION), account, user, token expiry, write switch |
| `docusign_draft_preview` | read | `allow` | Every check the create runs; returns the plan, creates nothing |
| `docusign_create_draft` | write | `ask` | The same checks, one draft with status `created`, then a read-back |

Both preview and create take `template_name`, `recipients` (buyer roles:
`role`, `name`, `email`), `email_subject`, `email_blurb`, `job_no` and
`documents` (`kind`, `path`), taken unchanged from `draftArgs` in the
`docusign_envelope.json` that
`job-roles/contract-admin/scripts/docusign_payload.py` writes. Step 8 of
`/new-contract-template` calls this server (`docusign-upload-prod` for a real
job, this sandbox server for a synthetic one; CD-11).

## How the draft is built

One composite per job document. A document **carries** the template's tabs
when the template has a document of that kind with the same page count;
otherwise it goes in with no tabs and the report **flags** it for staff to tag.
The build contract must carry, or the run stops. Template documents with no
job file are left out, so no past job's PDF reaches the draft. Every template
tab is fixed to a page position, which is why page counts decide.

## Gates

1. `DOCUSIGN_ENABLE_WRITES` is off by default; the committed `.mcp.json` sets it.
2. `docusign_create_draft` is on `ask` in `.claude/settings.json`: every call prompts.
3. The status is a constant in `draft.py`, and `client.py` has no call that could
   send, void, correct or delete an envelope.

With `DOCUSIGN_ENVIRONMENT=demo` the server reads documents only from this
checkout's `runtime\docusign-sandbox` folder: the sandbox gets synthetic jobs
only. The rest of `runtime` is refused, because contract runs keep real jobs'
working files there.

## Install (Windows server, `pwsh`)

```powershell
Set-Location "Z:\CLAUDE CODE\transpire-claude-code\shared\mcp\docusign-upload"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# .env beside this README: copy .env.example and fill it in (values from the
# DocuSign admin; the key file stays on Z: outside the checkout)
.\.venv\Scripts\python.exe -m docusign_upload.selftest
```

Then open a new Claude Code session in the repo folder and run
`docusign_token_info`. The admin prerequisites (integration key, RSA public
key, consent) are listed in the design document.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Synthetic data only, no network, no credentials.
