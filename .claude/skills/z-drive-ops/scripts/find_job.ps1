<#
Find job folders anywhere under Z:\PROJECTS - live regions, the in-region
lifecycle folders (HANDED OVER, ARCHIVE-HANDED OVER, CANCELLED), and the
top-level COMPLETED CONTRACTS / CANCELLED CONTRACTS. About 78% of jobs are NOT
in a live region folder, so a region-level look alone misses most of them.

    pwsh find_job.ps1 26049
    pwsh find_job.ps1 "lot 13 zhang"
    pwsh find_job.ps1 "pioneer close" -Region TAMWORTH

Matching: every word must appear in the folder name (case-insensitive). A
5-digit term also matches on the leading job number alone, because real names
vary around the dash ("26003- LOT", "16001 -LOT"). Read-only; prints full
paths for pasting into Explorer.
#>
param(
    [Parameter(Mandatory)] [string]$Term,
    [string]$Region
)

$ErrorActionPreference = 'Stop'
$projects = 'Z:\PROJECTS'
if (-not (Test-Path -LiteralPath $projects)) {
    Write-Error "Z:\PROJECTS is not reachable - is the Z: drive mapped in this session?"
}

$words = @($Term.ToLower() -split '[\s,]+' | Where-Object { $_ })
$lifecycle = 'CANCELLED', 'HANDED OVER', 'ARCHIVE-HANDED OVER', 'COMPLETED CONTRACTS'

$tops = Get-ChildItem -LiteralPath $projects -Directory
if ($Region) { $tops = $tops | Where-Object { $_.Name -ieq $Region -or $_.Name -in 'COMPLETED CONTRACTS', 'CANCELLED CONTRACTS' } }

$candidates = foreach ($top in $tops) {
    foreach ($child in (Get-ChildItem -LiteralPath $top.FullName -Directory -ErrorAction SilentlyContinue)) {
        $child
        if ($child.Name -in $lifecycle) {
            Get-ChildItem -LiteralPath $child.FullName -Directory -ErrorAction SilentlyContinue
        }
    }
}

$hits = foreach ($c in $candidates) {
    $name = $c.Name.ToLower()
    $all = $true
    foreach ($w in $words) { if (-not $name.Contains($w)) { $all = $false; break } }
    # a bare job number also matches on the leading five digits
    if (-not $all -and $words.Count -eq 1 -and $words[0] -match '^\d{5}$' -and $name -match "^$($words[0])\D") { $all = $true }
    if ($all) { $c }
}

$hits = @($hits | Sort-Object FullName -Unique)
if (-not $hits) {
    Write-Host "No job folder matches '$Term'."
    Write-Host "Try fewer words - folder names vary (brackets, extra spaces, estate names)."
    exit 1
}

Write-Host "$($hits.Count) match(es) for '$Term':`n"
foreach ($h in $hits) {
    $tag = if ($h.FullName -imatch 'CANCELLED') { '  [CANCELLED]' } else { '' }
    Write-Host "$($h.FullName)$tag"
}
