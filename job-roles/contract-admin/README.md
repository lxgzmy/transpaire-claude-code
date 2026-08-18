# Contract Administration (job-role)

Builder-side contract administration for Transpire, on Windows Server 2022. Start
with [CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the repo-root
`CLAUDE.md` also apply).

Proof-of-concept, read-only and draft-first. Three workflows:

1. **New Job Creation** (retired 18 Aug 2026) — the `/ca-new-job` intake skill,
   `workflows/new-job.md` and its scripts were removed in favour of
   `/new-contract-template`; OSC job entry stays manual pending the technical
   session with Adam. The `JD-*` rules remain (used by workflow 2).
2. **Contract documents** (built; fills and saves in one pass) — build contract
   request → filled inclusions + preliminary agreement + HIA build contract
   (`.docx` + PDF export each; the build contract fills whenever a usable Word
   template exists — approved blank → real name, staged UNAPPROVED conversion →
   TEST runs only, otherwise data sheet, CD-5.2b) → saved to the routed
   destination: the job folder for first drafts, the template-testing folder
   when the job already exists in production (CD-7.7, 17 Aug 2026 — no preview
   stop; issuing stays human).
   Verified character-for-character against completed jobs in all three
   template families. Skill: `/new-contract-template`.
3. **Variation Stage 1** (not started) — variation type decision → OSC variation +
   workflow templates → Z-Drive Excel variation → OSC document generation → PDF
   filing → staff alert. Blocked on transcribing `rules/variation-rules.md`.

General `Z:` drive help (search, save-location advice, duplicate/clutter
reporting) is **company-wide, not role-specific** — it lives in the org-level
[`z-drive-ops`](../../.claude/skills/z-drive-ops/SKILL.md) skill. This role keeps
only the job-specific `Z:` rules (`JD-10`, `scripts/new_job_folders.ps1`).

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow. `new-contract.md` built; variation stage 1 to come. |
| `rules/` | Transcribed, testable business rules. `job-details.md` (`JD-*`) and `contract-docs.md` (`CD-*`) transcribed; `variation-rules.md` still a stub. |
| `scripts/` | The workflow pipeline: email → extraction → template fill → PDF export, plus probes, diff tools and the three test suites. See [scripts/README.md](scripts/README.md). |
| `skills/` | Role-only skills, authored and documented here. `new-contract-template` built (registered in `../../.claude/skills/`). |
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
> OSC/DataBuild automation. Treat them as forward design; the current scope is
> read-only and draft-first (the contract-documents save is the one sanctioned
> automation, CD-7.7). They will be refreshed as the workflows are built.

## Source manuals

The authoritative manuals (e.g. *Creating a Variation — Stage 1*, the discovery
record, the OSC new-job manual) contain client PII and server names, so they are
**not** stored in this repo. They live on `Z:` and are pointed to from
[reference/](reference/README.md); only de-identified rules are transcribed into
[rules/](rules/README.md).

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\` (git-ignored) — see
the org [CLAUDE.md](../../CLAUDE.md).
