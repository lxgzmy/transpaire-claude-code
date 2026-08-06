# CLAUDE.md — Contract Administration (job-role)

Scoped context for the Contract Administration job-role. The org-wide guardrails in
the repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Builder-side contract administration for Transpire (Australian residential home
builder). Claude assists by reading requests, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only first.

## Scope

1. **New Job Creation** (built, draft-only). EOI intake → job setup. Rules
   transcribed from the OSC new-job manual (`rules/job-details.md`); workflow
   spec `workflows/new-job.md`; intake skill `/ca-new-job`.
2. **Variation Stage 1** (not started). Blocked on transcribing the variation
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
- `reference/` — pointers to the source manuals (kept on `Z:`, never in the repo).

> `rules/job-details.md` is **transcribed** (pending business review);
> `rules/variation-rules.md` is still a **stub**. Do not author skills against
> guessed rules.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\{state,evidence,outputs,logs,reports}\`
— git-ignored. Naming / CAPS conventions from the manuals are enforced in outputs.

## Human-in-the-loop

Every externally visible artefact (job summary, variation document, alert, email,
DocuSign) is produced as a **draft with an evidence bundle** for review. Nothing is
sent to a client/owner or written to a system of record without explicit approval.
