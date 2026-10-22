# Scripts — Permit Officer

Stdlib-only Python (no third-party packages on the server), mirroring the
contract-admin scripts convention — except `osc_snapshot.py`, which borrows
the OSC MCP server's virtual environment for its HTTP client. All read-only
against business files and OSC; outputs go to `runtime\permit-officer\` only.

| Script | Purpose |
|---|---|
| `xlsx_min.py` | Minimal stdlib `.xlsx` reader + multi-sheet writer (no openpyxl on the server). Reading never modifies a workbook. |
| `osc_snapshot.py` | Snapshot step: one JSON per pilot job (job, activities, alerts, documents) from the **production** OnSite Companion, GET only, through the `osc_mcp` client the MCP server uses. Runs under `shared\mcp\osc-api\.venv\Scripts\python.exe` (needs `httpx`); refuses a stale copy; writes only under `runtime\`. |
| `ba_report_parse.py` | Weekly BA report → row model. Columns are located **by header text** (the export gained five columns on 28 Sep 2026); unknown columns are carried verbatim; "Submit all RFI Items" is required. Reads the "PENDING …" / "RESOLVED …" item list, the v0.3 **Items** sheet (per-item values, one row per item, matched by Job No. + Item) and, for older drafts, the v0.2 L–O columns. |
| `ba_report_draft.py` | Deterministic Monday draft (v0.3): last week's report + per-job OSC snapshot JSONs → draft workbook (main sheet = the base's columns exactly; Items sheet = one row per item) + evidence bundle. Per item: Assigned to, Date submitted, Date resolved, Days outstanding in NSW business days, YELLOW/RED by tier (`TIERS`, `ASSIGNEE_TIER`, PO-11a). Items resolve only on fresh evidence and show once as RESOLVED; everything uncertain is kept and flagged. `--jobs` scopes the pilot. |
| `nsw_holidays.py` | NSW public holidays 2026–27 and `business_days()`; verify each new year before the first Monday run. |
| `compare_ba_report.py` | Pilot scorecard: AI draft vs the officer's real report for the same Monday → matched / missed / extra items per pilot job and the "% correctly pre-populated" headline (criterion 90 %). |
| `regress_ba_report.py` | Regression over synthetic fixtures (fake jobs/names only). Run after any change to the scripts above. |

Run mechanics are in `../workflows/ba-weekly-report.md` (§How to run).
