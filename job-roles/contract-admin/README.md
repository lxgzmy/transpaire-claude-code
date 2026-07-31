# Contract Administration (job-role)

Builder-side contract administration for Transpire. Start with
[CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the repo-root
`CLAUDE.md` also apply).

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow (Z-drive adviser → variation stage 1 → new job). |
| `rules/` | Transcribed, testable business rules (currently stubs). |
| `skills/` | Role-only skills, authored here (none built yet). |
| `reference/` | Pointers to source manuals (never the manuals themselves). |
| `templates/` | Sanitised prompt / document / output templates. |
| `fixtures/` | Synthetic test data only. |
| `docs/` | Operational docs & solution design (01–03 architecture set). |

## Current status

Read-only / draft-only POC. First deliverable is the **Z-drive adviser** (read-only
search + save-location advice + duplicate/stale reporting). OSC/DataBuild
write-automation is deferred pending the technical session with Adam.
