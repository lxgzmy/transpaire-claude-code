# shared/schemas/

Shared JSON schemas used by multiple roles and skills. Keep them de-identified —
schemas define shape, never real data.

Planned:

- `job-record.schema.json` — the **canonical job record** (cross-system, not tied to
  any single system such as DataBuild or OSC), with the owning system noted per field.
- `evidence-bundle.schema.json` — the shape of the evidence attached to any draft
  (sources, paths, versions, screenshots, confidence).
