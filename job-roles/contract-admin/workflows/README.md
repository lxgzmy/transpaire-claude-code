# workflows/

One spec per workflow. Each spec states: **trigger, inputs, decision points, the
deterministic steps, HITL gates, outputs, and the rules it relies on.**

Planned (in order):

1. `z-drive-adviser.md` — read-only: search, identify latest/authoritative version,
   advise save folder + filename, report duplicates/stale/misfiled. No writes.
2. `variation-stage-1.md` — assist raising a Stage 1 variation (see `../rules/variation-rules.md`).
3. [`new-job.md`](new-job.md) — EOI intake → job setup. **Drafted** from the OSC
   new-job manual (rules in `../rules/job-details.md`); pending business review.

Stubs are added here as each workflow is designed with the business.
