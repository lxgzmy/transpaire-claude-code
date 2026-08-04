# workflows/

One spec per workflow. Each spec states: **trigger, inputs, decision points, the
deterministic steps, HITL gates, outputs, and the rules it relies on.**

Planned (in order):

1. `variation-stage-1.md` — assist raising a Stage 1 variation (see `../rules/variation-rules.md`).
2. [`new-job.md`](new-job.md) — EOI intake → job setup. **Drafted** from the OSC
   new-job manual (rules in `../rules/job-details.md`); pending business review.

> The planned `z-drive-adviser.md` workflow was **retired on 4 Aug 2026**: `Z:`
> help is company-wide, not role-specific, so it became the org-level
> [`z-drive-ops`](../../../.claude/skills/z-drive-ops/SKILL.md) skill. See
> [`../skills/README.md`](../skills/README.md) for why. The retired draft is in
> git history at commit `a02c789`.

Stubs are added here as each workflow is designed with the business.
