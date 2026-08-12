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
  `transpire-writing`, writes the evidence bundle. Draft-only: never writes
  to OSC, never sends email. Supersedes the planned `ca-email-intake` for the
  new-job case (variation-request intake still to come).

- **`new-contract-template`** (registered in
  `.claude/skills/new-contract-template/`) — invoke as
  `/new-contract-template <email-file-or-subject>`. Orchestrates
  [`../workflows/new-contract.md`](../workflows/new-contract.md): reads the build
  contract request chain and its attachments, picks the correct **existing** blank
  template off `Z:\PROCEDURES & FORMS\CONTRACTS\`, fills it via
  `../scripts/fill_inclusions.py`, diffs filled against blank, and presents a
  field table for approval before anything reaches a job folder. Produces the
  inclusions and preliminary agreement as completed `.docx`; the build contract is
  a **data sheet only**, because the current NSW/SEQ contracts are flat PDFs with
  no form fields (CD-5.1). Never invents contract wording, never signs, never
  sends. Rules: [`../rules/contract-docs.md`](../rules/contract-docs.md).

  Staff guide (HTML source + formatted PDF):
  [`docs/new_contract_claude_guide.html`](../../../docs/new_contract_claude_guide.html)
  → `docs/Transpire_new_contract_claude_guide.pdf`. Markdown source and a PDF copy
  also sit in `Z:\CLAUDE CODE\cowork-projects\3.new_contract\`, mirroring the
  `z-drive-ops` guide. Rebuild the PDF from the HTML with headless Chrome:

  ```
  chrome --headless --disable-gpu --no-pdf-header-footer --user-data-dir="Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\state\chrome-render" --print-to-pdf="<out.pdf>" "<file:///...html>"
  ```

  (`--user-data-dir` stops headless Chrome dumping a Crashpad folder at the
  `Z:\` root — it did exactly that on 11 Aug 2026.)

  **Not role-prefixed**, unlike `ca-new-job`: the name was requested as
  `/new-contract-template`. Renaming it `ca-new-contract-template` would match the
  convention below — worth settling before anyone learns the current name.

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
