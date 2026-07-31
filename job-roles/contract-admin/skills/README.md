# skills/

Contract-Admin job-role skills are authored here (skill definition + any
PowerShell 7 / Python scripts). **Nothing is built yet — propose before creating.**

To be loadable by Claude Code, an activated skill is registered under
`.claude/skills/` (prefix the name with the role, e.g. `ca-zdrive`).

Planned:

- **`ca-zdrive`** — read-only `Z:` search + save-location adviser + duplicate/stale
  report. Reads `Z:\PROJECTS`; writes only under the role's `runtime/…/reports/`.
  Runs as the requesting user so NTFS permissions are honoured. Never moves files.
- **`ca-email-intake`** — read-only extraction of EOI / variation-request emails into
  a structured job record with missing/low-confidence fields flagged; produces a
  draft for review. Blocked on a sanitised test EOI + read-only Graph access.

Each skill, when proposed, is documented with: purpose, users, inputs, outputs,
systems/folders accessed, permissions, read/write behaviour, evidence/audit,
failure handling, security boundary, and maintenance burden.
