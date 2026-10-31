# OSC field map — weekly BA report

How each part of the weekly BA report is read from OnSite Companion through
the `osc-api-prod` MCP (production since 13 Oct 2026; the report only reads,
and the role's OSC changes are `../workflows/osc-updates.md`).
Mapped on **4 Sep 2026** (spec v7.3) against what was then the `osc-api`
connection, a dev copy of production frozen on 21 Aug 2026, using one NSW job
in the report and cross-checked against that week's report row.
**Re-checked against production on 23 Oct 2026** on the three pilot jobs and
the 19 Oct 2026 export: every field name and query below works, and the
seven mapped activity descriptions match exactly. The five columns the export
gained on 28 Sep 2026 were mapped in the same pass (three verified, two
unresolved). OSC data is live client data, so no row content appears here.
Query patterns follow the `osc-api` skill's
golden rules (always `$top`, body-filter GETs need `odata_filter={}`,
resolve contract number → `jobID` GUID first).

## The report itself

The Monday report is an OSC **Executive Reporter** export (saved definition,
"BA lodged jobs only" filter — procedure documented in the AI testing
folder), saved as `BA REPORT - DD.MM.YYYY.xlsx` (one sheet, header row 1,
one row per job) into the BA REPORTS archive under `Z:\ADMINISTRATION`.
The definition changes: on **28 Sep 2026** it gained *Engineering Ordered*,
*Receive Engineering*, *Review Engineering - Michael*, *Forward Engineering
to Certifier* (E–H) and *Covenant Ordered* (J), moving "Submit all RFI
Items" from G to L. The parser therefore locates every column by its
header text and carries unknown columns verbatim. The letters below are the
original (pre-28-Sep) layout, kept for the OSC mapping:

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
| Site Start (Physical) | construction-template activity (appended after BA; confirm exact description once a pilot job crosses over; none had by 23 Oct 2026, `APPEND Construction Workflow Template` still pending on all three) |

### Columns added 28 Sep 2026 (mapped 23 Oct 2026)

Since 27 Oct 2026 the engineering and covenant columns are also aged on
the Items sheet (PO-11b; engineering in two stages, PO-11c), read from the export
itself, so the two unresolved columns below still count: their dates
are what the officer typed as the engineering *Date submitted* on all
three pilot jobs.

| Report column | OSC job activity (description) | Status |
|---|---|---|
| Engineering Ordered | `Order Engineering - Piers, Footings & Slab Design` | verified (one job differed, but its OSC date was edited after the export) |
| Receive Engineering | none found | **unresolved**, see Gaps |
| Review Engineering (the header carries the reviewer's name) | none found | **unresolved**, see Gaps |
| Forward Engineering to Certifier | `Forward Engineers Footing/Slab Design to Private Certiifier` | verified; the doubled *i* is OSC's own spelling, match it as written |
| Covenant Ordered | `Submit Covenant Application` | verified |

These cells can hold text instead of a date (`PENDING REVIEW` on one job),
so read them like *Received RFI*.

Activity descriptions come from the workflow template, so they are stable
across jobs on the same template; treat the strings as config, re-verify per
template version. **Sequence numbers are not stable**: one pilot job carries
two extra activities (`Gas Mains Check` straight after lodgement, `Request
NOC from Certifier` late in the pre-construction steps), which shifts every
later step by one. Match on the description, never on the sequence.

Every job carries **two engineering chains**, *Piers, Footings & Slab
Design* and *Structural Steel*, each running Order → Receive → Review →
Amend Working Drawings → Forward to the certifier. OSC misspells two of the
steps (`Review Engineering - Strucutral Steel`, and `Private Certiifier` on
both Forward steps), so match on the start of the description. The drafter's
ENGINEERING family patterns (`Receive Engineering`, `Review Engineering`,
`Forward Engineers`) match both chains, and the family clears only when
every match is complete: a job whose slab engineering has gone to the
certifier still shows ENGINEERING active while its steel steps are pending.
Whether the report's ENGINEERING item means the slab chain only is a
question for the officer (#79).

## Query patterns (all verified live; re-checked on production 23 Oct 2026)

On production these collection GETs answer in OData form, with the items
under `value`.

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
else pending. An N/A activity usually still carries a `completionDate`, and
the export shows that date (the covenant steps on two pilot jobs), so check
`isNotApplicable` before reading the date as a completion. `user` is the
assigned owner (the ageing view's "who it is with"); it can be a team
placeholder rather than a person (`DRAFTING`, `ESTIMATING`, `SUPERVISOR`).
`*LastUpdatedOnUtc` companions (e.g. `completionDateLastUpdatedOnUtc`) give
audit timestamps. `completionDate` is date-only and is whatever the person
entered, so it can be back-dated: on one pilot job an engineering step was
ticked seven weeks after the date it carries. `completionDateLastUpdatedOnUtc`
is when the tick was entered. `hasAlerts` marks activities carrying an alert
thread.

Alerts on a job (coordination trail):

```
osc_get path=/api/Jobs/Alerts
        query={"$filter": "jobID eq <guid>", "$orderby": "createdOnUtc desc", "$top": 50,
               "$select": "alertID,subject,createdBy,createdOnUtc"}
        odata_filter={}
```

Per-activity alert threads: `GET /api/JobActivities/Alerts` filtered by
`jobActivityID` (same body-filter form). `jobID` is not a property there
(HTTP 400, checked 23 Oct 2026), so select `jobActivityID` on the activities
first.

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
        query={"$filter": "workflowStatusName eq '3. Pre-Construction'",
               "$orderby": "createdOnUtc desc", "$top": 50, "$skip": 0,
               "$select": "jobID,contractNumber,clientName,siteAddress,workflowStatusName"}
        odata_filter={}
```

**Always page.** On 23 Oct 2026 Pre-Construction held 83 jobs, and without
an `$orderby` one pilot job came back only on the second page of 50, so a
single `$top` silently drops jobs. Keep the `$orderby` fixed and raise
`$skip` by `$top` (both verified on this endpoint) until a page comes back
short. Then keep jobs whose *Submit … for Building Approval Application* activity
is complete. Workflow statuses are enumerable via
`GET /api/Jobs/WorkflowStatuses` (a `20. Test Job` status exists — useful
for safe write-phase testing later). The definitive membership rule is the
Executive Reporter definition; reconcile the API-derived set against one
real export before trusting it.

## DATE SUBMITTED evidence (v0.2, PO-11a)

Per outstanding item the drafter takes, in order: the officer's value from
column M of last week's corrected report; the **oldest** order / application
/ receipt document for the item family (`submitted_docs` in
`ba_report_draft.py`, e.g. `… - Energy Efficiency Request.msg`, `DRIVEWAY
APPLICATION`, `SECTION 68 APPLICATION.msg`); for activity-backed families the
last completed step before the first pending one in the same chain (so a
pending *Receive Engineering - X* dates from *Order Engineering - X*, and a
pending *Review* step from the *Receive* step; the slab and structural-steel
chains are told apart by their subject words because OSC misspells some
steps; a not-applicable step dates nothing); an alert whose subject matches the family **and was raised on
or after *Submit for BA*** (pre-lodgement alerts such as `LODGE FOR CC` are
instructions, not handovers — observed on the pilot jobs); else the first
report sighting, flagged "assumed". Documents and activities may
legitimately predate lodgement (engineering, s10.7 ordered early, PO-5).
Document and alert timestamps are UTC, so the drafter reads them as Sydney
dates (an upload at 08:30 on a Monday is Sunday evening in UTC); activity
completion dates are stored at midnight UTC and keep their day.
`attachedOnUtc` is when the `.msg` was dragged into OSC, which lags the
actual send (PO-9), so document-derived dates are verify-grade and the
officer's typed value always wins.

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
- *Receive Engineering* and *Review Engineering* (export columns
  since 28 Sep 2026): no activity matches. The export holds date-times
  (a minute apart on two jobs), while the slab-engineering activities carry
  other dates or are still pending. On each pilot job the *Receive
  Engineering* time falls within one to four minutes of an engineering
  document upload (a certificate of compliance or a design revision),
  reading the export's times as UTC+10, and on two jobs the *Review
  Engineering* time does too; none equals an upload time. The saved
  Executive Reporter definition names each column's source; read it there
  before mapping these two.
