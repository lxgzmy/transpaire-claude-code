# MCP servers (org-wide)

Register of MCP servers connected to Claude Code for Transpire. Servers listed here
are installed at **user scope**, so they are available in every project and to
**every job-role** — a role does not install its own copy.

The org guardrails in [CLAUDE.md](../CLAUDE.md) apply. In particular: no new MCP
server without approval, and no credentials in the repo.

| Server | Scope | Environment | State |
|---|---|---|---|
| `docusign-demo` | User (all projects) | DocuSign **developer sandbox** | Installed, needs sign-in |
| `osc-api` | User (all projects) | Companion Systems OSC API — **dev** | Built + tested, not yet registered |

## Prerequisite — the `claude` CLI on PATH

The CLI bundled with Claude Desktop lives in a **version-pinned** folder whose real
location is inside the Desktop app's MSIX package:

```
%LOCALAPPDATA%\Packages\Claude_<suffix>\LocalCache\Roaming\Claude\claude-code\<version>\claude.exe
```

Processes running **inside** the app container (anything Claude Desktop spawns) see
the same files projected at `%APPDATA%\Claude\claude-code\<version>\` — a normal
PowerShell does **not**, which is a trap when debugging: two shells can disagree
about whether the folder exists, and both are right for their own view. Launchers
must scan **both** roots.

The version folder also changes on every auto-update, so putting either folder on
PATH directly breaks at the next update. Instead `%USERPROFILE%\.local\bin` is on
the user PATH and holds two launchers that resolve the newest installed version
across both roots at run time:

- `claude.cmd` — PowerShell and `cmd`
- `claude` — Git Bash

A PATH change only reaches **newly launched** processes, and a new terminal opened
from an app that is already running inherits that app's stale environment, so
"just open a new tab" is not reliable. To avoid the problem entirely, a two-line
forwarder also sits at
`%LOCALAPPDATA%\Microsoft\WindowsApps\claude.cmd` and calls the launcher above.
That folder is a long-standing default PATH entry, so `claude` resolves in terminals
that were already open. All version-resolution logic stays in `.local\bin`; the
forwarder holds none of it.

Check with `claude --version`. If a shell still cannot find it, refresh PATH in place
rather than restarting:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
```

### If Claude Desktop is reinstalled

`WindowsApps` is managed by Windows and its contents can be reset by a Store or
Windows update. If `claude` stops resolving in open terminals but
`%USERPROFILE%\.local\bin\claude.cmd --version` still works, the forwarder was
removed; recreate it. New terminals keep working from the PATH entry regardless.

## DocuSign

### What is connected

```
Server name   docusign-demo
Transport     http
URL           https://mcp-d.docusign.com/mcp     (developer sandbox / demo)
Auth          OAuth — client id + client secret, callback port 8080
Scope         user config, available in all projects
```

