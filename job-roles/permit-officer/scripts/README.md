# Scripts — Permit Officer

Stdlib-only Python (no third-party packages on the server), mirroring the
contract-admin scripts convention — except `osc_snapshot.py`, which borrows
the OSC MCP server's virtual environment for its HTTP client. All read-only
against business files and OSC; outputs go to `runtime\permit-officer\` only.

| Script | Purpose |
|---|---|
| `xlsx_min.py` | Minimal stdlib `.xlsx` reader + multi-sheet writer (no openpyxl on the server). Reading never modifies a workbook. |
| `osc_snapshot.py` | Snapshot step: one JSON per pilot job (job, activities, alerts, documents) from the **production** OnSite Companion, GET only, through the `osc_mcp` client the MCP server uses. Runs under `shared\mcp\osc-api\.venv\Scripts\python.exe` (needs `httpx`); refuses a stale copy; writes only under `runtime\`. |
| `ba_report_parse.py` | Weekly BA report → row model. Columns are located **by header text** (the export gained five columns on 28 Sep 2026); unknown columns are carried verbatim; "Submit all RFI Items" is required. Reads the "PENDING …" / "RESOLVED …" item list, the v0.3 **Items** sheet (per-item values, one row per item, matched by Job No. + Item) and, for older drafts, the v0.2 L–O columns. `officer_edits()` compares a draft as the officer left it with the draft as written. |
| `ba_report_draft.py` | Deterministic Monday draft (v0.4): last week's report + per-job OSC snapshot JSONs → draft workbook (main sheet = the base's columns exactly; Items sheet = one row per item) + evidence bundle. Per item: Assigned to, Date submitted, Date resolved, Days outstanding in NSW business days, YELLOW/RED by tier (`TIERS`, `ASSIGNEE_TIER`, PO-11a) or the item's own limit (PO-11b); engineering and covenant also tracked from their columns (`COLUMN_CYCLES`). Items resolve only on fresh evidence or the officer's Date resolved and show once as RESOLVED; everything uncertain is kept and flagged. `--edited` reads her Items-sheet changes from last week's draft; `--jobs` scopes the pilot. |
| `ba_weekly_run.py` | The Monday run in one command: finds her latest export in the archive (never an older one), copies her edited draft from the drop folder, snapshots OSC, drafts, delivers to the drop folder without overwriting a draft she may be editing, and keeps the delivered copy. `--dry-run`, `--restart LABEL` (week 1), `--force`. |
| `nsw_holidays.py` | NSW public holidays 2026–27 and `business_days()`; verify each new year before the first Monday run. |
| `compare_ba_report.py` | Pilot scorecard: AI draft vs the officer's real report for the same Monday → matched / missed / extra items per pilot job and the "% correctly pre-populated" headline (criterion 90 %). |
| `regress_ba_report.py` | Regression over synthetic fixtures (fake jobs/names only). Run after any change to the scripts above. |

Run mechanics are in `../workflows/ba-weekly-report.md` (§How to run).
