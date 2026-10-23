# Reference — Permit Officer

Source material lives outside the repo (it contains client PII); this file
only points at it.

| Source | Where | Notes |
|---|---|---|
| Discovery recording, 20 Aug 2026 | To be filed on `Z:` in the AI testing folder | `AI consultation - Approval-20260820_040605UTC-Meeting Recording.mp4`; the substantive session ends when the guests leave the call. |
| Discovery record (de-identified) | `Z:\CLAUDE CODE\cowork-projects\5. permit_officer\` | 12-page PDF, 20 Aug 2026; the repo's de-identified extraction is `docs/superpowers/brainstorms/2026-08-20-permit-officer-approvals.md`. |
| AI testing folder (per-role) | `Z:\AI test\Permit Officer` | Created by the business owner 21 Aug 2026 (the parent `Z:\AI test\` on 11 Aug), populated by the permit officer from 31 Aug, and sorted into subfolders on 23 Oct 2026: `GENERAL PROCEDURES\` — `Standard RFI Tasks .docx` (the standard RFI item vocabulary — also the input to the OSC workflow-enrichment session) and `WEEKLY BA REPORT PROCEDURE.pdf` (the report's OSC Executive Reporter export mechanics: saved definition, BA-lodged-jobs filter, Excel formatting steps); `NSW PROCEDURES\` (CDC lodgement, energy report, insurance, principal-certifier appointment, water-authority applications); `QLD PROCEDURES\` (energy report, insurance); `PAST RFIs\` (eight NSW certifier RFIs, the workflow-2 corpus); `BA Report test\` (the agreed drop folder for weekly drafts and their evidence notes). |
| Still to drop into the AI testing folder | `Z:\AI test\Permit Officer` | Blank council/certifier application forms (workflow 3). The weekly report exports live in the BA REPORTS archive under `Z:\ADMINISTRATION` and are copied into the runtime reports folder per the runbook. |
| Current weekly BA report | Maintained by the permit officer (Excel, updated Mondays) | Never copy into the repo; a **synthetic** layout fixture may go under `../fixtures/` once the template is agreed. |
| OSC field map | [osc-field-map.md](osc-field-map.md) (this folder) | De-identified endpoint → report-column mapping, verified 4 Sep 2026 against the `osc-api` MCP (then a dev copy frozen 21 Aug 2026; re-check against production through `osc-api-prod`), plus the list of facts OSC cannot yet provide (feeds the workflow-enrichment ask). |
