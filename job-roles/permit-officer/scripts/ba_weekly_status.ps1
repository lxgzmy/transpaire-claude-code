<#
.SYNOPSIS
  Is the Monday BA draft on track? One look at the scheduled task, this week's drop folder, the run
  log and the checkout. Read-only.

.DESCRIPTION
  Run it in PowerShell 7 on the server, from the Z: checkout, any time; on a Monday after 06:30 it says
  whether the draft is out and, if not, why. It catches what the drop-folder note cannot: a task that
  never started (a changed password, a disabled task, the server off all week), a checkout left on
  another branch, and a week with neither a draft nor a note.

  Exit code 0 when nothing needs a person, 1 when something does; each reason is on its own line.

.PARAMETER TaskName
  The scheduled task register_ba_weekly_task.ps1 set up.

.PARAMETER Drop
  For the regression suite only: another drop folder.

.PARAMETER Logs
  For the regression suite only: another logs folder.
#>
param(
    [string]$TaskName = 'Transpire - BA report weekly draft',
    [string]$Drop = 'Z:\AI test\Permit Officer\BA Report test',
    [string]$Logs = ''
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
if (-not $Logs) { $Logs = Join-Path $repo 'runtime\permit-officer\logs' }
$attention = [Collections.Generic.List[string]]::new()
$facts = [Collections.Generic.List[string]]::new()
$now = Get-Date

# What the task's last result means (the wrapper's own codes, then Task Scheduler's).
$results = @{
    '0'          = 'finished (drafted, or nothing to do)'
    '1'          = 'Python stopped with an error; see that day''s ba-weekly log'
    '2'          = 'stopped; a note saying why is in the drop folder'
    '3'          = 'stopped on an unexpected error; a note is in the drop folder'
    '4'          = 'Z: could not be mapped, so the share was unreachable'
    '5'          = 'the wrapper itself failed (Python not found?); see that day''s ba-weekly log'
    '267009'     = 'running now'
    '267011'     = 'has not run yet'
    '267014'     = 'was stopped, by a person or the one-hour limit'
    '2147750687' = 'did not start: the last run was still going'
    '2147942402' = 'did not start: pwsh or the wrapper was not found'
    '2147943726' = 'did not start: Windows could not sign in as the task''s account (its password has changed). Run register_ba_weekly_task.ps1 again'
    '2147943785' = 'did not start: the account may not log on as a batch job'
}
$fine = '0', '267009', '267011'

# ---- the task
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    $attention.Add("The scheduled task '$TaskName' is not registered: run register_ba_weekly_task.ps1.")
} else {
    $info = $task | Get-ScheduledTaskInfo
    $facts.Add("Task: $($task.State), runs as $($task.Principal.UserId) ($($task.Principal.LogonType)), next run $('{0:ddd dd/MM/yyyy HH:mm}' -f $info.NextRunTime)")
    if ($task.State -eq 'Disabled') { $attention.Add('The scheduled task is disabled: enable it in Task Scheduler.') }
    if ($task.Principal.LogonType -ne 'Password') {
        $attention.Add("The task logs on as '$($task.Principal.LogonType)', not with a stored password, so it cannot reach the share while nobody is signed in: run register_ba_weekly_task.ps1 again.")
    }
    $file = if ($task.Actions[0].Arguments -match '-File "([^"]+)"') { $Matches[1] } else { '' }
    $tail = '\job-roles\permit-officer\scripts\ba_weekly_task.ps1'
    if (-not $file.EndsWith('\transpire-claude-code' + $tail, [StringComparison]::OrdinalIgnoreCase)) {
        $attention.Add("The task starts '$file', not the shared checkout's ba_weekly_task.ps1.")
    } elseif (Test-Path -LiteralPath $file) {
        # Look at the checkout the task runs, wherever this check was started from.
        $repo = $file.Substring(0, $file.Length - $tail.Length)
        if (-not $PSBoundParameters.ContainsKey('Logs')) { $Logs = Join-Path $repo 'runtime\permit-officer\logs' }
    } else {
        $attention.Add("The task starts '$file', which is not there.")
    }
    $raw = [long]$info.LastTaskResult
    $code = "$(if ($raw -lt 0) { $raw + 4294967296 } else { $raw })"
    $said = if ($results.ContainsKey($code)) { $results[$code] } else { 'code {0} (0x{0:X})' -f [long]$code }
    $last = if ($info.LastRunTime.Year -lt 2000) { 'never' } else { '{0:ddd dd/MM/yyyy HH:mm}' -f $info.LastRunTime }
    $facts.Add("Last run: $last, $said")
    if ($code -notin $fine) { $attention.Add("The last run $said.") }

    # The latest slot the triggers say should have started by now (10 minutes' grace).
    $slot = $null
    foreach ($t in $task.Triggers) {
        if (-not $t.Enabled) { continue }
        $at = ([datetime]$t.StartBoundary).TimeOfDay
        for ($d = 0; $d -le 7; $d++) {
            $day = $now.Date.AddDays(-$d)
            $when = $day + $at
            if ($when -gt $now.AddMinutes(-10)) { continue }
            if (($t.DaysOfWeek -band (1 -shl [int]$day.DayOfWeek)) -and (-not $slot -or $when -gt $slot)) { $slot = $when }
        }
    }
    if ($slot -and $task.State -ne 'Running' -and ($info.LastRunTime.Year -lt 2000 -or $info.LastRunTime -lt $slot.AddMinutes(-1))) {
        $attention.Add("The run due $('{0:ddd dd/MM/yyyy HH:mm}' -f $slot) has not started (last run: $last). Check the task's History tab for why.")
    }
    $days = ($task.Triggers | ForEach-Object { $_.DaysOfWeek }) | Sort-Object -Unique
    $times = ($task.Triggers | ForEach-Object { '{0:HH:mm}' -f [datetime]$_.StartBoundary }) | Sort-Object
    if ("$days" -ne '14' -or ($times -join ',') -ne '06:30,12:30') {
        $attention.Add("The task's triggers are not 06:30 and 12:30 each Monday, Tuesday and Wednesday (days $days, times $($times -join ', ')): run register_ba_weekly_task.ps1 again.")
    }
}

