# Transpire Claude Code - role-aware status line
# Reads the Claude Code JSON payload from stdin and prints one line:
#   <context>  <branch>  <model>
# Requires PowerShell 7 (pwsh). Wired via .claude/settings.json -> statusLine.
# This file must stay on the Z: drive (see project CLAUDE.md) - never on C:.

$ErrorActionPreference = 'SilentlyContinue'

$raw = [Console]::In.ReadToEnd()
$data = $null
if ($raw) {
    try { $data = $raw | ConvertFrom-Json } catch { $data = $null }
}

# --- Resolve working directory defensively (fields may be absent) ---
$cwd = $null
if ($data -and $data.workspace -and $data.workspace.current_dir) {
    $cwd = $data.workspace.current_dir
} elseif ($data -and $data.cwd) {
    $cwd = $data.cwd
} else {
    $cwd = (Get-Location).Path
}

$projectDir = $cwd
if ($data -and $data.workspace -and $data.workspace.project_dir) {
    $projectDir = $data.workspace.project_dir
}

$modelName = $null
if ($data -and $data.model -and $data.model.display_name) {
    $modelName = $data.model.display_name
}

$esc   = [char]27
$reset = "$esc[0m"
$dim   = "$esc[2m"
$alarm = "$esc[1;7;31m"   # bold + inverse + red: obvious off-Z:-drive warning

# --- Context segment: role name if under job-roles\<role>\, else project root folder name ---
$roleName = $null
if ($cwd -and ($cwd -match '(?i)job-roles[\\/]+([^\\/]+)')) {
    $roleName = $Matches[1]
}

if ($roleName) {
    $contextText = $roleName
} elseif ($projectDir) {
    $contextText = Split-Path -Leaf $projectDir
} elseif ($cwd) {
    $contextText = Split-Path -Leaf $cwd
} else {
    $contextText = '?'
}

$onZDrive = $false
if ($cwd -and $cwd.Length -ge 2 -and ($cwd.Substring(0,2).ToUpper() -eq 'Z:')) {
    $onZDrive = $true
}

if ($onZDrive) {
    $contextSegment = "$dim$contextText$reset"
} else {
    $contextSegment = "$alarm!! $contextText !!$reset"
}

# --- Branch segment: current branch + '*' if dirty; omitted entirely outside a git repo ---
$branchSegment = $null
if ($cwd) {
    $isRepo = git -C "$cwd" --no-optional-locks rev-parse --is-inside-work-tree 2>$null
    if ($isRepo -eq 'true') {
        $branch = git -C "$cwd" --no-optional-locks rev-parse --abbrev-ref HEAD 2>$null
        if ($branch) {
            $statusOut = git -C "$cwd" --no-optional-locks status --porcelain 2>$null
            $branchText = $branch
            if ($statusOut) { $branchText = "$branchText*" }
            $branchSegment = "$dim$branchText$reset"
        }
    }
}

# --- Model segment ---
$modelSegment = $null
if ($modelName) {
    $modelSegment = "$dim$modelName$reset"
}

$segments = @()
if ($contextSegment) { $segments += $contextSegment }
if ($branchSegment)  { $segments += $branchSegment }
if ($modelSegment)   { $segments += $modelSegment }

Write-Output ($segments -join '  ')
