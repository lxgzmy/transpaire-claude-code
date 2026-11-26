<#
.SYNOPSIS
  Sets up (or replaces) the scheduled task that makes the Monday BA report draft unattended.

.DESCRIPTION
  Run it once, in your own PowerShell 7 window on the server, from the Z: checkout, signed in as the
  account the task should run as. It asks for that account's password: Windows keeps it with the
  task, so the run happens whether or not anyone is signed in, with that account's access to the
  share. Nothing else is changed. Run it again to change the contact name; -Remove takes the task
  away.

  The task starts ba_weekly_task.ps1 at 06:30 and 12:30 each Monday, Tuesday and Wednesday (a run
  missed while the server was off starts when it is back). ba_weekly_run.py holds the same days and
  times in SCHEDULE_DAYS / SCHEDULE_TIMES for the note it leaves in the drop folder, and its
  self-check compares the two.

.PARAMETER Contact
  Who the drop-folder note tells the officer to ask when a draft is late, e.g. a first name.

.PARAMETER Show
  Say what would be registered, change nothing.
#>
param(
    [string]$TaskName = 'Transpire - BA report weekly draft',
    [string]$Contact = '',
    [switch]$Show,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "Removed: $TaskName"
    return
}

$drive = Get-PSDrive -Name Z -PSProvider FileSystem -ErrorAction SilentlyContinue
$share = if ($drive) { $drive.DisplayRoot } else { $null }
if (-not $share) { throw 'Z: is not a mapped network drive in this window. Map it, then run this again.' }
$share = $share.TrimEnd('\')
$wrapper = Join-Path $PSScriptRoot 'ba_weekly_task.ps1'
if ($wrapper -notlike 'Z:\*') { throw "Run this from the Z: checkout; it was started from $wrapper." }
$wrapperOnShare = $share + $wrapper.Substring(2)

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$argLine = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$wrapperOnShare`" -ShareRoot `"$share`""
if ($Contact) { $argLine += " -Contact `"$Contact`"" }
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $argLine
$days = 'Monday', 'Tuesday', 'Wednesday'
$times = '06:30', '12:30'
$triggers = $times | ForEach-Object { New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $_ }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$user = "$env:USERDOMAIN\$env:USERNAME"

"Task:     $TaskName"
"Runs as:  $user (whether or not anyone is signed in)"
"When:     $($times -join ' and ') each $($days -join ', ')"
"Starts:   $pwsh $argLine"
if ($Show) { 'Nothing registered (-Show).'; return }

$cred = Get-Credential -UserName $user -Message "Password for $user, kept by Windows with the scheduled task"
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings `
    -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited -Force `
    -Description 'Permit Officer: the Monday BA report draft (job-roles/permit-officer/scripts/ba_weekly_run.py --scheduled).' |
    Out-Null
Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo |
    Format-List TaskName, NextRunTime, LastRunTime, LastTaskResult
