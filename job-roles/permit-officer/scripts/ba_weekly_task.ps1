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
  4 Z: could not be mapped.

.PARAMETER ShareRoot
  The share Z: maps to, as the task was registered with (never written into the repo).
#>
param(
    [Parameter(Mandatory)][string]$ShareRoot,
    [string]$Contact = '',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$ShareRoot = $ShareRoot.TrimEnd('\')

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
$logs = Join-Path $repo 'runtime\permit-officer\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$log = Join-Path $logs ('ba-weekly-{0:yyyy-MM-dd}.log' -f (Get-Date))

$python = (Get-Command python -ErrorAction Stop).Source
$pyArgs = @('-X', 'utf8', (Join-Path $here 'ba_weekly_run.py'), '--scheduled')
if ($Contact) { $pyArgs += @('--contact', $Contact) }
if ($DryRun) { $pyArgs += '--dry-run' }

# Which code ran: the shared checkout is meant to stay on main (CLAUDE.md, git workflow).
$ran = try { (git -c "safe.directory=*" -C $repo log -1 --format='%h %D' 2>$null) -join ' ' } catch { 'unknown' }
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $env:USERDOMAIN\$env:USERNAME, code $ran" |
    Out-File -FilePath $log -Append -Encoding utf8
& $python @pyArgs *>&1 | Out-File -FilePath $log -Append -Encoding utf8
$code = $LASTEXITCODE
"==== exit $code" | Out-File -FilePath $log -Append -Encoding utf8
exit $code
