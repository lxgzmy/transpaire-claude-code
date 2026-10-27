# Weekly BA report — agreed layout (v0.3)

The synthetic workbook the regression builds (`scripts/regress_ba_report.py`,
fake jobs 9xxxx only) is the fixture; this note records the agreed shape so
nobody has to open a real report to see it. Real reports never enter the
repo.

## Main sheet: the OSC export, column for column

The export is the officer's Executive Reporter definition and it changes
without notice (28 Sep 2026: five columns added, "Submit all RFI Items"
moved from G to L). The pipeline therefore locates columns **by header
text**, never by letter, and the draft reproduces whatever columns the base
has, in the base's order, under the base's sheet name. Known headers:

| Header | Content | Used by the drafter |
|---|---|---|
| Job No. | contract number | key; the cell takes the row's worst-item colour |
| Marketer | text | carried |
| Job Address | text | carried |
| Submit for BA | date | filled from the OSC activity when blank |
| Received RFI | date, or text ("AWAITING RFI") | filled from OSC when blank |
| Received Covenant Approval | date | filled from OSC when blank |
| Submit all RFI Items | date when complete; while in flight `PENDING A (STATE), B (W/O X)` in red bold, plus an optional second line `RESOLVED C (dd/mm/yyyy)` for items closed since the last report | **required**; the outstanding-items cell |
| BA Received | date | filled from OSC when blank |
| Deposit Paid | date | filled from OSC when blank |
| Nominate Site Start | date | filled from OSC when blank |
| Site Start (Physical) | date | carried |
| *anything else* (since 28 Sep 2026: Engineering Ordered, Receive Engineering, Review Engineering - Michael, Forward Engineering to Certifier, Covenant Ordered) | date-time serial or text ("PENDING REVIEW") | carried verbatim, listed in the evidence note; the engineering and covenant columns are also aged on the Items sheet (PO-11b) |

A workbook without a "Submit all RFI Items" header is refused outright.
Date cells are written as Excel serials with a `dd/mm/yyyy` format; text
stays text.

## Items sheet: one row per outstanding item

Per-item values (PO-11a) live on a second sheet named **Items**, which the
draft writes and the officer corrects. v0.2 put them in four main-sheet
columns L–O with one line per item; in practice the officer's edits there
could not be read back (shifted headers, multi-line cells), so v0.3 moved
them to their own rows.

| Col | Header | Content |
|---|---|---|
| A | Job No. | contract number (matches a main-sheet row) |
| B | Item | the item name as it appears in the PENDING list (without the parenthetical state) |
| C | Assigned to | who it is with; `⚠ ` prefix = low confidence, `?` = unknown |
| D | Date submitted | `dd/mm/yyyy` |
| E | Date resolved | `dd/mm/yyyy`, blank while open; the officer typing one closes the item |
| F | Days outstanding | NSW business days (a number); blank while not yet submitted |
| G | Flag | `YELLOW`, `RED`, `NOT SUBMITTED` or `RESOLVED` |
| H | Notes | **the officer's own**: carried week to week exactly as she typed it, until she changes or clears it |
| I | Draft notes | the draft's: why the row needs eyes ("date submitted assumed — please correct", "verify"), the evidence, the item's limit; rewritten every run |

Rows are in main-sheet order: pending items first (in PENDING order), then
engineering and covenant when they are tracked from their columns but not
on the RFI list (PO-11b), then the items resolved this cycle. Non-pilot jobs
have no rows. The header row stays in view while scrolling (frozen).

The officer's base is a plain export with no Items sheet, so her changes
are read from **last week's draft as she left it** (`--edited`), compared
cell by cell with the same draft as delivered (`outputs\delivered\`): a new
*Assigned to*, a typed *Date submitted* (an emptied one means not yet
submitted), a *Date resolved*, and her *Notes*. A date typed as 12.10.2026,
12-10-2026 or 12/10/26 is read; one that cannot be read ("TBC") is reported
and not used, never taken as emptied. Rows are matched by **Job No. + Item**
(names compared after dropping the parenthetical and punctuation,
case-insensitively); failing that, by evidence family only for a genuine
rename (a similar name that is new this week, "SEW EJECTION" to "SEWER
EJECTION"), and a rename never carries her *Date resolved*. A change to an
item that has since left her report, or whose list has closed, is noted, not
used. Officer-typed values win and stick from then on; they follow the item
when a second item of its family joins or leaves the list, and a resolved
engineering or covenant cycle stays closed until a newer step is dated. On the 22.10.2026 draft, the first she edited, Notes
held the draft's text too; her own words are taken out of it once.

A base that does carry an Items sheet (an officer-edited draft filed as the
base) is still read the old way: an Items row that matches nothing in that
job's PENDING list is **not used** and is flagged in the evidence note — to
add an item, add it to the PENDING list on the main sheet.

Older v0.2 drafts (L–O on the main sheet) are still read with the old
one-line-per-item rule when those four headers are present; a draft built
from such a base drops the L–O columns and writes the Items sheet instead.

## Fills

- **Yellow / red** on an Items row = that item's own flag (PO-11a tiers).
- **Yellow / red** on the main sheet's Job No. cell = the worst *open* item
  on the row (row-level colour, confirmed by the officer on #29).
- **Light grey** = no age fill applies but the item is low confidence
  (`⚠`); on the Items sheet the Notes cell carries it.
- **Red bold text** in "Submit all RFI Items" = the pending list, as the
  officer types it today.
