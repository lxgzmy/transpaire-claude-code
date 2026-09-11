# skills/

Contract-Admin job-role skills are authored here (skill definition + any
PowerShell 7 / Python scripts). **Propose before creating.**

To be loadable by Claude Code, an activated skill is registered under
`.claude/skills/` (prefix the name with the role, e.g. `ca-email-intake`).

Built:

- **`new-contract-template`** (registered in
  `.claude/skills/new-contract-template/`) — invoke as
  `/new-contract-template <email-file-or-subject>`. Orchestrates
  [`../workflows/new-contract.md`](../workflows/new-contract.md): reads the build
  contract request chain and its attachments, performs OSC intake through
  [the MCP execution reference](../../../.claude/skills/new-contract-template/references/osc-new-contract.md)
  (issue #34's Word items 1–9, approved writes, DataBuild excluded), then
  picks the correct **existing** blank
  template off `Z:\PROCEDURES & FORMS\CONTRACTS\`, fills it via
  `../scripts/fill_inclusions.py`, diffs filled against blank, and **saves in the
  same pass** (the preview/approval stop was removed 17 Aug 2026), **routed
  per document** (8 Sep 2026): a document type the job's `CONTRACT
  DOCUMENTATION` already holds refreshes to
  `cowork-projects\3.new_contract\template-testing\<job>\`; a document type
  not there yet saves its pair into the job folder, never overwriting
  (CD-7.6/7.7). Produces the inclusions and preliminary agreement as completed
  `.docx` **plus the PDF export** (CD-7.4 — every completed job keeps the
  pair); the **build contract is filled in the same pass** whenever a usable
  Word template exists (`../scripts/fill_hia.py`, NSW+QLD, CD-5.2b, 18 Aug
  2026): an MCR-approved blank in the region's `CONTRACT\` folder → real
  deliverable name; none yet → the region's staged interim template (NSW:
  v1.1 TABLES; QLD: v2.1 LAND TABLES — both 3 Sep 2026) fills under the real
  name too, in PRODUCTION and TEST alike (8 Sep 2026), with the interim
  provenance flagged for the reviewer; no staged template → data sheet only
  (CD-5.1/5.2a). DataBuild figures fill only
  when a person keys them into the job JSON — never calculated — and legal
  statements are never filled (CD-5.4). **Sydney inclusions content (10 Sep
  2026, CD-9):** the run edits section 18 to the job's area, actions the
  Bathroom 2 / air-con notes, writes the `UPGRADED INCLUSIONS` items from the
  job's `upgrades` block in Standard Variation wording
  (`../scripts/edit_inclusions.py`), re-levels the two columns through Word
  (`../scripts/word_layout.ps1`) and gates the result
  (`../scripts/gate_inclusions.py`) before it can save; the row a request maps
  to and any custom wording stay a person's call, reported with a confidence
  flag. Never invents contract wording of its own, never
  signs, never sends. Rules: [`../rules/contract-docs.md`](../rules/contract-docs.md).

  Staff guide (HTML source + formatted PDF):
  [`docs/new_contract_claude_guide.html`](../../../docs/new_contract_claude_guide.html)
  → `docs/Transpire_new_contract_claude_guide.pdf`. Markdown source and a PDF copy
  also sit in `Z:\CLAUDE CODE\cowork-projects\3.new_contract\`, mirroring the
  `z-drive-ops` guide. Rebuild the PDF from the HTML headlessly — on this
  server the browser is **Edge** (no Chrome installed; verified 18 Aug 2026):

  ```
  "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless --disable-gpu --no-pdf-header-footer --user-data-dir="Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\state\chrome-render" --print-to-pdf="<out.pdf>" "<file:///...html>"
  ```

  (`--user-data-dir` stops a headless Chromium dumping a Crashpad folder at
  the `Z:\` root — Chrome did exactly that on 11 Aug 2026.)

  **Not role-prefixed**: the name was requested as `/new-contract-template`.
  Renaming it `ca-new-contract-template` would match the convention below —
  worth settling before anyone learns the current name.

Retired:

- **`ca-new-job`** (removed 18 Aug 2026) — EOI intake → OSC draft sheets →
  DataBuild email draft, with `extract_eoi.py` and the `osc_entry.py` dry-run.
  Removed with its workflow spec, scripts and fixtures in favour of
  `/new-contract-template`; OSC intake is now integrated into that existing skill
  through MCP (11 September 2026). The `JD-*` rules it transcribed remain in
  `../rules/job-details.md` (the new-contract workflow relies on them).

Planned:

- **`ca-email-intake`** — variation-request flavour of intake. Blocked on the
  variation manual transcription.

## Where `/new-contract-template` saves its documents

**Where the contract documents go (four rules, 8 Sep 2026)**

1. Every `/new-contract-template` run first looks in the job's
   `Z:\PROJECTS\<region>\<job>\CONTRACT\CONTRACT DOCUMENTATION\` folder and
   notes which contract documents are already there: inclusions, preliminary
   agreement, build contract (`SS\` included).
2. A document the job folder does **not** have is a **real contract, not a
   test**. Its `.docx` + `.pdf` are saved straight into that `CONTRACT
   DOCUMENTATION` folder. It never goes to template-testing.
3. A document the job folder **already** has is treated as a **test /
   refresh**. Its `.docx` + `.pdf` go only to
   `Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\`.
   The original in the job folder is never overwritten; a person swaps it in
   (old version to `SS\`).
4. The build contract is **no longer blocked**. While NSW / QLD has no
   MCR-filed Word blank in its `CONTRACT\` template folder, the run fills the
   staged interim template under the real file name; the run report names
   the template, and a person reads the draft against the licensed HIA PDF
   before it is issued.

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
