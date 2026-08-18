# CLAUDE.md — Contract Administration (job-role)

Scoped context for the Contract Administration job-role. The org-wide guardrails in
the repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Builder-side contract administration for Transpire (Australian residential home
builder). Claude assists by reading requests, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only first.

## Scope

1. **New Job Creation** (retired 18 Aug 2026). The `/ca-new-job` intake skill,
   its workflow spec and scripts were removed in favour of
   `/new-contract-template`; OSC job entry stays manual pending the technical
   session with Adam. The rules transcribed from the OSC new-job manual
   (`rules/job-details.md`, `JD-*`) remain — the contract-documents workflow
   relies on them.
2. **Contract documents** (built; fills **and saves** with automatic routing —
   issuing and every outward act stays human). Build contract request → filled
   templates, saved in the same pass: first drafts into the job's
   `CONTRACT DOCUMENTATION`, jobs that already exist in production into the
   template-testing folder (CD-7.7, 17 Aug 2026 — no preview stop). Rules from
   the manual's "RAISING CONTRACTS" section plus the blank templates diffed
   against completed jobs (`rules/contract-docs.md`); workflow spec
   `workflows/new-contract.md`; skill `/new-contract-template`. Produces the
   inclusions and preliminary agreement; the build contract PDF is not
   fillable, so that stays a human keying job (CD-5.1) — the held HIA licence
   sets a docx+PDF target for the HIA contract once a fillable Word template
   exists (CD-5.2a; detection automated by `hia_probe.py` on every routed
   save, CD-5.2b).
3. **Variation Stage 1** (not started). Blocked on transcribing the variation
   manual into `rules/variation-rules.md` — do not build against guessed rules.

General `Z:` drive help (finding files, save-location advice, duplicate reports)
is **not** a Contract-Admin deliverable — it is the org-level
[`z-drive-ops`](../../.claude/skills/z-drive-ops/SKILL.md) skill, shared with
every other role. This role keeps only the job-specific `Z:` rules: `JD-10` in
`rules/job-details.md` and `scripts/new_job_folders.ps1`.

Deeper OSC / DataBuild write-automation is deferred until a technical session with
the IT specialist (Adam) confirms the integration surfaces, per the discovery record.

## Systems

OnSite Companion (OSC), DataBuild, the `Z:` share, Microsoft 365 / Outlook (a shared
Contract-Admin mailbox), DocuSign. The **authoritative record varies per field** and
must be confirmed — the canonical job record is not tied to any single system.

DocuSign is reached through the org-wide `docusign-demo` MCP server (sandbox only so
far, sign-in required, every call gated by an approval prompt). Connection details and
the production-promotion steps live in [`docs/mcp-servers.md`](../../docs/mcp-servers.md)
— not restated here, since the server is shared with every other role.

## Rules & knowledge

- `rules/variation-rules.md` — variation type/numbering, workflow & document
  templates, file naming, activities, alert recipients.
- `rules/job-details.md` — new-job address / CAPS / certifier / council / marketer rules.
- `rules/contract-docs.md` — contract template selection, inclusions and
  preliminary agreement fields, build contract data, aux/dual-key handling,
  output naming (`CD-*`).
- `reference/` — pointers to the source manuals (kept on `Z:`, never in the repo).

> `rules/job-details.md` and `rules/contract-docs.md` are **transcribed**
> (pending business review); `rules/variation-rules.md` is still a **stub**. Do
> not author skills against guessed rules. `contract-docs.md` carries an open-
> questions list where the manual and the live drive disagree — worth settling.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\{state,evidence,outputs,logs,reports}\`
— git-ignored. Naming / CAPS conventions from the manuals are enforced in outputs.

## Human-in-the-loop

Every externally visible artefact (job summary, variation document, alert, email,
DocuSign) is produced as a **draft with an evidence bundle** for review. Nothing is
sent to a client/owner or written to a system of record without explicit approval.

**Sanctioned exception (17 Aug 2026):** the `/new-contract-template` save is
automatic — routed by CD-7.7 to the job folder (first drafts, never
overwriting) or the template-testing folder (jobs already in production), with
the full report following the save. Issuing, sending, signing, OSC/DataBuild
writes, and promoting test output into a job folder stay human.
