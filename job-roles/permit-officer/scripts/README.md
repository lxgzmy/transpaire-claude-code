# Scripts — Permit Officer

Stdlib-only Python (no third-party packages on the server), mirroring the
contract-admin scripts convention. All read-only against business files;
outputs go to `runtime\permit-officer\` only.

| Script | Purpose |
|---|---|
| `xlsx_min.py` | Minimal stdlib `.xlsx` reader + single-sheet writer (no openpyxl on the server). Reading never modifies a workbook. |
| `ba_report_parse.py` | Weekly BA report → row model (columns A–K, date serials, the "PENDING …" / "RESOLVED …" item lists in column G, and the v0.2 per-item columns L–O when a corrected draft is the base). |
| `ba_report_draft.py` | Deterministic Monday draft (v0.2): last week's report + per-job OSC snapshot JSONs → draft workbook + evidence bundle. Per item: Assigned to, Date submitted, Date resolved, Days outstanding in NSW business days, YELLOW/RED by tier (`TIERS`, `ASSIGNEE_TIER`, PO-11a). Items resolve only on fresh evidence and show once as RESOLVED; everything uncertain is kept and flagged. `--jobs` scopes the pilot. |
| `nsw_holidays.py` | NSW public holidays 2026–27 and `business_days()`; verify each new year before the first Monday run. |
| `compare_ba_report.py` | Pilot scorecard: AI draft vs the officer's real report for the same Monday → matched / missed / extra items per pilot job and the "% correctly pre-populated" headline (criterion 90 %). |
| `regress_ba_report.py` | Regression over synthetic fixtures (fake jobs/names only). Run after any change to the scripts above. |

Run mechanics are in `../workflows/ba-weekly-report.md` (§How to run).
