<#
Layout measurement and correction for the Sydney inclusions document, through
Word itself (COM automation - the same Word that exports the PDFs).

    pwsh word_layout.ps1 -Mode measure -Docx <blank.docx> -Out <measure.json>
    pwsh word_layout.ps1 -Mode align   -Docx <file.docx> -Plan <layout_plan.json> -Out <report.json> [-Save <aligned.docx>]
    pwsh word_layout.ps1 -Mode check   -Docx <file.docx> -Plan <layout_plan.json> -Out <report.json>

Why Word: the inclusions body is ONE table row with two cells. The left cell
holds the section headings and item labels, the right cell the wording, as two
independent text flows. A label sits level with its wording only because the
template's typist padded the left column with blank paragraphs by eye, and the
turnkey / upgraded headings start a page only because ~15 blank paragraphs sit
before each. Nothing in the XML says where a paragraph lands on the page - only
Word's layout engine knows - so the pass that keeps labels level after a
content edit has to ask Word.

measure (the BLANK, once per template, cached by draft_contract.py): every
paragraph of both body cells with page and vertical position - the raw material
layout_pairs.py turns into the label/wording pair map. Slow (every paragraph
is a COM round trip; minutes on this server), which is why it is cached.

align (every filled document): executes the plan edit_inclusions.py wrote.
Each planned paragraph is located with Word's own Find (one call) instead of
walking the whole cell, measured, and the left column padded or trimmed with
blank paragraphs (a fraction of a line as paragraph spacing) until the label
sits level with its wording within -Tolerance points; each package heading is
pushed to the top of its page. A verification pass then re-measures every
step, and the report carries the final delta per step, the anchor
x-positions (page-1 values, page-13 names and Date:), the page count and the
empty pages - everything gate_inclusions.py checks. Only blank paragraphs are
ever inserted or deleted, only inside the two body cells; text never changes.

check: the same report without changing anything.

Word constants: wdActiveEndPageNumber=3, wdHorizontalPositionRelativeToPage=5,
wdVerticalPositionRelativeToPage=6, wdGoToPage=1, wdGoToAbsolute=1, wdParagraph=4.
#>
param(
    [Parameter(Mandatory)] [ValidateSet('measure', 'align', 'check', 'anchors')] [string]$Mode,
    [Parameter(Mandatory)] [string]$Docx,
    [string]$Plan,
    [string]$Out,
    [string]$Save,
    [int]$BodyTable = 2,
    [double]$Tolerance = 1.5,
    [int]$MaxIter = 80
)

$ErrorActionPreference = 'Stop'
$wdPage = 3; $wdLeft = 5; $wdTop = 6
$script:T0 = Get-Date
function Say([string]$m) { Write-Host ("[{0,6:n1}s] {1}" -f ((Get-Date) - $script:T0).TotalSeconds, $m) }

$Anchors = @('Lot No. :', 'STREET :', 'SUBURB :', 'ESTATE :', 'PRICE :', 'HOUSE TYPE :', 'HOUSE SIZE :',
             'HOUSE FAÇADE :', 'GARAGE SIDE :', 'Name of Owner 1:', 'Name of Owner 2:', 'Builders Representative:',
             'INTERNAL TURNKEY PACKAGE', 'EXTERNAL TURNKEY PACKAGE', 'UPGRADED INCLUSIONS')

function Clean([string]$t) { return ($t -replace "[`r`a]+$", '') }
function Norm([string]$t) { return (($t -replace '\s+', ' ').Trim()) }

function Find-Runs($doc, $scope, [string]$needle) {
    # every paragraph Range in $scope (main story) that contains $needle, in order.
    # Word's Find is run from a COLLAPSED range at the current position: a
    # non-collapsed range that lies inside a table cell is silently widened to
    # the whole cell, so the search would keep returning the first hit.
    $hits = New-Object System.Collections.Generic.List[object]
    $scopeEnd = $scope.End
    $p = $scope.Start
    $text = $needle
    if ($text.Length -gt 200) { $text = $text.Substring(0, 200) }
    $guard = 0
    while ($guard -lt 80) {
        $guard++
        $rng = $doc.Range($p, $p)
        $f = $rng.Find
        $f.ClearFormatting()
        $ok = $f.Execute($text, $true, $false, $false, $false, $false, $true, 0, $false, '', 0)
        if (-not $ok) { break }
        if ($rng.Start -ge $scopeEnd) { break }
        $pr = $rng.Paragraphs.Item(1).Range
        if ($pr.Start -ge $scopeEnd) { break }
        $hits.Add($pr)
        if ($pr.End -ge $scopeEnd) { break }
        $p = $pr.End
    }
    return $hits
}

