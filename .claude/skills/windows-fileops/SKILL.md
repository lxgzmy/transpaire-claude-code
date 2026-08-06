---
name: windows-fileops
description: >
  PowerShell 7 file and folder management on the Windows server and the Z: share.
  Use when listing, searching, reading, comparing, or reporting on folders and
  files under Z:\ (share-drive paths with spaces and brackets), when writing or
  reviewing server-side scripts, or when a task needs Windows-native path
  handling. Read-only by default; moving, renaming, or deleting business files
  requires explicit human approval.
---

# Windows file operations (PowerShell 7)

Windows-native folder and file management for this project, on the server and
the `Z:` share. Applies whenever a task touches Windows paths.

This is the **technique layer**: how to do Windows file work safely. If the task
is a business question about the share ("where is it?", "where should this go?",
"is this a mess?"), use the `z-drive-ops` skill instead — it holds the drive map,
the sensitive-folder blocklist, and the plain-English answering style, and calls
down to these recipes.

## Ground rules

- Script with **PowerShell 7 (`pwsh`)**, never Windows PowerShell 5.1 and never
  Bash. In Claude Code, use the PowerShell tool for anything touching Windows
  paths; the Bash tool is Git Bash, where `Z:\` appears as `/z/` and quoting
  differs, which causes silent path errors.
- **Read-only by default.** Listing, searching, hashing, and reporting are
  always safe. Moving, renaming, or deleting business files requires explicit
  human approval naming the exact files (HITL), and must preserve NTFS
  permissions.
- **Never write to `C:`.** All generated output goes to the repo's git-ignored
  `runtime\<job-role>\...` folders on `Z:`.
- Never hardcode server names or UNC paths in scripts, prompts, logs, or
  commits. Refer only to the mapped `Z:` drive.

## Before touching Z:

`Z:` is an SMB mapping and is **per-session** (each RDP or console session maps
it separately). Verify before any operation:

```powershell
if (-not (Get-PSDrive -Name Z -ErrorAction SilentlyContinue)) {
    throw "Z: drive is not mapped in this session. Map it before continuing."
}
```

## Path handling

- Always quote paths containing spaces: `"Z:\CLAUDE CODE\..."`.
- Use `-LiteralPath` whenever a name may contain `[`, `]`, or other wildcard
  characters, which are common in job folders such as
  `26049 - LOT 5 (12) PEARSON STREET, GUNNEDAH NSW`:

  ```powershell
  Get-ChildItem -LiteralPath $path
  ```

- Build paths with `Join-Path`, not string concatenation.
- Windows names are case-insensitive: compare case-insensitively, but preserve
  the original casing in any report or output.
- Deep job folders can exceed the legacy 260-character limit. PowerShell 7
  handles long paths, but flag any path over ~240 characters in reports, since
  Explorer and Office may still fail on them.

## Read-only recipes

List a folder, including hidden items:

```powershell
Get-ChildItem -LiteralPath $path -Force
```

Full recursive inventory with size and dates:

```powershell
Get-ChildItem -LiteralPath $path -Recurse -File -Force |
    Select-Object FullName, Length, LastWriteTime
```

Find the latest (likely authoritative) version of a document:

```powershell
Get-ChildItem -LiteralPath $path -Recurse -File -Filter "*variation*" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

Find duplicate files by content hash:

```powershell
Get-ChildItem -LiteralPath $path -Recurse -File |
    Get-FileHash -Algorithm SHA256 |
    Group-Object Hash | Where-Object Count -gt 1
```

Folder size summary:

```powershell
Get-ChildItem -LiteralPath $path -Directory | ForEach-Object {
    [pscustomobject]@{
        Folder = $_.Name
        MB     = [math]::Round((Get-ChildItem -LiteralPath $_.FullName -Recurse -File |
                 Measure-Object Length -Sum).Sum / 1MB, 1)
    }
}
```

## Writing outputs

- Reports (CSV / Markdown) go to `runtime\<job-role>\reports\`; logs to
  `runtime\<job-role>\logs\`.
- Create target folders with `New-Item -ItemType Directory -Force`.
- Never write to `C:`, Dropbox-synced folders, or git-tracked paths.

## Do not

- Do not run `Remove-Item`, `Move-Item`, or `Rename-Item` against business
  files without an approved instruction naming the exact files.
- Do not use WSL or Linux path forms (`/mnt/z`, `/z/`) in server scripts.
- Do not store credentials, connection strings, or server names in scripts.
