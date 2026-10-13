# MCP servers (org-wide)

Register of MCP servers connected to Claude Code for Transpire. Scope is per
server (see the table): `docusign-demo` is at **user scope** (all projects, per
Windows account), while `osc-api-prod` is at **project scope** via the committed
[`.mcp.json`](../.mcp.json), so every session started in this repo gets it, for
**every job-role**, with nothing to redo per account. A role never installs its
own copy of a server.

The org guardrails in [CLAUDE.md](../CLAUDE.md) apply. In particular: no new MCP
server without approval, and no credentials in the repo.

| Server | Scope | Environment | State |
|---|---|---|---|
| `docusign-demo` | User (all projects) | DocuSign **developer sandbox** | Installed, needs sign-in |
| `osc-api-prod` | Project (`.mcp.json` in repo root) | Companion Systems OSC API — **production** (since 13 Oct 2026) | Loads in every session started in this repo; needs the per-checkout venv + `production.env` (see below). Every write is prepared, confirmed by the person in plain words, re-checked and read back |
| ~~`osc-api`~~ | — | OSC API — dev copy frozen 21 Aug 2026 | **Retired 13 Oct 2026.** Writes through it never reached staff. Its tool names are denied in `.claude/settings.json` |

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

The new-contract workflow uses this MCP for issue #34's OSC steps and fields.
See the [execution reference](../.claude/skills/new-contract-template/references/osc-new-contract.md).
DataBuild is excluded.

### Production since 13 October 2026