function Story-Ranges($doc) {
    # the main text plus every text box story (the page-13 signature block lives in a text box)
    $out = New-Object System.Collections.Generic.List[object]
    $out.Add($doc.Content)
    try {
        $st = $doc.StoryRanges.Item(5)   # wdTextFrameStory
        $guard = 0
        while ($st -ne $null -and $guard -lt 50) { $guard++; $out.Add($st); $st = $st.NextStoryRange }
    } catch { }
    return $out
}

function Needle([string]$want) {
    # the longest word of the text: the plan's texts are whitespace-normalised
    # but the document may carry double spaces ("1.  PRELIMINARY WORKS"), which
    # Word's Find would not match; a single word survives that, and every hit
    # is verified against the full normalised text anyway
    $best = ''
    foreach ($w in ($want -split ' ')) { if ($w.Length -gt $best.Length) { $best = $w } }
    return $(if ($best.Length -ge 3) { $best } else { $want })
}

function Find-Paragraph($doc, $scope, [string]$text, [int]$ordinal) {
    # the n-th paragraph in $scope whose normalised text equals $text (null when absent)
    $want = Norm $text
    $seen = 0
    foreach ($pr in (Find-Runs $doc $scope (Needle $want))) {
        if ((Norm (Clean $pr.Text)) -eq $want) {
            $seen++
            if ($seen -eq $ordinal) { return $pr }
        }
    }
    return $null
}

function Find-Paragraph-After($doc, $scope, [int]$from, [string]$text) {
    # the first paragraph after position $from (inside $scope) whose normalised text equals $text
    $want = Norm $text
    $sub = $doc.Range([math]::Max($from, $scope.Start), $scope.End)
    foreach ($pr in (Find-Runs $doc $sub (Needle $want))) {
        if ((Norm (Clean $pr.Text)) -eq $want) { return $pr }
    }
    return $null
}

function Pos($rng) { return @{ page = [int]$rng.Information($wdPage); top = [double]$rng.Information($wdTop) } }

function Adjust-Step($res, [double]$usable, [double]$lineH, [double]$tol, [int]$maxIter) {
    # pad / trim the left column (or push the right heading) until this step is
    # level or at page top; works on the live ranges kept in $res._lp / $res._rp
    $actions = @()
    $lp = $res._lp; $rp = $res._rp
    for ($iter = 0; $iter -lt $maxIter; $iter++) {
        if ($res.kind -eq 'pair') {
            $delta = (Flow (Pos $rp) $usable) - (Flow (Pos $lp) $usable)   # + : label sits above its wording
            if ([math]::Abs($delta) -le $tol) { break }
            $first = Block-First $lp
            if ($delta -gt 0) {
                $n = [math]::Floor($delta / $lineH)
                if ($n -ge 1) {
                    for ($k = 0; $k -lt $n; $k++) { $first.Range.InsertParagraphBefore() }
                    $actions += "left +$n"
                } else { $first.SpaceBefore = [double]$first.SpaceBefore + $delta; $actions += ("left space +{0:n1}" -f $delta) }
            } else {
                $sb = [double]$first.SpaceBefore
                $prev = $first.Previous(1)
                if ($sb -gt 0.05) { $cut = [math]::Min($sb, -$delta); $first.SpaceBefore = $sb - $cut; $actions += ("left space -{0:n1}" -f $cut) }
                elseif ($prev -ne $null -and (Is-Blank $prev)) { $prev.Range.Delete() | Out-Null; $actions += 'left -1' }
                else { $rp.Paragraphs.Item(1).Range.InsertParagraphBefore(); $actions += 'right +1' }
            }
            # InsertParagraphBefore grows the range to include the new blank: re-point at the text paragraph
            $lp = $lp.Paragraphs.Last.Range
            $rp = $rp.Paragraphs.Last.Range
        }
        else {  # page_top: the right-column heading must be first on its page
            $hp = Pos $rp
            $prev = Prev-Paragraph $rp
            if ($prev -eq $null) { break }
            $pp = Pos $prev.Range
            if ($pp.page -lt $hp.page) { break }
            # walk back over the blank spacers to the content before them
            $anchor = $prev; $blanks = 0
            while ($anchor -ne $null -and (Is-Blank $anchor)) { $blanks++; $anchor = $anchor.Previous(1) }
            $anchorPage = $(if ($anchor -eq $null) { 0 } else { (Pos $anchor.Range).page })
            if ($blanks -gt 0 -and $anchorPage -lt $hp.page) {
                # the content ends on the page before: the blank just above the
                # heading spilled onto its page - remove it, the heading moves up a line
                $prev.Range.Delete() | Out-Null; $actions += 'right -1'
            } else {
                # content shares the heading's page: push the heading to the next page
                $rp.Paragraphs.Item(1).Range.InsertParagraphBefore(); $actions += 'right +1'; $rp = $rp.Paragraphs.Last.Range
            }
        }
    }
    $res._lp = $lp; $res._rp = $rp
    return $actions
}

