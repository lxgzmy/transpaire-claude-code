<#
.SYNOPSIS
Create a new job's folder tree on Z: by copying the region's LOT MASTER FOLDER.

.DESCRIPTION
Every region folder under Z:\PROJECTS\ contains "00000 - LOT MASTER FOLDER" -
the template tree (incl. seeded template documents). A new job is that tree
copied to "<JobNumber> - <JobTitle>" in the same region folder.

DRY-RUN BY DEFAULT: without -Commit it only reports what it would create.
HITL: -Commit additionally requires interactive confirmation. Refuses to run
if the job number is already in use, and never overwrites anything.

The duplicate check covers the live region folder, that region's lifecycle
subfolders (HANDED OVER / ARCHIVE-HANDED OVER / CANCELLED) and the top-level
COMPLETED / CANCELLED CONTRACTS, and matches on the leading 5 digits because
real folder names vary around the separator ("26003- LOT", "16001 -LOT").

Naming observed on Z: (confirm against the region's existing jobs):
  <JobNumber> - LOT <lot> <STREET>, <SUBURB> <STATE>
Job-number source (OSC contract no vs DataBuild) - confirm with the business.

.EXAMPLE
pwsh new_job_folders.ps1 -Region GUNNEDAH -JobNumber 26046 -JobTitle "LOT 8 YARRAANDOO CLOSE, GUNNEDAH NSW"
pwsh new_job_folders.ps1 -Region GUNNEDAH -JobNumber 26046 -JobTitle "..." -Commit
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Region,
    [Parameter(Mandatory)] [string]$JobNumber,
    [Parameter(Mandatory)] [string]$JobTitle,
    [string]$ProjectsRoot = 'Z:\PROJECTS',
    [string]$MasterName = '00000 - LOT MASTER FOLDER',
    [switch]$Commit
)

$ErrorActionPreference = 'Stop'

# Z: is mapped per RDP session - verify before anything else (org guardrail)
if (-not (Test-Path -LiteralPath $ProjectsRoot)) {
    throw "Projects root '$ProjectsRoot' not reachable - is Z: mapped in this session?"
}

$regionPath = Join-Path $ProjectsRoot $Region
if (-not (Test-Path -LiteralPath $regionPath)) {
    $known = (Get-ChildItem -LiteralPath $ProjectsRoot -Directory).Name -join ', '
    throw "Region '$Region' not found under $ProjectsRoot. Known: $known"
}

$master = Join-Path $regionPath $MasterName
if (-not (Test-Path -LiteralPath $master)) {
    throw "Master template '$MasterName' not found in $regionPath"
}

if ($JobNumber -notmatch '^\d{5}$') {
    throw "JobNumber '$JobNumber' does not match the observed 5-digit pattern (e.g. 26046)"
}

$targetName = "$JobNumber - $JobTitle"
$target = Join-Path $regionPath $targetName

# Duplicate protection. The job number must not already be in use anywhere the
# job could have moved to: the live region folder, that region's own lifecycle
# subfolders (HANDED OVER / ARCHIVE-HANDED OVER / CANCELLED - about 730 job
# folders sit in these), or the top-level COMPLETED / CANCELLED CONTRACTS.
#
# Folder names vary around the separator on this drive - "26003- LOT",
# "16001 -LOT", "26049 - LOT" all exist - so match on the leading 5 digits and
# never on "<number> - ", which silently misses the variants.
$searchRoots = [System.Collections.Generic.List[string]]::new()
$searchRoots.Add($regionPath)

# The region's non-job subfolders are its lifecycle/archive folders.
Get-ChildItem -LiteralPath $regionPath -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch '^\d{5}' } |
    ForEach-Object { $searchRoots.Add($_.FullName) }

foreach ($lifecycle in 'COMPLETED CONTRACTS', 'CANCELLED CONTRACTS') {
    $lifecyclePath = Join-Path $ProjectsRoot $lifecycle
    if (Test-Path -LiteralPath $lifecyclePath) { $searchRoots.Add($lifecyclePath) }
}

$clash = foreach ($root in $searchRoots) {
    Get-ChildItem -LiteralPath $root -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^$JobNumber(?!\d)" }
}
if ($clash) {
    $where = ($clash | ForEach-Object { $_.FullName }) -join "`n  "
    throw "Refusing: job number $JobNumber already exists ->`n  $where"
}

$items = Get-ChildItem -LiteralPath $master -Recurse
$dirs  = ($items | Where-Object PSIsContainer).Count
$files = ($items | Where-Object { -not $_.PSIsContainer }).Count
Write-Host "Template : $master"
Write-Host "Target   : $target"
Write-Host "Contents : $dirs folders, $files seeded template files"

if (-not $Commit) {
    Write-Host "`nDRY RUN - nothing created. Folders that would be created:" -ForegroundColor Yellow
    $items | Where-Object PSIsContainer | ForEach-Object {
        Write-Host ("  " + $_.FullName.Substring($master.Length + 1))
    }
    Write-Host "Re-run with -Commit (requires interactive confirmation) to create."
    exit 0
}

$answer = Read-Host "Create '$targetName' in $Region ? Type the job number ($JobNumber) to confirm"
if ($answer -ne $JobNumber) {
    Write-Host 'Not confirmed - nothing created.'
    exit 1
}

Copy-Item -LiteralPath $master -Destination $target -Recurse
$made = (Get-ChildItem -LiteralPath $target -Recurse | Measure-Object).Count
Write-Host "Created $target ($made items copied)." -ForegroundColor Green
Write-Host 'Verify in Explorer, then record the folder in the job record.'
