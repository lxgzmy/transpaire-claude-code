<#
Word automation helpers shared by word_layout.ps1 and export_pdf.ps1 (dot-sourced).

Start-Word   a new, hidden Word with alerts off, remembering the WINWORD process it started.
Stop-Word    quits that Word without saving and makes sure the process has gone: a Quit that
             Word refuses while still busy used to be swallowed, and the hidden Word stayed
             running after the script ended (two orphans on 15 Oct 2026, one beside the next
             run's Word). Only the process this script started is ever stopped - never another
             person's Word, and nothing when it cannot tell which process is its own.
Drive-Path   a \\server\share\... path mapped back to the drive letter it is mounted on: Word
             opens a UNC path in Protected View and Documents.Open returns nothing.
#>

$script:WordPid = 0

function Start-Word {
    $before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $w = New-Object -ComObject Word.Application
    $new = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id } | Where-Object { $_ -notin $before })
    # one new process is ours; two (someone else's Word started the same moment) and we cannot tell
    $script:WordPid = $(if ($new.Count -eq 1) { $new[0] } else { 0 })
    $w.Visible = $false
    $w.DisplayAlerts = 0
    return $w
}

function Stop-Word($w) {
    if ($w) {
        try { $w.NormalTemplate.Saved = $true } catch { }   # never a "save Normal.dotm?" prompt
        for ($i = 0; $i -lt 3; $i++) {
            try { $w.Quit(0); break } catch { Start-Sleep -Milliseconds 700 }   # 0 = wdDoNotSaveChanges
        }
        try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) } catch { }
    }
    if ($script:WordPid) {
        $p = Get-Process -Id $script:WordPid -ErrorAction SilentlyContinue
        if ($p -and $p.ProcessName -eq 'WINWORD' -and -not $p.WaitForExit(15000)) {
            Stop-Process -Id $script:WordPid -Force -ErrorAction SilentlyContinue
        }
        $script:WordPid = 0
    }
}

function Drive-Path([string]$path) {
    # Resolve-Path gives a UNC path as "Microsoft.PowerShell.Core\FileSystem::\\server\share\...",
    # which no drive root starts with - the prefix goes first
    $prefix = 'Microsoft.PowerShell.Core\FileSystem::'
    if ($path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) { $path = $path.Substring($prefix.Length) }
    if (-not $path.StartsWith([string][char]92 + [string][char]92)) { return $path }
    foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
        if ($d.DisplayRoot -and $path.StartsWith($d.DisplayRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $d.Root.TrimEnd([char]92) + $path.Substring($d.DisplayRoot.Length)
        }
    }
    return $path
}
