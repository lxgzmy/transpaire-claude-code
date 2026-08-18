# workflows/

One spec per workflow. Each spec states: **trigger, inputs, decision points, the
deterministic steps, HITL gates, outputs, and the rules it relies on.**

Built:

1. [`new-contract.md`](new-contract.md) — build contract request → filled
   inclusions + preliminary agreement (docx + PDF export) + build contract data
   sheet. Rules in `../rules/contract-docs.md`. Skill: `/new-contract-template`.

Retired: `new-job.md` (EOI intake → OSC job setup, skill `/ca-new-job`) was
removed 18 Aug 2026 in favour of `/new-contract-template`; its `JD-*` rules in
`../rules/job-details.md` remain because `new-contract.md` relies on them.

Planned:

- `variation-stage-1.md` — assist raising a Stage 1 variation. Blocked on
  transcribing `../rules/variation-rules.md` from the variation manual.

> The planned `z-drive-adviser.md` workflow was **retired on 4 Aug 2026**: `Z:`
> help is company-wide, not role-specific, so it became the org-level
> [`z-drive-ops`](../../../.claude/skills/z-drive-ops/SKILL.md) skill. See
> [`../skills/README.md`](../skills/README.md) for why. The retired draft is in
> git history at commit `a02c789`.

Stubs are added here as each workflow is designed with the business.
