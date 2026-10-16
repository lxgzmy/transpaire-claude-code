<#
.SYNOPSIS
  Create production.env for the osc-api-prod MCP server, then run the read-only check.

.DESCRIPTION
  Asks for the production OSC API settings and writes them into production.env
  (git-ignored) using production.env.example as the template. The secret is
  typed hidden and never printed. Run this yourself in a PowerShell 7 terminal;
  never paste these values into a chat, a document or a commit.

  Afterwards it runs `python -m osc_mcp.selftest`, which only reads: environment,
  granted scope, the live-data check, the intake lookups and, with -CheckJob, one
  job by contract number. No secret or host name is printed.

.PARAMETER Path
  Where to write the file. Default: production.env beside this script. Before the
  PR is merged, point it at the server checkout:
  "Z:\CLAUDE CODE\transpire-claude-code\shared\mcp\osc-api\production.env"

.PARAMETER CheckJob
  Optional contract number for the read-only check, e.g. 26032.

.PARAMETER Force
  Replace an existing file.
#>
param(
    [string]$Path = (Join-Path $PSScriptRoot 'production.env'),
    [string]$CheckJob = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if ((Test-Path -LiteralPath $Path) -and -not $Force) {
    throw "$Path already exists. Run again with -Force to replace it."
}

$baseUrl = (Read-Host 'Production OSC API address (https://host:port)').Trim()
if ($baseUrl -notmatch '^https://[^\s/]+') { throw 'The address must start with https:// and name the host.' }
$specUrl = (Read-Host 'Production OpenAPI spec URL (leave blank to skip)').Trim()
$clientId = (Read-Host 'Production client ID').Trim()
$secure = Read-Host 'Production client secret (typed hidden)' -AsSecureString
$secret = [System.Net.NetworkCredential]::new('', $secure).Password
if (-not $clientId -or -not $secret) { throw 'Both the client ID and the secret are needed.' }

$values = @{
    'OSC_BASE_URL'      = $baseUrl.TrimEnd('/')
    'OSC_SWAGGER_URL'   = $specUrl
    'OSC_CLIENT_ID'     = $clientId
    'OSC_CLIENT_SECRET' = $secret
}
$template = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'production.env.example')
$lines = foreach ($line in $template) {
    $key = ($line -split '=', 2)[0]
    if ($values.ContainsKey($key)) { "$key=$($values[$key])" } else { $line }
}
Set-Content -LiteralPath $Path -Value $lines -Encoding utf8NoBOM
$secret = $null
$values = $null
Write-Host "Saved $Path (git-ignored). Running the read-only check..."

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = 'Z:\CLAUDE CODE\transpire-claude-code\shared\mcp\osc-api\.venv\Scripts\python.exe'
}
$env:OSC_ENV_FILE = $Path
$env:PYTHONPATH = $PSScriptRoot
try {
    if ($CheckJob) { & $python -m osc_mcp.selftest $CheckJob } else { & $python -m osc_mcp.selftest }
    if ($LASTEXITCODE -eq 0) { Write-Host 'Read-only check passed.' }
    else { Write-Host "Read-only check did not pass (exit $LASTEXITCODE). Nothing was written to OSC." }
}
finally {
    Remove-Item Env:OSC_ENV_FILE, Env:PYTHONPATH -ErrorAction SilentlyContinue
}