function Verify-Steps($results, [double]$usable, [double]$tol) {
    $off = 0
    foreach ($r in $results) {
        if ($r.status -eq 'NOT FOUND') { continue }
        $rpos = Pos $r._rp
        $r.right_page = $rpos.page
        if ($r.kind -eq 'pair') {
            $lpos = Pos $r._lp
            $r.left_page = $lpos.page
            $r.delta = [math]::Round((Flow $rpos $usable) - (Flow $lpos $usable), 2)
            $r.status = $(if ([math]::Abs($r.delta) -le $tol) { 'level' } else { 'OFF' })
        } else {
            $prev = Prev-Paragraph $r._rp
            $r.status = $(if ($prev -eq $null -or (Pos $prev.Range).page -lt $rpos.page) { 'page top' } else { 'NOT AT PAGE TOP' })
        }
        if ($r.status -notin @('level', 'page top')) { $off++ }
    }
    return $off
}
function Flow($p, $usable) { return $p.page * $usable + $p.top }

function Prev-Paragraph($rng) {
    $p = $rng.Paragraphs.Item(1).Previous(1)
    if ($p -eq $null) { return $null }
    return $p
}

function Is-Blank($para) { return ((Clean $para.Range.Text).Trim().Length -eq 0) }

function Block-First($rng) {
    # the label and any heading glued directly above it move together
    $cur = $rng.Paragraphs.Item(1)
    while ($true) {
        $prev = $cur.Previous(1)
        if ($prev -eq $null -or (Is-Blank $prev)) { return $cur }
        $cur = $prev
    }
}

function X-At($pr, $offset) {
    # x (pt from the page's left edge) of the character at $offset within paragraph range $pr, any story
    $rr = $pr.Duplicate
    $rr.SetRange($pr.Start + $offset, $pr.Start + $offset + 1)
    return [math]::Round([double]$rr.Information($wdLeft), 2)
}

function Measure-Anchors($doc) {
    $found = New-Object System.Collections.Generic.List[object]
    # main story only: Range.Information returns -1 inside text boxes, so the
    # page-13 signature lines (a text box) are checked structurally by
    # gate_inclusions.py from the XML instead
    foreach ($n in $Anchors) {
        foreach ($story in @($doc.Content)) {
            foreach ($pr in (Find-Runs $doc $story $n)) {
                $t = Clean $pr.Text
                if (-not $t.StartsWith($n)) { continue }
                $info = [ordered]@{ anchor = $n; story = 'main'
                                    text = $t.Substring(0, [math]::Min(90, $t.Length))
                                    page = [int]$pr.Information($wdPage); top = [math]::Round([double]$pr.Information($wdTop), 2)
                                    label_left = (X-At $pr 0) }
                if ($t.Length -gt $n.Length) { $info.after_label_left = (X-At $pr $n.Length) }
                if ($t.Length -gt $n.Length + 1) { $info.after_label1_left = (X-At $pr ($n.Length + 1)) }
                $after = $n.Length
                while ($after -lt $t.Length -and ($t[$after] -eq ' ' -or $t[$after] -eq "`t" -or $t[$after] -eq [char]0x2026 -or $t[$after] -eq '.')) { $after++ }
                if ($after -lt $t.Length) {
                    $info.value_left = (X-At $pr $after)
                    $info.value_text = $t.Substring($after, [math]::Min(30, $t.Length - $after))
                }
                $di = $t.IndexOf('Date:')
                if ($di -ge 0) { $info.date_left = (X-At $pr $di) }
                $found.Add([pscustomobject]$info)
            }
        }
    }
    return $found
}

