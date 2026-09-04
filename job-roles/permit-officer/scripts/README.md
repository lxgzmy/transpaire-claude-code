# Scripts — Permit Officer

Stdlib-only Python (no third-party packages on the server), mirroring the
contract-admin scripts convention. All read-only against business files;
outputs go to `runtime\permit-officer\` only.

| Script | Purpose |
|---|---|
| `xlsx_min.py` | Minimal stdlib `.xlsx` reader (sheets, rows, TSV dump) used to parse the weekly BA report export. Read-only. |

Planned for the `ba-weekly-report` build (see `../workflows/ba-weekly-report.md`):
`ba_report_parse.py` (report → row model), `ba_report_draft.py`
(carry-forward + OSC snapshot → draft + evidence bundle),
`regress_ba_report.py` (regression over synthetic fixtures).
