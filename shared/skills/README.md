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

- **transpaire-writing** (project, in `.claude/skills/`) — the sanctioned entry point
  for all Transpire writing. Layers the Transpire house voice
  (`shared/conventions/writing-style.md`) + job-role/audience matching on top of the
  de-AI patterns. This is the customisation, so it lives in the repo.
- **humanizer** (project, in `.claude/skills/`) — the generic de-AI engine, vendored
  into the repo so every checkout (server and dev clones) has it without a per-machine
  global install. Referenced by `transpaire-writing` for step 1 (de-AI). If a global
  copy also exists on a dev machine, the project copy in this repo is the canonical
  one for Transpire work.
- **windows-fileops** (project, in `.claude/skills/`) — PowerShell 7 + Windows/Z:
  share folder management: per-session drive-mapping checks, safe path handling
  (spaces, brackets, long paths), read-only inventory/duplicate/latest-version
  recipes, and output routing to `runtime\<role>\`. Read-only by default; HITL for
  any move/rename/delete.