function Get-EmptyPages($doc, $pages) {
    # a page is empty when neither its main-story text nor any text box anchored on it says anything
    $shapePages = @{}
    foreach ($sh in $doc.Shapes) {
        try {
            if ($sh.TextFrame.HasText -and ($sh.TextFrame.TextRange.Text -replace '[\s\a]', '').Length -gt 0) {
                $shapePages[[int]$sh.Anchor.Information($wdPage)] = $true
            }
        } catch { }
    }
    $empty = New-Object System.Collections.Generic.List[int]
    $sel = $doc.ActiveWindow.Selection
    for ($p = 1; $p -le $pages; $p++) {
        $sel.GoTo(1, 1, $p) | Out-Null
        $t = $doc.Bookmarks.Item('\page').Range.Text
        if (($t -replace '[\s\a]', '').Length -eq 0 -and -not $shapePages.ContainsKey($p)) { $empty.Add($p) }
    }
    return $empty
}

function Get-CellParas($cell) {
    # every paragraph of a cell: text, page and top - three COM calls per paragraph
    # (the cell's one Range.Text does not split back into paragraphs reliably)
    $out = New-Object System.Collections.Generic.List[object]
    $i = 0
    foreach ($p in $cell.Range.Paragraphs) {
        $r = $p.Range
        $out.Add([pscustomobject]@{
            i = $i; text = (Clean $r.Text)
            page = [int]$r.Information($wdPage); top = [math]::Round([double]$r.Information($wdTop), 2)
        })
        $i++
    }
    return $out
}

function Doc-Facts($doc) {
    $pages = [int]$doc.ComputeStatistics(2)
    $ps = $doc.Sections.Item(1).PageSetup
    return [ordered]@{
        pages = $pages; empty_pages = @(Get-EmptyPages $doc $pages)
        page_top = [math]::Round([double]$ps.TopMargin, 2)
        usable = [math]::Round([double]$ps.PageHeight - [double]$ps.TopMargin - [double]$ps.BottomMargin, 2)
        anchors = @(Measure-Anchors $doc)
    }
}

