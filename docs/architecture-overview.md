# Architecture overview

How the Transpire Claude Code project is structured, and why.

## Goals

- Support many job-roles (and later teams) without mixing their instructions,
  context, permissions, or skills.
- Keep a stable information architecture as roles are added.
- Preserve Windows permissions, auditability, document history, and human approval.

## Two axes, kept separate

1. **The repo** is organised by **job-role → workflow**. This is *who uses Claude
   for what*. Each role is an isolated folder with its own `CLAUDE.md`.
2. **Business records on `Z:`** are organised by **job / project → document-type →
   workflow-stage**, grouped by **region**, with **lifecycle** as state. This is the
   more stable axis for records and is independent of who touches them.
3. **Roles are a permission overlay** (NTFS / AD groups), applied on top of the `Z:`
   record structure — never a folder axis for records.

## Repository layout

```
CLAUDE.md            # org-wide guardrails
README.md            # index
ONBOARDING.md        # orientation
.claude/
  settings.json      # permissions (deny C:, ask on DocuSign), status line
  skills/            # every activated skill, cross-role and role-scoped alike —
                     #   this is the only place Claude Code loads skills from.
                     #   Docs live with the owner: shared/skills/ or the role.
docs/                # org-wide architecture & decisions (this file)
shared/
  skills/            # cross-role skills (policy for global vs vendored)
  schemas/           # shared JSON schemas (canonical job record, evidence bundle)
  conventions/       # naming/CAPS, region codes, canonical-source matrix
job-roles/
  contract-admin/    # first job-role
    CLAUDE.md        # role context (imports org rules, does not restate them)
    workflows/       # one spec per workflow
    rules/           # transcribed, testable business rules
    skills/          # role-only skills (authored here)
    reference/       # pointers to source manuals (never the manuals themselves)
    templates/       # sanitised prompt/document/output templates
    fixtures/        # synthetic test data only
    docs/            # role operational docs & solution design
  <next-role>/       # same shape, fully isolated
```

## Server runtime

On Windows Server 2022 the repo is checked out at
`Z:\CLAUDE CODE\transpire-claude-code`. All client/runtime data lives only in that
checkout's **git-ignored** working folders:

```
runtime/
  <job-role>/
    state/      # per-job state machine, resumable checkpoints
    evidence/   # screenshots + action logs for review/audit
    outputs/    # generated drafts (Excel/Word/PDF) pending approval
    logs/       # run logs
    reports/    # read-only reports (e.g. Z: inventory, duplicate reports)
```

Scripting on the server uses **PowerShell 7 (`pwsh`)**. Runtime data never lands on
`C:`, never in Dropbox, never in git.

## Adding a job-role

1. Copy the `job-roles/contract-admin/` folder shape.
2. Write a role `CLAUDE.md` that imports the org guardrails and adds role scope,
   systems, rules pointers, and HITL specifics.
3. Register any activated skill under `.claude/skills/` (prefix with the role).
4. Add the role to the table in `README.md`.
