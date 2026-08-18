# Convert PDF(s) to .docx via Word's own PDF reflow, headless over COM.
#
#   pwsh pdf_to_docx.ps1 -Pdf a.pdf,b.pdf -Out a.docx,b.docx
#
# The same conversion a person gets from File > Open > PDF in Word. Needs
# HKCU:\...\Word\Options\DisableConvertPdfWarning = 1 (set 17 Aug 2026) or a
# headless session hangs on the "convert this PDF" notice.
#
# Reflow re-typesets: text survives at ~95%+ but pagination, tables and
# checkbox/initial blocks drift (trial-report.md, 17 Aug 2026). A conversion
# is therefore a CANDIDATE INPUT for repair + verification
# (pdf_docx_fidelity.py) and MCR approval - never a template by itself.
param(
    [Parameter(Mandatory)][string[]]$Pdf,
    [Parameter(Mandatory)][string[]]$Out,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
if ($Pdf.Count -ne $Out.Count) { throw "Pdf and Out counts differ" }
foreach ($o in $Out) {
    if ((Test-Path $o) -and -not $Force) { throw "exists (use -Force): $o" }
}
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0   # wdAlertsNone
try {
    for ($i = 0; $i -lt $Pdf.Count; $i++) {
        $src = (Resolve-Path $Pdf[$i]).Path
        $dst = [System.IO.Path]::GetFullPath($Out[$i])
        $t = [Diagnostics.Stopwatch]::StartNew()
        # Open(FileName, ConfirmConversions:=$false, ReadOnly:=$true)
        $doc = $word.Documents.Open($src, $false, $true)
        $doc.SaveAs2($dst, 16)   # wdFormatXMLDocument
        $pages = $doc.ComputeStatistics(2)  # wdStatisticPages
        $words = $doc.ComputeStatistics(0)  # wdStatisticWords
        $doc.Close($false)
        "{0}  ->  {1}   ({2}pp, {3} words, {4:n1}s)" -f `
            [IO.Path]::GetFileName($src), [IO.Path]::GetFileName($dst), `
            $pages, $words, $t.Elapsed.TotalSeconds
    }
}
finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