$word = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $src = (Resolve-Path -LiteralPath $Docx).Path
    if ($src.StartsWith([string][char]92 + [string][char]92)) {
        # a UNC path opens in Protected View and Documents.Open returns nothing;
        # map it back to the drive letter the share is mounted on
        foreach ($d in (Get-PSDrive -PSProvider FileSystem)) {
            if ($d.DisplayRoot -and $src.StartsWith($d.DisplayRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                $src = $d.Root.TrimEnd([char]92) + $src.Substring($d.DisplayRoot.Length); break
            }
        }
    }
    $doc = $word.Documents.Open($src, $false, ($Mode -ne 'align'))
    if ($doc -eq $null) { throw "Word did not open $src (Protected View or a lock on the file) - nothing measured" }
    Say "opened $([System.IO.Path]::GetFileName($src))"
    try {
        $tbl = $doc.Tables.Item($BodyTable)
        $lc = $tbl.Cell(1, 1); $rc = $tbl.Cell(1, 2)
        if ($Mode -eq 'anchors') {
            $facts = Doc-Facts $doc
            $m = [ordered]@{ docx = $doc.FullName } + $facts
            $json = $m | ConvertTo-Json -Depth 5 -Compress
            if ($Out) { [System.IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding $false)) } else { $json }
            Say "anchors: $($facts.anchors.Count), pages $($facts.pages), empty $($facts.empty_pages -join ',')"
        }
        elseif ($Mode -eq 'measure') {
            $left = Get-CellParas $lc;  Say "  left cell: $($left.Count) paragraphs"
            $right = Get-CellParas $rc; Say "  right cell: $($right.Count) paragraphs"
            $facts = Doc-Facts $doc;    Say "  pages $($facts.pages), empty $($facts.empty_pages -join ','), anchors $($facts.anchors.Count)"
            $m = [ordered]@{ docx = $doc.FullName } + $facts + [ordered]@{ left = $left; right = $right }
            $json = $m | ConvertTo-Json -Depth 5 -Compress
            if ($Out) { [System.IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding $false)) } else { $json }
            Say "measured"
        }
        else {
            if (-not $Plan) { throw "-Plan is required for $Mode" }
            # NOT $plan: PowerShell variables are case-insensitive and the [string]
            # parameter $Plan would coerce the parsed object back into a string
            $planObj = Get-Content -LiteralPath $Plan -Raw -Encoding UTF8 | ConvertFrom-Json
            $steps = @($planObj.steps)
            Say "plan: $($steps.Count) steps from $([System.IO.Path]::GetFileName($Plan))"
            $ps = $doc.Sections.Item(1).PageSetup
            $usable = [double]$ps.PageHeight - [double]$ps.TopMargin - [double]$ps.BottomMargin
            $lineH = 13.3
            $results = New-Object System.Collections.Generic.List[object]
            $stepNo = 0
            $lastL = -1; $lastR = -1   # end of the last located paragraph per column: steps run in document order
            foreach ($s in $steps) {
                $stepNo++
                $res = [ordered]@{ kind = $s.kind; left = $s.left; left_n = $s.left_n; right = $s.right; right_n = $s.right_n
                                   status = 'unresolved'; actions = ''; delta = $null; left_page = $null; right_page = $null }
                $rp = $null
                if ($lastR -ge 0) { $rp = Find-Paragraph-After $doc $rc.Range $lastR $s.right }
                if ($rp -eq $null) { $rp = Find-Paragraph $doc $rc.Range $s.right $s.right_n }
                $lp = $null
                if ($s.kind -eq 'pair') {
                    if ($lastL -ge 0) { $lp = Find-Paragraph-After $doc $lc.Range $lastL $s.left }
                    if ($lp -eq $null) { $lp = Find-Paragraph $doc $lc.Range $s.left $s.left_n }
                }
                if ($rp -ne $null) { $lastR = $rp.End }
                if ($lp -ne $null) { $lastL = $lp.End }
                if ($rp -eq $null -or ($s.kind -eq 'pair' -and $lp -eq $null)) {
                    $res.status = 'NOT FOUND'; $results.Add([pscustomobject]$res); continue
                }
                if ($lineH -eq 13.3 -and $lp -ne $null) {
                    # measure a blank line once: the paragraph before the first label, if blank
                    $pv = Prev-Paragraph $lp
                    if ($pv -ne $null -and (Is-Blank $pv)) {
                        $pp = $pv.Previous(1)
                        if ($pp -ne $null) {
                            $a = Pos $pp.Range; $b = Pos $pv.Range
                            if ($a.page -eq $b.page) { $d = $b.top - $a.top; if ($d -gt 8 -and $d -lt 20) { $lineH = $d } }
                        }
                    }
                }
                $res._lp = $lp; $res._rp = $rp
                $resObj = [pscustomobject]$res
                $iters = $(if ($Mode -eq 'check') { 0 } else { $MaxIter })
                $actions = @(Adjust-Step $resObj $usable $lineH $Tolerance $iters)
                $resObj.actions = ($actions -join ', ')
                $results.Add($resObj)
                if ($stepNo % 20 -eq 0) { Say "  step $stepNo/$($steps.Count)" }
            }
            Say "steps done - verifying"
            # verification pass: final positions after all edits; a later step's padding
            # can nudge an earlier pair, so anything still off gets another round (twice)
            $off = Verify-Steps $results $usable $Tolerance
            $round = 0
            while ($off -gt 0 -and $Mode -eq 'align' -and $round -lt 2) {
                $round++
                Say "  $off step(s) off after verification - correction round $round"
                foreach ($r in $results) {
                    if ($r.status -in @('OFF', 'NOT AT PAGE TOP')) {
                        $more = @(Adjust-Step $r $usable $lineH $Tolerance $MaxIter)
                        if ($more.Count) { $r.actions = (@($r.actions, ($more -join ', ')) | Where-Object { $_ }) -join ' | ' }
                    }
                }
                $off = Verify-Steps $results $usable $Tolerance
            }
            foreach ($r in $results) { $r.PSObject.Properties.Remove('_lp'); $r.PSObject.Properties.Remove('_rp') }
            if ($Mode -eq 'align') {
                $dst = if ($Save) { $Save } else { $src }
                if ($dst -ne $src) { $doc.SaveAs2($dst) } else { $doc.Save() }
            } else { $dst = $src }
            $facts = Doc-Facts $doc
            $report = [ordered]@{ docx = $dst; mode = $Mode; line_height = $lineH; tolerance = $Tolerance } + $facts + [ordered]@{ steps = $results }
            $json = $report | ConvertTo-Json -Depth 6 -Compress
            if ($Out) { [System.IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding $false)) } else { $json }
            $bad = @($results | Where-Object { $_.status -notin @('level', 'page top') }).Count
            Say "$Mode : $dst  ($($facts.pages) pages, empty $($facts.empty_pages -join ','); $($results.Count) steps, $bad not level)"
        }
    }
    catch {
        Write-Error ("word_layout.ps1 failed at " + $_.InvocationInfo.ScriptLineNumber + ": " + $_.Exception.Message + " | " + $_.InvocationInfo.Line.Trim())
        throw
    }
    finally {
        if ($doc) { try { $doc.Close($false) } catch { }; [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null }
    }
}
finally {
    if ($word) { try { $word.Quit() } catch { }; [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
}
