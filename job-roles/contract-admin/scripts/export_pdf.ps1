<#
Export .docx files to PDF the way a contract administrator does it in Word:
Save As / Export to PDF, same base name, same folder (CD-7.4 - every completed
job keeps the .docx and its .pdf export side by side).

    pwsh export_pdf.ps1 -Docx "<file.docx>"                      # <file>.pdf beside it
    pwsh export_pdf.ps1 -Docx "<file.docx>" -Out "<other.pdf>"   # explicit destination
    pwsh export_pdf.ps1 -Docx "<file.docx>" -Out p1.pdf -From 1 -To 1   # page range (previews)
    pwsh export_pdf.ps1 -Docx a.docx,b.docx -Out a.pdf,b.pdf     # batch: ONE Word instance

Word start-up dominates the cost of an export (several seconds per launch), so
a run that needs more than one PDF should pass them all in one call - the batch
form opens Word once and exports each pair in turn. -From/-To apply to every
document in the batch, so page-range previews stay a single-document call.

Requires Word on the machine (COM automation). Refuses to overwrite an existing
PDF unless -Force is given - superseded versions move to SS\, they are not
replaced (CD-7.3).
#>
param(
    [Parameter(Mandatory)] [string[]]$Docx,
    [string[]]$Out = @(),
    [int]$From = 0,
    [int]$To = 0,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if ($Out.Count -gt 0 -and $Out.Count -ne $Docx.Count) {
    Write-Error "-Out must be omitted or give one destination per -Docx ($($Docx.Count) given, $($Out.Count) outs)"
}

# Resolve and validate every pair BEFORE Word starts, so a bad path or an
# overwrite refusal costs nothing.
$jobs = for ($i = 0; $i -lt $Docx.Count; $i++) {
    $src = (Resolve-Path -LiteralPath $Docx[$i]).Path
    $dst = if ($Out.Count -gt 0 -and $Out[$i]) { $Out[$i] }
           else { [System.IO.Path]::ChangeExtension($src, '.pdf') }
    if (-not [System.IO.Path]::IsPathRooted($dst)) {
        $dst = Join-Path (Get-Location).Path $dst
    }
    $dst = [System.IO.Path]::GetFullPath($dst)
    $outDir = Split-Path -Parent $dst
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Force $outDir | Out-Null
    }
    if ((Test-Path -LiteralPath $dst) -and -not $Force) {
        Write-Error "Refusing to overwrite existing $dst (use -Force only for scratch copies)"
    }
    [pscustomobject]@{ Src = $src; Dst = $dst }
}

$word = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $wdExportFormatPDF = 17
    $wdExportOptimizeForPrint = 0
    $wdExportAllDocument = 0
    $wdExportFromTo = 3

    foreach ($job in $jobs) {
        $doc = $null
        try {
            $doc = $word.Documents.Open($job.Src, $false, $true)   # no conversion dialog, read-only
            if ($From -gt 0 -and $To -ge $From) {
                $doc.ExportAsFixedFormat($job.Dst, $wdExportFormatPDF, $false,
                    $wdExportOptimizeForPrint, $wdExportFromTo, $From, $To)
            } else {
                $doc.ExportAsFixedFormat($job.Dst, $wdExportFormatPDF, $false,
                    $wdExportOptimizeForPrint, $wdExportAllDocument)
            }
            Write-Host "written : $($job.Dst)"
        }
        finally {
            if ($doc) { $doc.Close($false); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null }
        }
    }
}
finally {
    if ($word) { $word.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
}
