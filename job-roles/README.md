# job-roles/

One subfolder per **job-role**. Each role is fully isolated: its own `CLAUDE.md`,
`rules/`, `skills/`, `workflows/`, `reference/`, `templates/`, `fixtures/`, and
`docs/`. Roles do **not** share instruction context — the org guardrails in the
repo-root `CLAUDE.md` are the only thing that applies across all of them.

| Job-role | Status |
|---|---|
| [contract-admin](contract-admin/README.md) | POC — read-only / draft-only first |

## Adding a role

Copy the `contract-admin/` folder shape, write a role `CLAUDE.md`, and add a row
above. See [../docs/architecture-overview.md](../docs/architecture-overview.md).
