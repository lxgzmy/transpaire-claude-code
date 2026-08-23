# MCP servers (org-wide)

Register of MCP servers connected to Claude Code for Transpire. Servers listed here
are installed at **user scope**, so they are available in every project and to
**every job-role** — a role does not install its own copy.

The org guardrails in [CLAUDE.md](../CLAUDE.md) apply. In particular: no new MCP
server without approval, and no credentials in the repo.

| Server | Scope | Environment | State |
|---|---|---|---|
| `docusign-demo` | User (all projects) | DocuSign **developer sandbox** | Installed, needs sign-in |

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
