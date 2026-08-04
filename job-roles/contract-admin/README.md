# Contract Administration (job-role)

Builder-side contract administration for Transpire, on Windows Server 2022. Start
with [CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the repo-root
`CLAUDE.md` also apply).

Proof-of-concept, read-only / draft-only first. Two target workflows:

1. **New Job Creation** — EOI email intake → OnSite Companion (OSC) job creation →
   Z-Drive folder → DataBuild handoff → contact details → plan-arrival updates.
2. **Variation Stage 1** — variation type decision → OSC variation + workflow
   templates → Z-Drive Excel variation → OSC document generation → PDF filing →
   staff alert.

General `Z:` drive help (search, save-location advice, duplicate/clutter
reporting) is **company-wide, not role-specific** — it lives in the org-level
[`z-drive-ops`](../../.claude/skills/z-drive-ops/SKILL.md) skill. This role keeps
only the job-specific `Z:` rules (`JD-10`, `scripts/new_job_folders.ps1`).

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow (new job → variation stage 1). |
| `rules/` | Transcribed, testable business rules (currently stubs). |
| `skills/` | Role-only skills, authored here (none built yet). |
| `reference/` | Pointers to source manuals (never the manuals themselves). |
| `templates/` | Sanitised prompt / document / output templates. |
| `fixtures/` | Synthetic test data only. |
| `docs/` | Operational docs & solution design (below). |

## Documentation

| Doc | Contents |
|---|---|
| [docs/01-solution-architecture.md](docs/01-solution-architecture.md) | Draft solution: architecture, integration tiers per system, workflow design, HITL, rollout, risks. |
| [docs/02-windows-server-setup.md](docs/02-windows-server-setup.md) | Software/config on Windows Server 2022 for the OSC UI-automation skill. |
| [docs/03-automation-flow.md](docs/03-automation-flow.md) | How Claude Code, UI automation, SQL and import routines fit together at runtime. |

> Note: `docs/01–03` predate the read-only-first direction and describe the fuller
> OSC/DataBuild automation. Treat them as forward design; the current scope is the
> read-only, draft-only scope. They will be refreshed as the workflows are built.

## Source manuals

The authoritative manuals (e.g. *Creating a Variation — Stage 1*, the discovery
record, the OSC new-job manual) contain client PII and server names, so they are
**not** stored in this repo. They live on `Z:` and are pointed to from
[reference/](reference/README.md); only de-identified rules are transcribed into
[rules/](rules/README.md).

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\` (git-ignored) — see
the org [CLAUDE.md](../../CLAUDE.md).
