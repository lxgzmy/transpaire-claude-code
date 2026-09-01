# shared/skills/

Skills usable across job-roles. This is the register for them.

Role-scoped skills are also registered in `.claude/skills/` so Claude Code can
load them, but they are **documented under their role**, not here — e.g.
`new-contract-template` in
[job-roles/contract-admin/skills/README.md](../../job-roles/contract-admin/skills/README.md).
Role prefixes (`ca-`) keep the two apart at a glance (that skill is unprefixed
by explicit request — see the role's README).

## Global vs vendored policy

- **Global skills** live in `~/.claude/skills/` and are available to every project
  and session. **Reference** them — do not vendor a copy into this repo.
- **Vendor a copy into the repo only** if the server must be pinned to a specific
  version independent of the global install. If you do vendor one, keep only what
  the skill needs (`SKILL.md` + its scripts) and drop third-party plugin/CI cruft
  (`.claude-plugin/`, `.github/`, foreign-platform agent files).

## Current

- **transpire-writing** (project, in `.claude/skills/`) — the sanctioned entry point
  for all Transpire writing. Layers the Transpire house voice
  (`shared/conventions/writing-style.md`) + job-role/audience matching on top of the
  de-AI patterns. This is the customisation, so it lives in the repo.
- **humanizer** (project, in `.claude/skills/`) — the generic de-AI engine, vendored
  into the repo so every checkout (server and dev clones) has it without a per-machine
  global install. Referenced by `transpire-writing` for step 1 (de-AI). If a global
  copy also exists on a dev machine, the project copy in this repo is the canonical
  one for Transpire work.
- **windows-fileops** (project, in `.claude/skills/`) — PowerShell 7 + Windows/Z:
  share folder management: per-session drive-mapping checks, safe path handling
  (spaces, brackets, long paths), read-only inventory/duplicate/latest-version
  recipes, and output routing to `runtime\<role>\`. Read-only by default; HITL for
  any move/rename/delete. **The technique layer** — how to do Windows file work.
- **z-drive-ops** (project, in `.claude/skills/`) — the **whole-`Z:` adviser for
  every role and every department**: find files, advise where to save something
  new, search any folder, report duplicates and clutter. Written for
  **non-technical staff** (plain English, no commands shown); staff reach it
  through Claude Desktop's **Code mode**, which reads the skill straight from
  this repo — nothing is packaged or installed per user.
  Read-only by default; every create/move/rename/delete needs a named,
  per-batch approval. Carries its own drive map in
  `references/z-drive-map.md` and the canonical job-location search in
  `scripts/find_job.ps1`, kept inside the skill folder so it stays
  self-contained. **The knowledge + judgement layer** — what
  lives where, what's safe to touch, how to answer a person.
  Setup: [docs/z_drive_claude_setup.md](../../docs/z_drive_claude_setup.md). Staff
  guide (HTML source + rendered PDF) in `docs/`, with a courtesy PDF copy at
  `Z:\CLAUDE CODE\cowork-projects\2.z_drive\`.

  Not role-scoped, on purpose — the reasoning, and the retirement of the
  Contract-Admin-only `ca-zdrive`, is recorded once in
  [job-roles/contract-admin/skills/README.md](../../job-roles/contract-admin/skills/README.md).

- **osc-api** (project, in `.claude/skills/`) — preloaded knowledge for the
  `osc-api` MCP server (see `docs/mcp-servers.md`): endpoint + field reference
  generated from the OSCAPI OpenAPI spec (`references/endpoints.md`, no
  hostnames — the generator enforces that), the query cookbook (always page,
  body-filter GETs, contract number → `jobID` GUID), and the write-gating
  rules. Saves the 6–10 discovery calls a fresh session otherwise spends on
  `osc_list_endpoints` / `osc_describe_endpoint`. Regenerate the reference
  with `scripts/generate_endpoints.py` when the API version moves.

## Role-scoped, listed here only because the name has no role prefix

- **new-contract-template** (Contract Admin, in `.claude/skills/`) — build contract
  request → filled contract templates. Despite the unprefixed name this is **not**
  a cross-role skill: it is Contract Admin's, and it is documented in
  [job-roles/contract-admin/skills/README.md](../../job-roles/contract-admin/skills/README.md)
  with the rest of the role. Noted here so nobody reads the missing `ca-` prefix as
  meaning org-level. Carries its own template map in
  `references/contract-template-map.md`.
