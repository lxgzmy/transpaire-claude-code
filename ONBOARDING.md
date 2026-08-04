# Onboarding

A short orientation for anyone working in this repo (human or Claude).

## 1. Read the guardrails first

- **[CLAUDE.md](CLAUDE.md)** — org-wide rules: paths, `Z:` runtime, HITL, security.
  These apply to every job-role and override defaults.
- Then the `CLAUDE.md` inside the job-role you are working on.

## 2. Understand the two homes

| | Repo (this folder) | Server runtime |
|---|---|---|
| Location | Dev clone (macOS/Dropbox) + server checkout | `Z:\CLAUDE CODE\transpire-claude-code\runtime\<role>\` |
| Contains | code, skills, rules, docs — **no client data** | state, evidence, outputs, logs, reports — **client data lives here only** |
| Git | tracked & pushed | git-ignored, never pushed |

## 3. How the repo is organised

- `job-roles/<role>/` — one isolated role. Start with `contract-admin`.
- `shared/` — assets used by more than one role (`skills/`, `schemas/`, `conventions/`).
- `docs/` — org-wide architecture and decisions.

## 4. Working rules

- Read-only and draft-only until a change is explicitly approved.
- Never put PII, credentials, or server names in the repo, prompts, or logs.
- Propose new skills before creating them.
- On the server, script with PowerShell 7 (`pwsh`).

## 5. Add a new job-role

Copy the `job-roles/contract-admin/` folder shape (its `CLAUDE.md`, `workflows/`,
`rules/`, `skills/`, `reference/`, `templates/`, `fixtures/`, `docs/`), give it its
own `CLAUDE.md`, and add a row to the job-roles table in [README.md](README.md).
See [docs/architecture-overview.md](docs/architecture-overview.md).
