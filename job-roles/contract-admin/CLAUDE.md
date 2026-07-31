# CLAUDE.md — Contract Administration (job-role)

Scoped context for the Contract Administration job-role. The org-wide guardrails in
the repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Builder-side contract administration for Transpire (Australian residential home
builder). Claude assists by reading requests, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only first.

## Scope (sequenced)

1. **Z-drive adviser — first, read-only.** Find files, identify the latest /
   authoritative version, advise the correct save folder + filename, and report
   duplicate / stale / misfiled files. No business file is moved or written.
2. **Variation Stage 1.** Assist the variation workflow (see `docs/` +
   `rules/variation-rules.md`).
3. **New Job Creation.** EOI intake → job setup (blocked on the OSC new-job manual).

Deeper OSC / DataBuild write-automation is deferred until a technical session with
the IT specialist (Adam) confirms the integration surfaces, per the discovery record.

## Systems

OnSite Companion (OSC), DataBuild, the `Z:` share, Microsoft 365 / Outlook (a shared
Contract-Admin mailbox), DocuSign. The **authoritative record varies per field** and
must be confirmed — the canonical job record is not tied to any single system.

## Rules & knowledge

- `rules/variation-rules.md` — variation type/numbering, workflow & document
  templates, file naming, activities, alert recipients.
- `rules/job-details.md` — new-job address / CAPS / certifier / council / marketer rules.
- `reference/` — pointers to the source manuals (kept on `Z:`, never in the repo).

> The `rules/` files are **stubs pending transcription from the manuals.** Do not
> author skills against guessed rules.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpaire-claude-code\runtime\contract-admin\{state,evidence,outputs,logs,reports}\`
— git-ignored. Naming / CAPS conventions from the manuals are enforced in outputs.

## Human-in-the-loop

Every externally visible artefact (job summary, variation document, alert, email,
DocuSign) is produced as a **draft with an evidence bundle** for review. Nothing is
sent to a client/owner or written to a system of record without explicit approval.
