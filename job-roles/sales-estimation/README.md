# Sales Estimation (job-role)

Sales estimating for Transpire: lot feasibility, pricing new builds and
variations, and the property and development research underneath (land itself is
never priced). Start with [CLAUDE.md](CLAUDE.md) for role context (the org
guardrails in the repo-root `CLAUDE.md` also apply).

**Phase: discovery complete (27 August 2026), nothing built.** The role was
scoped from three sources, all reviewed in full: the Sales Estimating Manager's
completed AI Integration Interview questionnaire, the consultation meeting
transcript (74 minutes), and the six working documents the manager handed over
in `Z:\AI test\Sale Estimating\` (his project instructions, NSW and QLD
estimating rules, a packaged lot-research skill, a link library and his siting
guide). The meeting fixed the build order: **land assessment first, then
variations.** No rules are transcribed yet and no workflows or skills exist in
this repo.

## What discovery found (short version)

- Work arrives by email: job pricing requests, variation requests, queries.
- The three biggest time sinks: researching lots (30 minutes to 3 hours each),
  pricing variations, and writing variations.
- Variations are the biggest structural gap: fully manual, no system, no
  register outside the job folders.
- The manager already runs his own Claude assistant (about six months) and has
  handed over a working rules-plus-skill setup for lot research. The land
  assessment build is therefore transcription and hardening, not invention,
  once two rule conflicts found in review (pricing in reports; the MSDG
  Guideline 7 trigger) are settled with him.
- Boundaries: site costs and Bluebeam markups stay manual; land is never
  priced; every output is a draft for review.

Full record: [docs/01-discovery-summary.md](docs/01-discovery-summary.md)
(version 2), including the materials review in its section 6.

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, status, proposed scope, systems, HITL. |
| `docs/` | The discovery summary (below). Solution design will follow once the rule conflicts are settled and rules are transcribed. |
| `workflows/` | Proposed workflow specs. All six are **proposed, not built**. |
| `reference/` | Pointers to the source materials and the manager's handed-over documents on `Z:` (never the materials themselves). |
| `rules/` | Not created yet. The manager's NSW and QLD knowledge bases get transcribed here (after the conflicts are settled), before any skill is authored. |
| `skills/` | Not created yet. Role skills are proposed before they are built (org rule). |

## Documentation

| Doc | Contents |
|---|---|
| [docs/01-discovery-summary.md](docs/01-discovery-summary.md) | Discovery record, version 2: role and workflows as they run today, systems, pain points, the review of the manager's handed-over materials (with the conflicts it found), prioritised AI use cases, open questions and next steps. |

## Source materials

The questionnaire, meeting recording and transcript live in the cowork sales
folder; the manager's handed-over documents live in `Z:\AI test\Sale Estimating\`.
All contain staff or client detail, so they are **not** stored in this repo —
they are pointed to from [reference/](reference/README.md). The business copy of
the discovery summary (Markdown + PDF, version 2) sits beside the sources.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\sales-estimation\` (git-ignored) —
see the org [CLAUDE.md](../../CLAUDE.md). Holds an unpacked working copy of the
manager's packaged skill under `evidence\nick-materials\`.
