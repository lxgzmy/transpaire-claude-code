<#
Export a .docx to PDF the way a contract administrator does it in Word:
Save As / Export to PDF, same base name, same folder (CD-7.4 - every completed
job keeps the .docx and its .pdf export side by side).

    pwsh export_pdf.ps1 -Docx "<file.docx>"                      # <file>.pdf beside it
    pwsh export_pdf.ps1 -Docx "<file.docx>" -Out "<other.pdf>"   # explicit destination
    pwsh export_pdf.ps1 -Docx "<file.docx>" -Out p1.pdf -From 1 -To 1   # page range (previews)

Requires Word on the machine (COM automation). Refuses to overwrite an existing
PDF unless -Force is given - superseded versions move to SS\, they are not
replaced (CD-7.3).
#>
param(
    [Parameter(Mandatory)] [string]$Docx,
    [string]$Out,
    [int]$From = 0,
    [int]$To = 0,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$src = (Resolve-Path -LiteralPath $Docx).Path
if (-not $Out) { $Out = [System.IO.Path]::ChangeExtension($src, '.pdf') }
if (-not [System.IO.Path]::IsPathRooted($Out)) {
    $Out = Join-Path (Get-Location).Path $Out
}
$Out = [System.IO.Path]::GetFullPath($Out)
$outDir = Split-Path -Parent $Out
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Force $outDir | Out-Null
}
if ((Test-Path -LiteralPath $Out) -and -not $Force) {
    Write-Error "Refusing to overwrite existing $Out (use -Force only for scratch copies)"
}

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($src, $false, $true)   # no conversion dialog, read-only

    $wdExportFormatPDF = 17
    $wdExportOptimizeForPrint = 0
    $wdExportAllDocument = 0
    $wdExportFromTo = 3

    if ($From -gt 0 -and $To -ge $From) {
        $doc.ExportAsFixedFormat($Out, $wdExportFormatPDF, $false,
            $wdExportOptimizeForPrint, $wdExportFromTo, $From, $To)
    } else {
        $doc.ExportAsFixedFormat($Out, $wdExportFormatPDF, $false,
            $wdExportOptimizeForPrint, $wdExportAllDocument)
    }
    Write-Host "written : $Out"
}
finally {
    if ($doc) { $doc.Close($false); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null }
    if ($word) { $word.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
}
