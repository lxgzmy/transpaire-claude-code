# job-roles/

One subfolder per **job-role**. Each role is fully isolated: its own `CLAUDE.md`,
`rules/`, `scripts/`, `skills/`, `workflows/`, `reference/`, `templates/`,
`fixtures/`, and `docs/`. Roles do **not** share instruction context — the org
guardrails in the repo-root `CLAUDE.md` are the only thing that applies across
all of them.

| Job-role | Status |
|---|---|
| [contract-admin](contract-admin/README.md) | Contract-documents workflow built and verified against real jobs: inclusions + prelim + HIA build contract filled and saved with routed destinations (CD-7.7; build contract per CD-5.2b - approved blank or TEST-only staged conversion). New-job intake retired 18 Aug 2026; variations not started |
| [sales-estimation](sales-estimation/README.md) | Discovery complete 27 Aug 2026, all three sources reviewed (questionnaire, meeting transcript, the manager's handed-over rules + lot-research skill). Build order agreed: land assessment first, then variations. Two rule conflicts to settle before rules transcription; nothing built |

## Adding a role

Copy the `contract-admin/` folder shape, write a role `CLAUDE.md`, and add a row
above. See [../docs/architecture-overview.md](../docs/architecture-overview.md).
