# OSC field map — weekly BA report

How each part of the weekly BA report is read from OnSite Companion through
the read-only `osc-api` MCP. Mapped live against the dev instance on
**4 Sep 2026** (spec v7.3) using one NSW job in the report and cross-checked
against that week's report row; the dev instance serves live client data, so
no row content appears here. Query patterns follow the `osc-api` skill's
golden rules (always `$top`, body-filter GETs need `odata_filter={}`,
resolve contract number → `jobID` GUID first).

## The report itself

The Monday report is an OSC **Executive Reporter** export (saved definition,
"BA lodged jobs only" filter — procedure documented in the AI testing
folder), saved as `BA REPORT - DD.MM.YYYY.xlsx` (one sheet, header row 1,
one row per job) into the BA REPORTS archive under `Z:\ADMINISTRATION`.
Columns:

| Col | Header | Kind |
|---|---|---|
| A | Job No. | contract number |
| B | Marketer | text |
| C | Job Address | text |
| D | Submit for BA | date (Excel serial) |
| E | Received RFI | date, or text (e.g. "AWAITING RFI") |
| F | Received Covenant Approval | date |
| G | Submit all RFI Items | **date when complete; "PENDING …" item list while in flight** (the manually-typed red column) |
| H | BA Received | date |
| I | Deposit Paid | date |
| J | Nominate Site Start | date |
| K | Site Start (Physical) | date |

In-flight `G` text is a comma-separated list of outstanding items in caps,
with parenthetical state — `(REVIEW)`, `(TO BE ORDERED)`, `(UPGRADES)`,
`(W/O X)` meaning *waiting on X*. Those item names map onto the standard
RFI task vocabulary (`Standard RFI Tasks .docx` in the AI testing folder).

## Column → OSC source (verified)

The date columns are **workflow activity completion dates**. Verified: the
mapped job's activity completion dates equal the report's serials exactly.

| Report column | OSC job activity (description) |
|---|---|
| Submit for BA | `Submit Documents to Private Certifier for Building Approval Application` |
| Received RFI | `Receive RFI from Certifier` |
| Received Covenant Approval | `Receive Covenant Approval & Upload to OSC` |
| Submit all RFI Items | `Return RFI Information to Certifier` |
| BA Received | `h) Building Approval Received from Certifier` |
| Deposit Paid | `Receive Deposit Claim Payment` |
| Nominate Site Start | `Nominate Site Start Date` |
| Site Start (Physical) | construction-template activity (appended after BA; confirm exact description once a pilot job crosses over) |

Activity descriptions come from the workflow template, so they are stable
across jobs on the same template; treat the strings as config, re-verify per
template version.

## Query patterns (all verified live)

Resolve a report row's job:

```
osc_get path=/api/Jobs
        query={"$filter": "contractNumber eq '<jobno>'", "$top": 2,
               "$select": "jobID,contractNumber,clientName,siteAddress,workflowStatusName"}
        odata_filter={}
```

Note: the Jobs collection model exposes `contractNumber` (the
`contractNo` name on the single-job view model is not filterable here).
`siteAddress.state` gives NSW/QLD.

Activities with completion state and owner:

```
osc_get path=/api/JobActivities
        query={"$filter": "jobID eq <guid>", "$orderby": "sequence", "$top": 200,
               "$select": "sequence,description,completionDate,isNotApplicable,serviceProvider,user,hasAlerts"}
```

Status is derived: `completionDate` set → complete; `isNotApplicable` → N/A;
else pending. `user` is the assigned owner (the ageing view's "who it is
with"); `*LastUpdatedOnUtc` companions (e.g.
`completionDateLastUpdatedOnUtc`) give audit timestamps. `hasAlerts` marks
activities carrying an alert thread.

Alerts on a job (coordination trail):

```
osc_get path=/api/Jobs/Alerts
        query={"$filter": "jobID eq <guid>", "$orderby": "createdOnUtc desc", "$top": 50,
               "$select": "alertID,subject,createdBy,createdOnUtc"}
        odata_filter={}
```

Per-activity alert threads: `GET /api/JobActivities/Alerts` filtered by
`jobActivityID` (same body-filter form).

Documents (names encode status; order/approval evidence):

```
osc_get path=/api/Jobs/Documents
        query={"$filter": "jobID eq <guid>", "$orderby": "attachedOnUtc desc", "$top": 100,
               "$select": "documentID,description,extension,version,attachedOnUtc,documentTypeID"}
        odata_filter={}
```

Observed evidence conventions on the mapped job: order emails saved as
`.msg` (e.g. an energy-efficiency request), fee receipts (`… RECEIPT`),
approvals (`APPROVAL - …`), the RFI itself (`RFI`, `.msg`, versioned), plus
the discovery's energy application → energy report rename rule (PO-8a).
`GET /api/Jobs/{JobID}/DocumentTypes` resolves `documentTypeID`.

Enumerating the report's job set:

```
osc_get path=/api/Jobs
        query={"$filter": "workflowStatusName eq '3. Pre-Construction'", "$top": 50,
               "$select": "jobID,contractNumber,clientName,siteAddress,workflowStatusName"}
        odata_filter={}
```

then keep jobs whose *Submit … for Building Approval Application* activity
is complete. Workflow statuses are enumerable via
`GET /api/Jobs/WorkflowStatuses` (a `20. Test Job` status exists — useful
for safe write-phase testing later). The definitive membership rule is the
Executive Reporter definition; reconcile the API-derived set against one
real export before trusting it.

## Gaps (feed these to the OSC workflow-enrichment session)

Facts the report needs that are **not** OSC activities on the mapped NSW
job's template — they live only in document names, alert text, or the
mailbox:

- Energy application / report status (no energy activity; evidence is the
  order `.msg` and the report document rename).
- s10.7 certificate ordered/received.
- Water-authority application (evidence: receipt + approval documents).
- Council applications (driveway, s68/s138…): application/receipt/approval
  exist only as documents.
- Contributions payable (HPC / s7.11) — no activity, no standard document
  name observed.
- Insurances exist as activities (pay + email to certifier) but not per
  policy type.
- Alert recipients: the collection alert models return the requester's own
  read state; enumerating recipients per alert needs
  `/api/Alerts/{AlertID}/Recipients/{RecipientID}` (by id) — treat recipient
  enumeration as unresolved; ageing starts from activity `user` + alert
  `createdOnUtc`.
- QLD certifier-portal facts (per PO-14): never readable; drafts mark them
  "manual check".