`mcp-d.docusign.com` is the **sandbox**. Production is `https://mcp.docusign.com/mcp`
and is deliberately **not** connected yet — see [Promoting to production](#promoting-to-production).
The `-demo` suffix in the server name is there so nobody mistakes one for the other
in a tool call.

### Credentials

The client id and client secret come from the DocuSign eSignature Admin app and are
held in the company password store. They are **not in this repo and must never be**.

The secret is passed to the CLI through the `MCP_CLIENT_SECRET` environment variable
at install time and is then stored by Claude Code in
`%USERPROFILE%\.claude\.credentials.json` (verified: it does **not** land in
`.claude.json`). Treat that file as a credential store.

### Install / reinstall

Run once per Windows user account. Substitute the real values; do not paste them
into a document, a commit, or a chat prompt.

```powershell
$env:MCP_CLIENT_SECRET = '<client-secret>'
claude mcp add-json docusign-demo '{"type":"http","url":"https://mcp-d.docusign.com/mcp","oauth":{"clientId":"<client-id>","callbackPort":8080}}' --client-secret --scope user
$env:MCP_CLIENT_SECRET = $null
```

`--scope user` is the part that makes it org-wide. Without it the CLI defaults to
`local`, which binds the server to one project folder only.

### Signing in

Registering the server is not the same as authorising it. Until someone signs in,
the status reads `Needs authentication` and no DocuSign tool can be called.

1. Start an **interactive** session: `claude`
2. Run `/mcp`, select `docusign-demo`, and complete the browser sign-in.

The OAuth callback is `http://localhost:8080`, so sign in from a session on the
machine that has the browser — port 8080 must be free and must match the redirect
URI registered on the DocuSign app.

Verify:

```powershell
claude mcp get docusign-demo
```

### Human-in-the-loop

DocuSign actions are external, legally significant, and mostly irreversible once an
envelope goes out. The org HITL rule ("human approval before external email,
signature, or legal / financial change") is enforced in
[`.claude/settings.json`](../.claude/settings.json):

```json
"ask": ["mcp__docusign-demo"]
```

Every DocuSign tool call therefore prompts for approval, including read-only ones.
That is the intended starting posture. Once the tool list has been enumerated after
first sign-in, the genuinely read-only tools (envelope status, template list) can be
moved to `allow` and the sending and voiding tools left on `ask`. Do not widen this
before that list is confirmed — the tool names are not documented publicly and are
not guessed here.

On top of the prompt, the role rules still apply: Claude drafts the envelope, the
recipients, and the document set as an **evidence bundle** for review. A person
approves before anything is sent for signature.

### How job-roles use it

Roles do not configure anything. The server is present in every session, so a role
workflow just references it.

- **Contract Administration** — signature requests for variation authorities and
  contract correspondence. See
  [`job-roles/contract-admin/CLAUDE.md`](../job-roles/contract-admin/CLAUDE.md).
  DocuSign is listed there as a role system; the connection details stay here so
  the next role inherits them rather than re-documenting them.
- **Future roles** — add a line above rather than installing a second server.

Client and job data produced around a DocuSign run (drafts, evidence, logs) belongs
in the git-ignored `runtime\<role>\` folders on `Z:`, as with any other workflow.

### Promoting to production

Not done yet, and it is a deliberate decision rather than a config tweak. When the
sandbox workflow has been reviewed:

1. Register a second server, `docusign`, pointing at `https://mcp.docusign.com/mcp`
   with the production client id and secret.
2. Add `mcp__docusign` to `ask` **before** first use.
3. Keep `docusign-demo` installed for testing, and keep the names distinct so a
   workflow cannot send a real envelope while someone thinks they are testing.

## OSC API (Companion Systems)

### What it is

A **local (stdio) MCP server** — Python, in-repo at
[`shared/mcp/osc-api/`](../shared/mcp/osc-api/) — bridging Claude Code to the
Companion Systems **OSC API** (OSCAPI). Unlike DocuSign (a remote HTTP server we
only register), this one is **our code**, so it lives in the repo and is
installed from there. It is the read/write counterpart to the manual OSC work in
Contract Admin, and the intended integration point now that DataBuild is ruled
out (see the table below).

```
Server name   osc-api            (dev)   /  osc-api-prod (production, later)
Transport     stdio (local Python process)
Code          shared/mcp/osc-api/  (osc_mcp package)
Auth          OAuth client-credentials -> Bearer token (RFC6750/7617)
Config        OSC_* environment variables only — no creds in the repo
```

### Tools

Five generic, spec-driven tools cover all 148 OSCAPI endpoints (the OpenAPI spec
is loaded at run time, so no per-endpoint code to maintain across versions):

- `osc_token_info` *(read)* — granted scope + token expiry; use to check access.
- `osc_list_endpoints` *(read)* — list endpoints, filter by substring/method.
- `osc_describe_endpoint` *(read)* — params/body/responses for one path.
- `osc_get` *(read)* — GET any endpoint; supports OData query params and the
  body-filter GETs (e.g. `/api/Jobs`).
- `osc_write` *(write — gated)* — POST/PUT/PATCH/DELETE.

### Human-in-the-loop

Reading OSC is safe; writing changes a system of record, which the org rules do
not allow without human sign-off. `osc_write` is gated three independent ways:

1. **Off by default** — refuses unless the server is started with
   `OSC_ENABLE_WRITES=true`; returns a preview and sends nothing otherwise.
2. **Approved per call** — `mcp__osc-api__osc_write` (and the future
   `mcp__osc-api-prod__osc_write`) are on `ask` in
   [`.claude/settings.json`](../.claude/settings.json), so every write prompts
   with the exact request shown.
3. **Explicit confirm** — the tool needs `confirm=true`; without it, it returns a
   dry-run preview.

The read-only tools are on `allow` so queries run without a prompt.

### Credentials

The OAuth **client id / secret** are issued per environment by Companion Systems
and belong in the company password store. They are passed to the server through
`OSC_CLIENT_ID` / `OSC_CLIENT_SECRET` at registration time and are **never** in
the repo, a commit, a log, or a prompt. Server host names live only in the env
too (`OSC_BASE_URL`, `OSC_SWAGGER_URL`) — not in the repo — per the guardrail
against committing server names.

### Install / register (Windows server, `pwsh`, user scope)

Full steps are in [`shared/mcp/osc-api/README.md`](../shared/mcp/osc-api/README.md).
In short: `uv venv` + `uv pip install -e .` inside the package, then
`claude mcp add osc-api --scope user --env OSC_...=... -- <venv-python> -m osc_mcp.server`.
Verify with `claude mcp get osc-api` and `osc_token_info` in a session.

Before registering, confirm configuration with the host-free check:
`python -m osc_mcp.selftest` (read-only; uses the same `OSC_*` env).

### Note on the dev environment

The nominal *dev* instance serves **real production client data** (real names,
ABNs, contact details) and its host resolves to a **public IP** with the API port
open. Treat its output as live client data under the org guardrails, and keep the
credential out of shared logs. Flag the public exposure to the integration owner.

### Promoting to production

Register a **second** server, `osc-api-prod`, with the prod `OSC_BASE_URL`, prod
credentials, prod `OSC_SWAGGER_URL`, and `OSC_VERIFY_TLS=true`. Keep the names
distinct so a workflow cannot hit prod while someone believes they are on dev.
Leave `OSC_ENABLE_WRITES=false` until a write workflow has been reviewed, and the
`mcp__osc-api-prod__osc_write` `ask` rule is already in place.

## Evaluated — cannot be connected

Systems investigated for an MCP server where the answer was no. Recorded here so
the work is not redone.

| System | Outcome |
|---|---|
| DataBuild (estimating / job-costing) | **No API access — vendor-confirmed 23 Aug 2026.** No MCP server or any other integration can be built against it; the once-planned MCP-over-SQL route (Microsoft Data API Builder) died with that confirmation and was removed from the docs. DataBuild stays a manual system (a person keys its figures — contract-admin rules CD-5.4, JD-6) and is retiring in favour of Estimator Companion. Background: [contract-admin docs/01](../job-roles/contract-admin/docs/01-solution-architecture.md). |

## Adding another shared MCP server

1. Propose it first (org guardrail: no MCP server, skill, or software without
   approval).
2. Prefer read-only access before any write access.
3. Install with `--scope user` if more than one role needs it; `--scope local` only
   for a genuinely project-specific server.
4. Put the secret in an environment variable at install time, never in the JSON that
   goes into a doc or a commit.
5. Add it to the table at the top of this file, with an `ask` rule if it can cause an
   external or irreversible action.
