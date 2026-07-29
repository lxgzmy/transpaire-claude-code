# CLAUDE.md — Transpire Contract-Admin Automation

Guardrails for Claude Code working on this project. This file is auto-loaded as
project memory. Read it before creating files, running scripts, or generating
any client-facing artifact.

## What this project is

Proof-of-concept automation of the builder-side **Contract Administration** role
for Transpire Constructions (Australian residential home builder). Two workflows:
**New Job Creation** and **Variation Stage 1**. Full design lives in `docs/`.

Claude Code is the **orchestrator and judgment layer** — it reads emails, applies
rules, and calls deterministic step-scripts. It does **not** move the mouse
itself; OnSite Companion (OSC) UI work is done by Python `pywinauto` step-scripts
with per-step screenshot evidence. Every externally visible artifact is a **draft
for human review** before anything is sent.

## Environment & path rules (MANDATORY on Windows Server 2022)

- **Never** write project data, generated files, caches, temp files, logs, or
  working files to the `C:` drive.
- All runtime output goes under **`Z:\CLAUDE CODE`**.
- Contract Administration team workspace: **`Z:\CLAUDE CODE\CONTRACT ADMN`**.
- This applies to state, evidence/screenshots, logs, extracted job/variation
  JSON, populated Excel/Word/PDF — everything.
- **Do not** write runtime/client data into this repository or any Dropbox-synced
  folder. The repo holds code, skills, rules, and docs only. `.gitignore` blocks
  `state/`, `evidence/`, `*.log`, `*.job.json`, `*.variation.json` as a backstop.
- The Z: drive is mapped per RDP session; confirm it is mapped before writing.

## Human-in-the-loop (HITL)

- The review gate sits **between extraction and data entry**.
- Claude drafts what it intends to enter/generate (with an evidence bundle:
  screenshots + diffs), a person approves during morning review, then step-scripts
  run. Nothing is sent to a client/owner without explicit approval.
- Flag low-confidence extractions for human confirmation rather than guessing.

## Naming & data conventions (from the source manuals — see `rules/`)

- Enforce **UPPERCASE** where the manuals require it (e.g. new-job request subject
  `NEW JOB`; suburb in CAPS).
- **QLD** jobs: certifier = **Buildable**.
- Verify suburb/postcode and council via lookup before entry.
- **Variation numbering:** Post-Contract / Building variations `VAR-001+`; Internal
  variations `VAR-021+`. Pick the next number from OSC. File naming `VAR-#####001`.
- **Workflow template selection:** 9.1 or 9.4 depending on variation type; append
  9.2 when prompted.
- These are summarised from the source manuals; the authoritative detail lives in
  `rules/job-details.md` and `rules/variation-rules.md` (pending the manuals).

## System access order (per docs/03)

1. **DataBuild reads** → read-only SQL (no UI).
2. **DataBuild writes** → native XML/CSV import, or the existing OSC→DataBuild
   vendor bridge. UI automation only as a last resort.
3. Validate any DataBuild access against a **test/backup copy** first — never write
   to the live DB until the schema is understood.

## Skills

- `.claude/skills/humanizer/` — de-AI-ify / naturalise prose before it goes to a
  human or client. Also installed globally.
- Contract-Admin skills (`ca-email-intake`, `ca-zdrive`, and later
  `ca-onsite-companion`, `ca-databuild`) are **not built yet** — they are blocked
  on the source manuals and OSC/DataBuild validation. See the plan and `rules/`.

## Do not

- Do not install or reference the OpenAI Codex `ecc-*` / `au-family-*` skills under
  `~/Documents/nl-codex` — different platform, and the family skills contain
  unrelated personal PII.
- Do not commit secrets, connection strings, or client PII.
