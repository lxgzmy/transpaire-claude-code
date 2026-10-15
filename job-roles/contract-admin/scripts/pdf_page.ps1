<#
Render PDF pages to PNG with Windows' own PDF renderer (Windows.Data.Pdf).

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File pdf_page.ps1 -Pdf <file.pdf> -Pages 1[,2] -OutDir <dir> [-Scale 1.5] [-Crop "x0,y0,x1,y1"] [-Prefix p]

The one script here that runs under Windows PowerShell 5.1 (powershell.exe),
not PowerShell 7: the Windows.Data.Pdf projection exists only in Windows
PowerShell. There is no other rasteriser on this server (no poppler, no
Ghostscript), and the CAD plan sets carry their drawings as vector art, so
reading a site plan - which street a corner block's driveway uses, which side
the garage is on (CD-2.9, issue #59) - means looking at a rendered page.

-Pages   1-based page numbers, comma-separated.
-Scale   page size in DIPs x Scale (an A3 sheet at 1.5 is about 2400 px wide).
-Crop    a part of the page as fractions of its width and height, e.g.
         "0.4,0.3,0.8,0.7" - rendered at -Scale, then cut out, to zoom on a
         driveway.
-OutDir  must sit under the checkout's runtime\ folder (plans carry client
         names; runtime\ is git-ignored) and never on C:. Created if missing.

Writes <OutDir>\<Prefix><page>.png (default p1.png ...) and prints each path.
#>
param(
    [Parameter(Mandatory)] [string]$Pdf,
    [Parameter(Mandatory)] [string]$Pages,
    [Parameter(Mandatory)] [string]$OutDir,
    [double]$Scale = 1.5,
    [string]$Crop,
    [string]$Prefix = 'p'
)
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSEdition -ne 'Desktop') {
    throw "run pdf_page.ps1 with powershell.exe (Windows PowerShell 5.1): Windows.Data.Pdf is not available in PowerShell 7"
}

$src = (Resolve-Path -LiteralPath $Pdf).Path
$runtime = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\runtime'))
$dest = [System.IO.Path]::GetFullPath($OutDir)
if ($dest.StartsWith('C:', [System.StringComparison]::OrdinalIgnoreCase) -or
    -not $dest.StartsWith($runtime, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutDir must be under $runtime (git-ignored, never C:) - got $dest"
}
if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }

$box = $null
if ($Crop) {
    $box = @($Crop.Split([char]44) | ForEach-Object { [double]$_ })
    if ($box.Count -ne 4 -or $box[0] -lt 0 -or $box[1] -lt 0 -or $box[2] -gt 1 -or $box[3] -gt 1 -or
        $box[0] -ge $box[2] -or $box[1] -ge $box[3]) {
        throw "-Crop takes x0,y0,x1,y1 as fractions of the page, 0 <= x0 < x1 <= 1 - got $Crop"
    }
    Add-Type -AssemblyName System.Drawing
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
# WinRT async calls, awaited through the .NET AsTask bridge
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }
function AwaitAction($op) { $task = $asTaskAction.Invoke($null, @($op)); $task.Wait(-1) | Out-Null }

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($src)) ([Windows.Storage.StorageFile])
$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$folder = Await ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($dest)) ([Windows.Storage.StorageFolder])
Write-Output ("pages: " + $doc.PageCount)

foreach ($p in $Pages.Split([char]44)) {
    $n = [int]$p.Trim()
    if ($n -lt 1 -or $n -gt $doc.PageCount) { throw "page $n is not in this PDF (1-$($doc.PageCount))" }
    $page = $doc.GetPage([uint32]($n - 1))
    $name = "$Prefix$n.png"
    $stream = $null
    try {
        $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
        $opts.DestinationWidth = [uint32]($page.Size.Width * $Scale)
        $opts.DestinationHeight = [uint32]($page.Size.Height * $Scale)
        $target = Await ($folder.CreateFileAsync($name, [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
        $stream = Await ($target.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
        AwaitAction ($page.RenderToStreamAsync($stream, $opts))
    }
    finally {
        if ($stream) { $stream.Dispose() }
        $page.Dispose()
    }
    $out = Join-Path $dest $name
    if ($box) {
        # cut the requested part out of the full render (System.Drawing; the
        # file is read into memory first so it can be overwritten)
        $bytes = [System.IO.File]::ReadAllBytes($out)
        $ms = New-Object System.IO.MemoryStream(, $bytes)
        $full = [System.Drawing.Bitmap]::FromStream($ms)
        try {
            $rect = New-Object System.Drawing.Rectangle(
                [int]($box[0] * $full.Width), [int]($box[1] * $full.Height),
                [int](($box[2] - $box[0]) * $full.Width), [int](($box[3] - $box[1]) * $full.Height))
            $part = $full.Clone($rect, $full.PixelFormat)
            try { $part.Save($out, [System.Drawing.Imaging.ImageFormat]::Png) } finally { $part.Dispose() }
        }
        finally { $full.Dispose(); $ms.Dispose() }
    }
    Write-Output ("page $n -> $out")
}