The connection is the **production** OnSite Companion, the system staff use
(Transpire owner's approval, 13 Oct 2026; issues #34 and #46).

Until then the only registration was `osc-api`, which pointed at the "OSC API -
Dev" install. Its database is a copy of production frozen on 21 Aug 2026.
Writes switched on 24 Sep 2026 (PR #44) landed in that copy and were read back
from it, so they looked verified while staff saw nothing (job 26032,
8 Oct 2026). `osc-api` is retired: it is gone from `.mcp.json`, its tool names
are on `deny` in `.claude/settings.json`, and the server no longer reads the
old `.env`. A per-checkout `.env` left behind is inert and can be deleted.

### What it is

A **local (stdio) MCP server** — Python, in-repo at
[`shared/mcp/osc-api/`](../shared/mcp/osc-api/) — bridging Claude Code to the
Companion Systems **OSC API** (OSCAPI). Unlike DocuSign (a remote HTTP server we
only register), this one is **our code**, so it lives in the repo and is
installed from there.

```
Server name   osc-api-prod   (production OnSite Companion)
Transport     stdio (local Python process)
Code          shared/mcp/osc-api/  (osc_mcp package; the write gate is osc_mcp/gate.py)
Auth          OAuth client-credentials -> Bearer token (RFC6750/7617)
Config        OSC_* settings in the git-ignored production.env; nothing in the repo
```

### Tools

- `osc_token_info` *(read)* — environment, granted scope, write switch, and a
  live-data check (`live_check`: the newest job's date; over 30 days old means
  a stale copy, and no write goes ahead).
- `osc_list_endpoints`, `osc_describe_endpoint` *(read)* — the OpenAPI spec.
- `osc_get` *(read)* — GET any endpoint; OData query params and body-filter GETs.
- `osc_prepare_write` *(read)* — checks a change and words its confirmation;
  sends nothing.
- `osc_cancel_write` *(read)* — discards a prepared change.
- `osc_confirm_write` *(write)* — the only tool that changes OSC.

### Human-in-the-loop: the write gate

Writing changes the system of record staff work from, so every change passes
these checks, enforced in code (`osc_mcp/gate.py`), not just in the skills:

1. **Approved changes only.** The 14 contract-intake changes of issue #34
   (create or update client, person, client and job contact links, job;
   complete an activity; answer an activity question; job or activity message).
   Anything else, including every DELETE and every endpoint that emails or
   re-templates, is refused. Widening the list is a reviewed code change.
2. **Tied to the job.** Each change names the job it is for (`job_id`), and the
   gate checks the record belongs to it: the job itself, its client, a contact
   on it, or one of its activities. A missing, unknown or ambiguous target
   (no match, or more than one) is refused.
3. **Protected fields.** Contract price (DataBuild only), contract number
   (OSC generates it), region of an existing job, and the DataBuild client code
   are refused. So are field names the record does not have.
4. **Only real changes are sent.** The gate reads the current record, drops
   values OSC already holds, and sends only the changed fields. Custom fields
   go as the job's full set with the changes merged in, so none is dropped
   whether OSC merges or replaces that list. (Checked on the 8 Oct 2026 writes:
   PATCH keeps fields left out and clears a field sent as null.)
5. **Plain-language confirmation.** The person sees the job, each change as
   *now X, will be Y* (overwrites and clears spelled out), when a client or
   person is shared with other jobs, and duplicate warnings, and replies.
6. **Explicit yes, re-checked.** `osc_confirm_write` needs the confirmation
   code and the person's reply: a plain yes sends, "no" cancels, anything else
   sends nothing. The gate reads OSC again first; if the record or the request
   differs from what was confirmed, nothing is sent and a new confirmation
   comes back. A code works once, is replaced by a newer check of the same
   target, and expires after 30 minutes.
7. **Host approval.** `mcp__osc-api-prod__osc_confirm_write` is on `ask` in
   [`.claude/settings.json`](../.claude/settings.json), so the person also
   approves the call itself.
8. **Read-back.** After sending, the record is read again: `verified` only when
   every confirmed field took and nothing else on the record changed.
9. **Master switch.** `OSC_ENABLE_WRITES` in the `env` block of `.mcp.json`
   (beats `production.env`). It changes only by PR and takes effect in the next
   session opened in the repo folder; the server is started per session, so
   nothing is ever "restarted". `osc_token_info` reports
   `enable_writes_source`. With the switch off, `osc_prepare_write` still shows
   the confirmation, but no code is issued.

Message attachments add a tenth: a file is read only from a directory listed in
`OSC_UPLOAD_ROOTS` (default the checkout's git-ignored `runtime\` folder), and
only when the change is sent.

### Credentials

The production OAuth **client id / secret** come from Companion Systems and
belong in the company password store. They go into
`shared/mcp/osc-api/production.env` on the server checkout (git-ignored;
Claude is blocked from reading or editing `*.env` files), never into the repo,
a commit, a log, an issue, or a chat. The host names (`OSC_BASE_URL`,
`OSC_SWAGGER_URL`) live there too, per the guardrail against committing
server names. The tools show a short hash of the base URL (`target`), never
the host.

### Install / register (Windows server, `pwsh`, project scope)

Registration is **committed**: [`.mcp.json`](../.mcp.json) at the repo root
registers `osc-api-prod` at project scope with `OSC_ENVIRONMENT=production`,
and `enabledMcpjsonServers` in
[`.claude/settings.json`](../.claude/settings.json) pre-approves it, so there
is no `claude mcp add` to run and nothing to redo per Windows account.

What the committed registration does **not** carry is per-checkout state. Each
checkout needs, under `shared/mcp/osc-api/`:

1. `production.env`, created by a person with
   [`new-production-env.ps1`](../shared/mcp/osc-api/new-production-env.ps1)
   (it asks for the values, the secret typed hidden, fills
   [`production.env.example`](../shared/mcp/osc-api/production.env.example)
   and runs the read-only self-test); the values come from the company
   password store; and
2. the venv the committed command points at:

```powershell
Set-Location "Z:\CLAUDE CODE\transpire-claude-code\shared\mcp\osc-api"
python -m venv .venv        # or `uv venv` where uv is installed
.\.venv\Scripts\python.exe -m pip install -e .
```

The production API refuses any request without an `api-version` header
(HTTP 400, found 13 Oct 2026; the dev install never asked for one). The client
sends `OSC_API_VERSION`, default `7.3`, on every call.

`.mcp.json` sets three env vars: `OSC_ENVIRONMENT=production` (the only
environment the server accepts), `OSC_TIMEOUT=120` (the API's first response
after idling can exceed 30 seconds), and `OSC_ENABLE_WRITES=true`, the write
switch above.

Note: the `mcp` Python SDK is pinned to `<2` in `pyproject.toml` — mcp 2.x
negotiates the 2026-07-28 MCP protocol, which the Claude Code CLI rejects at
the initialize handshake (`-32022`), and the server then never connects.

Verify a checkout with the read-only check, which sends no write:

```powershell
.\.venv\Scripts\python.exe -m osc_mcp.selftest <contract number>
```

It prints the environment, granted scope, the live-data check, the lookups the
intake depends on and, given a contract number, that job's identity. One
display quirk: `claude mcp list` shows the server as *Pending approval* until
the account has accepted the one-time workspace trust dialog (first
interactive `claude` run in the repo); sessions still load it through the
settings pre-approval. Already-open sessions pick the server up on restart,
not live.

### Client data

Everything the server returns is live client data (names, addresses, contact
details). Treat it under the org guardrails: fine to show the user, never in
the repo, on `C:`, or in Dropbox. Keep the credential out of shared logs: the
server keeps HTTP request logging at warning level so the host does not appear
in the MCP log.

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
3. Pick the scope deliberately: commit it to [`.mcp.json`](../.mcp.json)
   (project scope) when it should travel with this repo for every account,
   like `osc-api-prod`; `--scope user` when it must also be available outside this
   repo (per-account, like `docusign-demo`); `--scope local` only for a
   personal experiment.
4. Put the secret in an environment variable at install time, never in the JSON that
   goes into a doc or a commit.
5. Add it to the table at the top of this file, with an `ask` rule if it can cause an
   external or irreversible action.
