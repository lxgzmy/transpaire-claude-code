# Transpire Claude Code

Transpire's Claude Code project, organised by **job-role** so each role gets its
own instructions, context, skills, and runtime workspace without mixing.

New here? Read **[ONBOARDING.md](ONBOARDING.md)** and the org guardrails in
**[CLAUDE.md](CLAUDE.md)** first.

## How this repo is organised

| Path | What it holds |
|---|---|
| `CLAUDE.md` | Org-wide guardrails (paths, HITL, security). Applies to every role. |
| `docs/` | Org-wide architecture & decisions — see [architecture-overview](docs/architecture-overview.md) and [mcp-servers](docs/mcp-servers.md) — plus the staff-facing guides (HTML source + PDF) for `z-drive-ops` and `/new-contract-template`, and [z_drive_claude_setup](docs/z_drive_claude_setup.md) for rolling the drive help out to staff. |
| `shared/` | Cross-role assets: `skills/`, `schemas/`, `conventions/`. Cross-role skills are registered in `.claude/skills/` and listed in [shared/skills/README.md](shared/skills/README.md). |
| `job-roles/` | One isolated folder per job-role, each with its own `CLAUDE.md`. |

## Job-roles

| Job-role | Status | Entry point |
|---|---|---|
| Contract Administration | Contract-documents workflow built and verified against real jobs: inclusions + prelim + HIA build contract filled and saved with routed destinations (CD-7.7; build contract per CD-5.2b - approved blank or TEST-only staged conversion). New-job intake retired 18 Aug 2026; variations not started | [job-roles/contract-admin/](job-roles/contract-admin/README.md) |
| Sales Estimation | Discovery complete 27 Aug 2026, all three sources reviewed (questionnaire, meeting transcript, the manager's handed-over rules + lot-research skill). Build order agreed: land assessment first, then variations. Two rule conflicts to settle before rules transcription; nothing built | [job-roles/sales-estimation/](job-roles/sales-estimation/README.md) |
| Permit Officer | Building approvals (QLD certifier portal + NSW email/planning portal), RFI tracking, weekly BA report. Discovery 20 Aug 2026, business-owner review 21 Aug (NSW first); rules + workflow specs transcribed; OSC access gate cleared by the read-only `osc-api` MCP; no skills built yet | [job-roles/permit-officer/](job-roles/permit-officer/README.md) |

More roles are added as new `job-roles/<role>/` folders. Business records on `Z:`
are organised by job / document-type / stage (not by role); roles are a
**permission overlay**, not a folder axis.

## Runtime (server only)

On Windows Server 2022 the repo is checked out at
`Z:\CLAUDE CODE\transpire-claude-code`. Client / runtime data lives only in that
checkout's git-ignored `runtime\<role>\…` folders. **PowerShell 7 (`pwsh`)** is the
server scripting engine. Never on `C:`, never in Dropbox, never committed.
