# shared/skills/

Skills usable across job-roles.

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
  **non-technical staff** (plain English, no commands shown) and runs on **two
  surfaces** — Claude Code on the server *and* Claude Desktop on a staff PC.
  Read-only by default; every create/move/rename/delete needs a named,
  per-batch approval. Carries its own drive map in
  `references/z-drive-map.md`, kept inside the skill folder so the folder zips
  up self-contained for Desktop. **The knowledge + judgement layer** — what
  lives where, what's safe to touch, how to answer a person.
  Setup: [docs/z_drive_claude_setup.md](../../docs/z_drive_claude_setup.md). Staff
  guide (Markdown + formatted PDF): `Z:\CLAUDE CODE\cowork-projects\2.z_drive\`.

  Not role-scoped, on purpose: the share is department-shaped above `PROJECTS`,
  and roles are a permission overlay rather than a folder axis (see
  [architecture-overview](../../docs/architecture-overview.md)). The
  Contract-Admin-only `ca-zdrive` was retired in favour of this before it was
  built.
