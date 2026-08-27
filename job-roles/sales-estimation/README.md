# Sales Estimation (job-role)

Sales estimating for Transpire: pricing new builds and variations, plus property
and development research. Start with [CLAUDE.md](CLAUDE.md) for role context (the
org guardrails in the repo-root `CLAUDE.md` also apply).

**Phase: discovery complete (27 August 2026), nothing built.** The role was
scoped from the Sales Estimating Manager's completed AI Integration Interview
questionnaire and the consultation meeting of 27 August 2026 (recording pending
transcript). Seven use cases are proposed and await the manager's confirmation;
no rules are transcribed and no workflows or skills exist yet.

## What discovery found (short version)

- Work arrives by email: job pricing requests, variation requests, queries.
- The three biggest time sinks: researching lots (30 minutes to 3 hours each),
  pricing variations, and writing variations.
- Variations are the biggest gap: fully manual, no system, no register outside
  the job folders.
- The manager already runs his own Claude assistant (about six months): land
  contract review no longer misses critical notes. This role builds on that,
  moving it into shared, reviewed skills.
- Boundaries: site costs and Bluebeam markups stay manual.

Full record: [docs/01-discovery-summary.md](docs/01-discovery-summary.md).

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, status, proposed scope, systems, HITL. |
| `docs/` | The discovery summary (below). Solution design will follow once priorities are confirmed. |
| `workflows/` | Proposed workflow specs. All seven are **proposed, not built**. |
| `reference/` | Pointers to the source materials on `Z:` (never the materials themselves). |
| `rules/` | Not created yet. Transcribed, testable business rules will land here before any skill is authored. |
| `skills/` | Not created yet. Role skills are proposed before they are built (org rule). |

## Documentation

| Doc | Contents |
|---|---|
| [docs/01-discovery-summary.md](docs/01-discovery-summary.md) | Discovery record: role and workflows as they run today, systems, pain points, prioritised AI use cases, open questions and next steps. |

## Source materials

The completed questionnaire and the meeting recording contain staff and client
detail, so they are **not** stored in this repo. They live on `Z:` and are
pointed to from [reference/](reference/README.md). The business copy of the
discovery summary (Markdown + PDF) sits beside them.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\sales-estimation\` (git-ignored) —
see the org [CLAUDE.md](../../CLAUDE.md).
