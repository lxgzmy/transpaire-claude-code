# skills/

Contract-Admin job-role skills are authored here (skill definition + any
PowerShell 7 / Python scripts). **Propose before creating.**

To be loadable by Claude Code, an activated skill is registered under
`.claude/skills/` (prefix the name with the role, e.g. `ca-zdrive`).

Built:

- **`ca-new-job`** (registered in `.claude/skills/ca-new-job/`) — invoke as
  `/ca-new-job <email-file-path>`. Orchestrates the new-job intake workflow
  (`../workflows/new-job.md` Phase 1): reads the request email, runs
  `../scripts/extract_eoi.py`, resolves postcode/council flags with web-lookup
  evidence, presents draft sheets for approval, dry-runs
  `../scripts/osc_entry.py`, drafts the DataBuild email via
  `transpaire-writing`, writes the evidence bundle. Draft-only: never writes
  to OSC, never sends email. Supersedes the planned `ca-email-intake` for the
  new-job case (variation-request intake still to come).

Planned:

- **`ca-zdrive`** — read-only `Z:` search + save-location adviser + duplicate/stale
  report. Reads `Z:\PROJECTS`; writes only under the role's `runtime/…/reports/`.
  Runs as the requesting user so NTFS permissions are honoured. Never moves files.
- **`ca-email-intake`** — variation-request flavour of intake (EOI/new-job is
  covered by `ca-new-job`). Blocked on the variation manual transcription.

Each skill, when proposed, is documented with: purpose, users, inputs, outputs,
systems/folders accessed, permissions, read/write behaviour, evidence/audit,
failure handling, security boundary, and maintenance burden.
