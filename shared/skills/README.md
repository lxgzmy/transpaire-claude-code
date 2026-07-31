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

- **humanizer** — naturalise prose before it goes to a human/client. Installed
  **globally** in `~/.claude/skills/humanizer/`. It does not need to be vendored here.
