# shared/

Assets used by more than one job-role.

| Folder | Purpose |
|---|---|
| `skills/` | Cross-role skills and the policy for global vs vendored skills. |
| `schemas/` | Shared JSON schemas (e.g. the canonical job record, the evidence-bundle shape). |
| `conventions/` | Org-wide conventions: naming/CAPS, region/state codes, and the canonical-source matrix (which system is authoritative for each field). |

Anything specific to a single role belongs under `job-roles/<role>/`, not here.
