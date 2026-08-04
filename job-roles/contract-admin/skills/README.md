# skills/

Contract-Admin job-role skills are authored here (skill definition + any
PowerShell 7 / Python scripts). **Propose before creating.**

To be loadable by Claude Code, an activated skill is registered under
`.claude/skills/` (prefix the name with the role, e.g. `ca-new-job`).

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

- **`ca-email-intake`** — variation-request flavour of intake (EOI/new-job is
  covered by `ca-new-job`). Blocked on the variation manual transcription.

## Not a Contract-Admin skill: `Z:` drive work

`ca-zdrive` was **retired before being built** (4 Aug 2026). `Z:` help — finding
files, advising where to save something, duplicate/clutter reports — is needed by
every department, not just Contract Admin, and the share is department-shaped
above `PROJECTS`. Scoping it to one role would have meant either a role-shaped
view of company-wide records (which the
[architecture](../../../docs/architecture-overview.md) rules out — roles are a
permission overlay, not a folder axis) or a near-duplicate skill per role.

It is now the **org-level [`z-drive-ops`](../../../.claude/skills/z-drive-ops/SKILL.md)**
skill, covering the whole share and usable from Claude Code *and* Claude Desktop.
See [docs/z_drive_claude_setup.md](../../../docs/z_drive_claude_setup.md).

Contract-Admin-specific `Z:` rules stay here: `JD-10` in
[`../rules/job-details.md`](../rules/job-details.md) (job folder naming, the
`LOT MASTER FOLDER` copy, duplicate protection) and
[`../scripts/new_job_folders.ps1`](../scripts/new_job_folders.ps1).

Each skill, when proposed, is documented with: purpose, users, inputs, outputs,
systems/folders accessed, permissions, read/write behaviour, evidence/audit,
failure handling, security boundary, and maintenance burden.
