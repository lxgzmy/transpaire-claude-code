# Scripts — Permit Officer

Stdlib-only Python (no third-party packages on the server), mirroring the
contract-admin scripts convention. All read-only against business files;
outputs go to `runtime\permit-officer\` only.

| Script | Purpose |
|---|---|
| `xlsx_min.py` | Minimal stdlib `.xlsx` reader + single-sheet writer (no openpyxl on the server). Reading never modifies a workbook. |
| `ba_report_parse.py` | Weekly BA report export → row model (columns, date serials, the "PENDING …" item list in column G). |
| `ba_report_draft.py` | Deterministic Monday draft: last week's report + per-job OSC snapshot JSONs → draft workbook + evidence bundle + ageing (first-seen state persisted). Items drop only on fresh evidence; everything uncertain is kept and flagged. |
| `regress_ba_report.py` | Regression over synthetic fixtures (fake jobs/names only). Run after any change to the two scripts above. |

Run mechanics are in `../workflows/ba-weekly-report.md` (§How to run).
