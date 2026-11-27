<#
.SYNOPSIS
  The unattended Monday BA report run, started by the scheduled task that
  register_ba_weekly_task.ps1 sets up (workflows/ba-weekly-report.md).

.DESCRIPTION
  Task Scheduler starts this with no mapped drives, so it maps Z: to the share it is given, for this
  run only, then runs ba_weekly_run.py --scheduled. The task runs it at 06:30 and 12:30 each Monday,
  Tuesday and Wednesday; once the Monday's draft is in the drop folder, each run does nothing.

  Each run's full output is appended to runtime\permit-officer\logs\ba-weekly-<date>.log, and the
  run itself adds one line to ba-weekly-runs.log beside it. Exit codes: 0 delivered or nothing to do,
  2 stopped (a note saying why is left in the drop folder), 3 an unexpected error (likewise),
  4 Z: could not be mapped, 5 this wrapper failed (no Python, say). Any other code is Python's own.

  No stop is silent. Whenever the run ends with any code but 0, and neither the Monday's draft nor a
  note is in the drop folder, this wrapper leaves the note itself; and when the run wrote no line to
  ba-weekly-runs.log (it crashed before it could), this wrapper writes it. A checkout that is not on
  main still runs, with a warning line in both logs, since a draft from that code is better than none.

.PARAMETER ShareRoot
  The share Z: maps to, as the task was registered with (never written into the repo).

.PARAMETER Python
  For the regression suite only: the Python to run instead of the one on PATH.

.PARAMETER Drop
  For the regression suite only: the drop folder this wrapper leaves its own note in.

.PARAMETER Logs
  For the regression suite only: the logs folder instead of runtime\permit-officer\logs.
#>
param(
    [Parameter(Mandatory)][string]$ShareRoot,
    [string]$Contact = '',
    [switch]$DryRun,
    [string]$Python = '',
    [string]$Drop = '',
    [string]$Logs = ''
)
$ErrorActionPreference = 'Stop'
$ShareRoot = $ShareRoot.TrimEnd('\')

# The same as ba_weekly_run.py's DROP, NOTICE_NAME, SCHEDULE_DAYS and SCHEDULE_TIMES (the regression
# suite compares them), for a note when Python cannot leave its own.
$dropDefault = 'Z:\AI test\Permit Officer\BA Report test'
$noticeName = 'BA REPORT DRAFT - {0:dd.MM.yyyy} - NOT READY.txt'
$draftName = 'BA REPORT DRAFT - {0:dd.MM.yyyy}.xlsx'
$retryLine = 'The run tries again at 6:30 am and 12:30 pm each Monday, Tuesday and Wednesday.'
$lastDay = 'Wednesday'

if (-not (Test-Path -LiteralPath 'Z:\')) {
    net use Z: $ShareRoot /persistent:no | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath 'Z:\')) { exit 4 }
}

# This script's folder on Z:, however the task named it (the Z: path or the share's own path).
$here = $PSScriptRoot
if ($here.StartsWith($ShareRoot, [StringComparison]::OrdinalIgnoreCase)) {
    $here = 'Z:' + $here.Substring($ShareRoot.Length)
}
$repo = [IO.Path]::GetFullPath((Join-Path $here '..\..\..'))
if (-not $Logs) { $Logs = Join-Path $repo 'runtime\permit-officer\logs' }
if (-not $Drop) { $Drop = $dropDefault }
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$log = Join-Path $Logs ('ba-weekly-{0:yyyy-MM-dd}.log' -f (Get-Date))
$runLog = Join-Path $Logs 'ba-weekly-runs.log'
$mode = if ($DryRun) { 'dry run' } else { 'scheduled' }

# The Monday the run drafts for, as ba_weekly_run.draft_monday: this week's, at the weekend the coming one.
$today = (Get-Date).Date
$dow = [int]$today.DayOfWeek  # Sunday 0 ... Saturday 6
$monday = if ($dow -eq 6) { $today.AddDays(2) } elseif ($dow -eq 0) { $today.AddDays(1) } else { $today.AddDays(1 - $dow) }

function Write-Log([string]$text) {
    try { $text | Out-File -FilePath $log -Append -Encoding utf8 } catch { }
}
function Write-RunLog([string]$outcome, [string]$detail) {
    # One line per entry, as ba_weekly_run.record_run writes them.
    $detail = ($detail -replace '\s+', ' ').Trim()
    $line = '{0:yyyy-MM-dd HH:mm:ss} | Monday {1:dd.MM.yyyy} | {2} | {3} | {4}' -f (Get-Date), $monday, $mode, $outcome, $detail
    try { $line | Out-File -FilePath $runLog -Append -Encoding utf8 } catch { }
}

function Get-RunLogLength {
    if (Test-Path -LiteralPath $runLog) { (Get-Item -LiteralPath $runLog).Length } else { 0 }
}

$code = 5
$problem = ''
$runLogBefore = $null
try {
    # Which code ran: the shared checkout is meant to stay on main (CLAUDE.md, git workflow).
    $ran = try { (git -c "safe.directory=*" -C $repo log -1 --format='%h %D' 2>$null) -join ' ' } catch { 'unknown' }
    $branch = try { (git -c "safe.directory=*" -C $repo rev-parse --abbrev-ref HEAD 2>$null) -join '' } catch { '' }
    Write-Log "==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $env:USERDOMAIN\$env:USERNAME, code $ran"
    if ($branch -ne 'main') {
        $warn = "the checkout is on '$branch', not main, so this run uses that code; put it back on main"
        Write-Log "warning: $warn"
        Write-RunLog 'warning' $warn
    }
    $py = if ($Python) { $Python } else { (Get-Command python -ErrorAction Stop).Source }
    $pyArgs = @('-X', 'utf8', (Join-Path $here 'ba_weekly_run.py'), '--scheduled')
    if ($Contact) { $pyArgs += @('--contact', $Contact) }
    if ($DryRun) { $pyArgs += '--dry-run' }
    $runLogBefore = Get-RunLogLength
    & $py @pyArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    $code = $LASTEXITCODE
} catch {
    Write-Log "wrapper error: $($_.Exception.Message)"
    $problem = ($_.Exception.Message -split '\r?\n')[0].Trim()
}

if ($code -ne 0) {
    $why = if ($problem) { "the run could not start ($problem)" } else { "the run stopped before it could say why (exit $code)" }
    $why += "; the details are in $(Split-Path -Leaf $log) on the server"
    # Python records every run it gets as far as; a run that crashed first is recorded here.
    if ($null -eq $runLogBefore -or (Get-RunLogLength) -le $runLogBefore) { Write-RunLog 'stopped' $why }
    $draft = Join-Path $Drop ($draftName -f $monday)
    $notice = Join-Path $Drop ($noticeName -f $monday)
    if (-not $DryRun -and -not (Test-Path -LiteralPath $draft) -and -not (Test-Path -LiteralPath $notice)) {
        $who = if ($Contact) { $Contact } else { 'the person who runs the AI pilot' }
        $text = (@("No BA report draft has been made for Monday $('{0:dd.MM.yyyy}' -f $monday) yet.", '',
                   "Why: $why", '', "$retryLine This note goes once the draft is delivered.",
                   "If it is still here on $lastDay afternoon, please let $who know.") -join "`r`n") + "`r`n"
        try {
            [IO.File]::WriteAllText($notice, $text, [Text.UTF8Encoding]::new($false))
            Write-Log "A note saying why is in the drop folder: $notice"
        } catch {
            Write-Log "The note for the drop folder could not be written ($($_.Exception.Message))"
        }
    }
}
Write-Log "==== exit $code"
exit $code
