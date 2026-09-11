# Weekly BA report — agreed layout (v0.2, issue #29)

The synthetic workbook the regression builds (`scripts/regress_ba_report.py`,
fake jobs 9xxxx only) is the fixture; this note records the agreed shape so
nobody has to open a real report to see it. Real reports never enter the
repo.

## Sheet 1, header row 1, one row per job

| Col | Header | Content |
|---|---|---|
| A | Job No. | contract number |
| B | Marketer | text |
| C | Job Address | text |
| D | Submit for BA | date |
| E | Received RFI | date, or text ("AWAITING RFI") |
| F | Received Covenant Approval | date |
| G | Submit all RFI Items | date when complete; while in flight `PENDING A (STATE), B (W/O X)` in red bold, plus an optional second line `RESOLVED C (dd/mm/yyyy)` for items closed since the last report |
| H | BA Received | date |
| I | Deposit Paid | date |
| J | Nominate Site Start | date |
| K | Site Start (Physical) | date |
| L | Assigned to | one line per item, same order as G (pending first, then resolved); `⚠ ` prefix = low confidence, `?` = unknown |
| M | Date submitted | one line per item, `dd/mm/yyyy` |
| N | Date resolved | one line per item, `dd/mm/yyyy` or blank while open |
| O | Days outstanding | one line per item: `12 YELLOW`, `23 RED`, `5 YELLOW (assumed)`, `7 RESOLVED` |

A–K are the OSC Executive Reporter export exactly as today; the export
never has L–O. L–O appear on the AI draft and survive on the officer's
corrected copy. The drafter reads them back **only when each column has
exactly one line per item in G**; otherwise the row is flagged and the
officer's values are ignored for that week.

## Fills

- **Yellow / red** on L–O = the worst *open* item on the row (PO-11a tiers).
  Excel fills are per cell, so per-item colour is only possible on a
  one-row-per-item sheet — not built unless the owner asks (#29 q6).
- **Light grey** on L–O = no age fill applies but at least one item is low
  confidence (`⚠`).
- **Red bold text** in G = the pending list, as the officer types it today.