# ---- this week's Monday in the drop folder (as ba_weekly_run.draft_monday picks it)
$dow = [int]$now.Date.DayOfWeek
$monday = if ($dow -eq 6) { $now.Date.AddDays(2) } elseif ($dow -eq 0) { $now.Date.AddDays(1) } else { $now.Date.AddDays(1 - $dow) }
$tag = '{0:dd.MM.yyyy}' -f $monday
$draft = Join-Path $Drop "BA REPORT DRAFT - $tag.xlsx"
$notice = Join-Path $Drop "BA REPORT DRAFT - $tag - NOT READY.txt"
$runLog = Join-Path $Logs 'ba-weekly-runs.log'
$runs = if (Test-Path -LiteralPath $runLog) { @(Get-Content -LiteralPath $runLog -Tail 3) } else { @() }
$shutdown = $runs | Where-Object { $_ -match "\| Monday $([regex]::Escape($tag)) \| [^|]+ \| shutdown" }
if (Test-Path -LiteralPath $draft) {
    $facts.Add("This week (Monday $tag): the draft is in the drop folder, saved $('{0:ddd dd/MM/yyyy HH:mm}' -f (Get-Item -LiteralPath $draft).LastWriteTime)")
} elseif (Test-Path -LiteralPath $notice) {
    $why = (Get-Content -LiteralPath $notice | Where-Object { $_ -like 'Why:*' } | Select-Object -First 1)
    $attention.Add("No draft for Monday $tag yet; the note in the drop folder says: $why")
} elseif ($shutdown) {
    $facts.Add("This week (Monday $tag): the Christmas shutdown, no draft due")
} elseif ($now -lt $monday.AddHours(6).AddMinutes(40)) {
    $facts.Add("This week (Monday $tag): not due yet; the first run is Monday at 06:30")
} else {
    $attention.Add("No draft for Monday $tag and no note saying why in the drop folder.")
}

# ---- the checkout the task runs
function Get-Git { try { (git -c "safe.directory=*" -C $repo @args 2>$null) -join '' } catch { '' } }
$branch = Get-Git rev-parse --abbrev-ref HEAD
$head = Get-Git log -1 --format=%h
$behind = Get-Git rev-list --count HEAD..origin/main
$facts.Add("Checkout: $branch at $head" + $(if ($behind -and $behind -ne '0') { ", $behind behind origin/main as last fetched" } else { '' }))
if ($branch -ne 'main') { $attention.Add("The checkout is on '$branch', not main, so the task runs that code: put it back on main.") }
elseif ($behind -and $behind -ne '0') { $attention.Add("The checkout is $behind commit(s) behind origin/main as last fetched: pull.") }

if ($runs) { $facts.Add('Run log, last lines:'); $runs | ForEach-Object { $facts.Add("  $_") } }

if ($attention.Count) {
    'BA report weekly draft: NEEDS A PERSON'
    $attention | ForEach-Object { "  - $_" }
} else {
    'BA report weekly draft: OK'
}
$facts | ForEach-Object { "  $_" }
exit ([int]($attention.Count -gt 0))
