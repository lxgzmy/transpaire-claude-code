# CLAUDE.md — Transpire Claude Code (org-wide guardrails)

Auto-loaded project memory. These rules apply to **every job-role** in this repo.
Read before creating files, running scripts, or generating any client-facing artefact.

## What this repo is

Transpire's Claude Code project, organised by **job-role** so that each role (and
later, teams) gets its own instructions, context, skills, and runtime workspace
**without mixing**. The first job-role in scope is **Contract Administration**
(`job-roles/contract-admin/`).

Claude Code is the **orchestrator and judgment layer**: it reads inputs, applies
rules, and produces **drafts for human review**. It does not send, sign, move
business files, or write to any system of record without explicit human approval.

## Repository shape

```
CLAUDE.md                 # this file — org-wide guardrails (no client data, ever)
README.md                 # index of job-roles + how the repo is organised
ONBOARDING.md             # start here if you are new to the repo
docs/                     # org-wide architecture & decisions
shared/                   # cross-role assets: skills/, schemas/, conventions/
job-roles/<role>/         # one isolated folder per job-role (each has its own CLAUDE.md)
```

Each `job-roles/<role>/` is self-contained. A role's instructions, rules, and
skills are scoped to that folder and must not leak into another role.

## Information architecture (important)

- The **repo** is organised by **job-role → workflow**.
- **Business records on `Z:`** are organised by **job/project → document-type →
  workflow-stage**, grouped by **region**, with **lifecycle** as state.
- **Roles are a permission overlay** (NTFS / AD groups), never a folder axis. A
  person's role decides what they may see/do, not where a file lives.

## Environment & path rules (MANDATORY on Windows Server 2022)

- The server scripting engine is **PowerShell 7 (`pwsh`)** — target it, not
  Windows PowerShell 5.1.
- **Never** write project data, generated files, caches, temp files, logs, or
  working files to the **`C:`** drive.
- On the server this repo is checked out at **`Z:\CLAUDE CODE\transpaire-claude-code`**
  — the same name as the git repo, so the server workspace mirrors the repo 1:1.
- **All runtime / client data** lives only in that checkout's **git-ignored**
  working folders: `runtime\<job-role>\{state,evidence,outputs,logs,reports}\`.
  It stays on `Z:`, and is never committed, never pushed, never on `C:`, never in
  Dropbox.
- The **dev clone** (e.g. this macOS Dropbox copy) holds **code, skills, rules,
  and docs only** — never client data. `.gitignore` blocks `runtime/`, `state/`,
  `evidence/`, `outputs/`, `reports/`, `*.log`, `*.job.json`, `*.variation.json`
  as a backstop.
- **Never** place credentials, connection strings, PII, client data, or **server
  names/addresses** in prompts, code, logs, or git. Source manuals contain these —
  reference them, do not copy them in (see each role's `reference/`).
- The `Z:` drive is mapped per RDP session; confirm it is mapped before writing.

## Human-in-the-loop (HITL)

- The review gate sits **between analysis and any change or external action**.
- Claude drafts what it intends to do (with an evidence bundle: sources,
  screenshots, diffs); a human approves; then the action runs.
- Start **read-only and draft-only**. Prefer read-only connectors before any write
  access. Flag low-confidence extractions for human confirmation rather than guessing.

## Security posture

- Sanitised / synthetic samples first; no real client data in prototypes or fixtures.
- Read-only before write; preserve NTFS / share permissions; never bypass access controls.
- Human approval before external email, signature, or legal / financial change.
- Log sources, model output, reviewer decisions, and approved actions.
- Keep the canonical job record independent of any single system (e.g. DataBuild).

## Skills

- **All human- or client-facing writing** must go through the project
  **`transpaire-writing`** skill: house voice (Australian English, register by
  audience, CAPS/naming) + de-AI, matched to the active job-role. It layers on the
  global `humanizer` and `shared/conventions/writing-style.md`.
- **Cross-role skills** are registered in `.claude/skills/`. `humanizer` (the generic
  de-AI engine) is vendored there too (`.claude/skills/humanizer/`) so every checkout
  gets it — see `shared/skills/README.md` for the keep-vs-reference policy.
- **All `Z:` drive work** (finding files, save-location advice, duplicate/clutter
  reports, creating folders) goes through the org-level **`z-drive-ops`** skill —
  it is company-wide, not per-role, and is the one place the drive map and the
  sensitive-folder blocklist are maintained. `windows-fileops` remains the
  PowerShell technique layer underneath it. `z-drive-ops` also runs in **Claude
  Desktop** for non-technical staff: see `docs/z_drive_claude_setup.md`. Keep that
  skill folder self-contained (no `../` references out of it) so it stays
  zip-portable.
- **Job-role skills** are authored under `job-roles/<role>/skills/` and documented
  there. **Propose any new skill before creating it.** First Contract-Admin skill:
  `ca-new-job` (EOI intake, draft-only). Deeper OSC/DataBuild write-automation
  remains blocked on the technical session with Adam.

## Do not

- Do not write runtime / client data into the repo or any Dropbox-synced folder.
- Do not copy source manuals (they contain PII + server names) into the repo.
- Do not install skills, MCP servers, plugins, or software without approval.
- Do not commit secrets, connection strings, server names, or client PII.
- Do not reference the OpenAI Codex `ecc-*` / `au-family-*` skills under
  `~/Documents/nl-codex` — different platform, and the family skills contain
  unrelated personal PII.
