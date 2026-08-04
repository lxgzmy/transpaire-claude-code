# Transpire Claude Code

Transpire's Claude Code project, organised by **job-role** so each role gets its
own instructions, context, skills, and runtime workspace without mixing.

New here? Read **[ONBOARDING.md](ONBOARDING.md)** and the org guardrails in
**[CLAUDE.md](CLAUDE.md)** first.

## How this repo is organised

| Path | What it holds |
|---|---|
| `CLAUDE.md` | Org-wide guardrails (paths, HITL, security). Applies to every role. |
| `docs/` | Org-wide architecture & decisions — see [architecture-overview](docs/architecture-overview.md). |
| `shared/` | Cross-role assets: `skills/`, `schemas/`, `conventions/`. |
| `job-roles/` | One isolated folder per job-role, each with its own `CLAUDE.md`. |

## Job-roles

| Job-role | Status | Entry point |
|---|---|---|
| Contract Administration | POC — read-only / draft-only first | [job-roles/contract-admin/](job-roles/contract-admin/README.md) |

More roles are added as new `job-roles/<role>/` folders. Business records on `Z:`
are organised by job / document-type / stage (not by role); roles are a
**permission overlay**, not a folder axis.

## Runtime (server only)

On Windows Server 2022 the repo is checked out at
`Z:\CLAUDE CODE\transpire-claude-code`. Client / runtime data lives only in that
checkout's git-ignored `runtime\<role>\…` folders. **PowerShell 7 (`pwsh`)** is the
server scripting engine. Never on `C:`, never in Dropbox, never committed.
