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

- **`ca-zdrive`** — proposed, not yet built (propose-before-create, per the
  [org ONBOARDING.md](../../../ONBOARDING.md) working rules). Invokes
  [`../workflows/z-drive-adviser.md`](../workflows/z-drive-adviser.md).

  | | |
  |---|---|
  | Purpose | Read-only `Z:` search, save-location advice, duplicate/stale/misfiled reporting |
  | Users | Contract-Admin staff, in chat; other workflows (e.g. `new-job.md`'s duplicate check) |
  | Inputs | A job number, address/lot, region, or document description |
  | Outputs | Chat answers; optional Markdown/CSV report |
  | Systems/folders | `Z:\PROJECTS` only (not the wider `Z:` share) |
  | Permissions | Runs as the requesting user — sees only what they can already see in Explorer |
  | Read/write | Read-only, always. Writes reports only to `runtime\contract-admin\reports\`, never a business file |
  | Evidence/audit | Report includes the search performed and the folders/files inspected |
  | Failure handling | No confident match → say so; do not guess a save location or an "authoritative" version |
  | Security boundary | Never moves, renames, or deletes; never bypasses NTFS/share permissions |
  | Maintenance burden | Tracks the master-folder taxonomy in `z-drive-adviser.md` — needs a review if that template changes |

  Open before building: the staleness threshold and authority tie-breaks noted
  in `z-drive-adviser.md`'s Open questions — business input, not something to
  guess into the skill.

- **`ca-email-intake`** — variation-request flavour of intake (EOI/new-job is
  covered by `ca-new-job`). Blocked on the variation manual transcription.

Each skill, when proposed, is documented with: purpose, users, inputs, outputs,
systems/folders accessed, permissions, read/write behaviour, evidence/audit,
failure handling, security boundary, and maintenance burden.
