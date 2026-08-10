# Transpire Claude Code - role-aware status line
# Reads the Claude Code JSON payload from stdin and prints one line:
#   <context>  <branch>  <model> - <effort>  ctx <used>% - <tokens>  $<cost>
# Requires PowerShell 7 (pwsh). Wired via .claude/settings.json -> statusLine.
# This file must stay on the Z: drive (see project CLAUDE.md) - never on C:.
#
# Every field is read defensively: older Claude Code builds, and other surfaces,
# may not send all of them. A missing field drops its segment rather than
# printing an error or a zero.

$ErrorActionPreference = 'SilentlyContinue'

# PowerShell 7.2+ strips ANSI escapes when stdout is redirected, and Claude Code
# reads this script through a pipe. Without this, every colour below is discarded
# silently - including the off-Z: warning.
if ($PSStyle) { $PSStyle.OutputRendering = 'Ansi' }

$raw = [Console]::In.ReadToEnd()
$data = $null
if ($raw) {
    try { $data = $raw | ConvertFrom-Json } catch { $data = $null }
}

$esc   = [char]27
$reset = "$esc[0m"
$dim   = "$esc[2m"
$amber = "$esc[33m"
$red   = "$esc[1;31m"
$alarm = "$esc[1;7;31m"   # bold + inverse + red: obvious off-Z:-drive warning

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

# Warn only when a Z:-rooted project has wandered off the Z: drive. Projects that
# never lived on Z: are somebody else's work, so they get no Transpire warning.
$projectOnZ = ($projectDir -and $projectDir.Length -ge 2 -and $projectDir.Substring(0, 2).ToUpper() -eq 'Z:')
$cwdOnZ     = ($cwd -and $cwd.Length -ge 2 -and $cwd.Substring(0, 2).ToUpper() -eq 'Z:')

if ($projectOnZ -and -not $cwdOnZ) {
    $contextSegment = "$alarm!! OFF Z: $contextText !!$reset"
} else {
    $contextSegment = "$dim$contextText$reset"
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

# --- Model + effort segment: "Opus 5 1M - high" ---
$modelSegment = $null
$modelParts = @()
if ($data -and $data.model -and $data.model.display_name) {
    # "Opus 5 (1M context)" is too wide for a status line; keep the useful half.
    $modelParts += ($data.model.display_name -replace '\s*\(1M context\)', ' 1M')
}
if ($data -and $data.effort -and $data.effort.level) {
    $modelParts += $data.effort.level
}
if ($data -and $data.fast_mode) {
    $modelParts += 'fast'
}
if ($modelParts.Count -gt 0) {
    $modelSegment = "$dim$($modelParts -join ' - ')$reset"
}

# --- Context-usage segment: "ctx 6% - 61k/1M" ---
function Format-Tokens {
    param([long]$Count)
    if ($Count -ge 1000000) {
        $m = $Count / 1000000
        if ($m -ge 10) { return ('{0:N0}M' -f $m) }
        return (('{0:N1}' -f $m) -replace '\.0$', '') + 'M'
    }
    if ($Count -ge 1000) { return ('{0:N0}k' -f ($Count / 1000)) }
    return "$Count"
}

$ctxSegment = $null
if ($data -and $data.context_window) {
    $cw = $data.context_window
    $usedPct = $null
    if ($null -ne $cw.used_percentage) {
        $usedPct = [int]$cw.used_percentage
    } elseif ($null -ne $cw.remaining_percentage) {
        $usedPct = 100 - [int]$cw.remaining_percentage
    }

    if ($null -ne $usedPct) {
        $ctxText = "ctx $usedPct%"
        if ($cw.total_input_tokens -and $cw.context_window_size) {
            $ctxText += ' - ' + (Format-Tokens ([long]$cw.total_input_tokens)) +
                        '/' + (Format-Tokens ([long]$cw.context_window_size))
        }

        # Colour only once it matters, so a quiet line stays quiet.
        if ($usedPct -ge 85) {
            $ctxSegment = "$red$ctxText$reset"
        } elseif ($usedPct -ge 60) {
            $ctxSegment = "$amber$ctxText$reset"
        } else {
            $ctxSegment = "$dim$ctxText$reset"
        }
    }
}

# --- Cost segment ---
$costSegment = $null
if ($data -and $data.cost -and $null -ne $data.cost.total_cost_usd) {
    $costSegment = "$dim`$$('{0:N2}' -f [double]$data.cost.total_cost_usd)$reset"
}

$segments = @()
foreach ($s in @($contextSegment, $branchSegment, $modelSegment, $ctxSegment, $costSegment)) {
    if ($s) { $segments += $s }
}

Write-Output ($segments -join '  ')
