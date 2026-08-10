# Map of the Z: share

What lives where on `Z:`, so save advice and searches land in the right place.

**How this was built:** a read-only survey of folder *names* to depth 3 on
10 Aug 2026, plus loose-file counts by extension. No business file was opened.
Folders that could not be read are recorded as **denied**, not as empty — the two
are different and must never be conflated.

**Surveyed name-and-count only** (no descent into files, per the skill's
handle-with-care rules): `ACCOUNTS`, `WORKPLACE HEALTH AND SAFETY\INCIDENT
REPORTS`, and the staff folders in `COMPANY GENERAL INFORMATION`.
**Not opened at all:** `Z:\COMPANY GENERAL INFORMATION\TRANSPIRE PASSWORDS & SET
UP WORKFLOW`.

**Deliberately not recorded here:** client names and addresses, staff names,
server names, supplier names. Job folders, supplier folders, estate folders and
folders named after individuals are described by *pattern and count*, never
listed. Folders named after a person are personal working folders — never a
filing location to recommend.

**Treat as a starting map, not gospel.** It's a snapshot, and the business has
not yet confirmed it. If what you see on the drive disagrees with this file,
trust the drive and mention the difference.

## The drive has two different shapes

This is the single most important thing to understand before giving advice.

1. **`Z:\PROJECTS` is job-shaped** — organised by region → job → document type.
   Records for a specific build live here.
2. **Everything else is department-shaped** — organised by function (accounts,
   drafting, estimating, sales, safety). Company-wide material lives here.

So "where does this go?" splits on one question: **is this about one specific
job, or about the business generally?** Job-specific → `PROJECTS`. Otherwise →
the relevant department folder, using the per-folder sections below.

## Three questions that pick the folder

Work through these in order before answering any "where is it / where does it go"
question. They resolve almost every case, and they matter more than the folder
descriptions further down.

**1. Is there a job number or a specific address attached to it?**
Yes → `Z:\PROJECTS`, then the job template subfolder. No → a department folder.

**2. Is it a blank form, or a filled-in one?**
Blank template or procedure → `PROCEDURES & FORMS\<department>\`. Completed for a
job → the job folder. Completed but company-wide (a supplier agreement, a
subbie's certificate) → that department's own folder.
This is the single biggest source of wrong answers on this drive.

**3. Is it the controlled copy, or someone's working copy?**
Several folders hold reference copies of the same material —
`CONSTRUCTION MANAGER\CONSTRUCTION` mirrors `PROCEDURES & FORMS\CONSTRUCTION`,
and there are personal folders in `ACCOUNTS`, `DRAFTING`, `SALES` and
`PROCEDURES & FORMS`. `PROCEDURES & FORMS` is the controlled home for forms and
procedures. Never recommend saving into a personal folder or a `Do Not Use`
folder, and flag it if a search result lands in one.

## Same document, different homes

When a request matches a row here, ask which one they mean rather than guessing —
this is the one case where a clarifying question is always worth it.

| They say | Blank / template | Company-wide record | For one job |
|---|---|---|---|
| Variation | `PROCEDURES & FORMS\CONTRACTS\REGION - …\` | `ESTIMATING\6. Sales Estimating\3. Variations\` (pricing masters) | `…\<job>\ESTIMATING\1. SALES\2. VARIATIONS\VAR-###\` |
| Contract | `PROCEDURES & FORMS\CONTRACTS\REGION - …\` | — | `…\<job>\CONTRACT\CONTRACT DOCUMENTATION\` |
| Colour scheme | `PROCEDURES & FORMS\COLOURS\` (standard schemes) | — | `…\<job>\COLOUR SCHEMES\` |
| SWMS | `PROCEDURES & FORMS\SAFETY\` | `WHS\Standard SWMS\` (ours) or `WHS\SWMS and Certs of Currency\<subbie>\` | — |
| Safety pack | `PROCEDURES & FORMS\SAFETY PACK FOR SUBBIES\` | `WHS\SAFETY PACK FOR SUBBIES\` and `WHS\SAFETY PACK FOR METERBOX (SUPERVISOR FILE)\` | — |
| QA / construction form | `PROCEDURES & FORMS\CONSTRUCTION\QA Forms\` | `CONSTRUCTION MANAGER\CONSTRUCTION\` (reference copy) | `…\<job>\CONSTRUCTION\` |
| Defects form | `MAINTENANCE\FORMS\` | `MAINTENANCE\` (defect register) | `…\<job>\MAINTENANCE\` |
| Insurance certificate | — | `ADMINISTRATION\INSURANCE\` (company) | `…\<job>\COUNCIL\INSURANCES\` |
| BASIX | `ADMINISTRATION\COUNCIL\BASIX - ENERGY FORMS\` | — | `…\<job>\DRAFTING\WORKING DRAWINGS\BASIX Report\` |
| Estate / stage info | — | `ESTATES INFORMATION\<NSW\|SEQ>\<estate>\` (authoritative; ignore the `DRAFTING` stub) | — |
| Quote | — | `ESTIMATING\2. Supplier Agreements & Information\<supplier>\` | `…\<job>\ESTIMATING\1. SALES\3. QUOTES\` (sales) or `\2. PRODUCTION\QUOTES\` |

## A–Z: what people ask for

Keyed on the words staff actually use. `<job>` means the job folder under
`Z:\PROJECTS\<region>\`. Everything else is a full path from `Z:\`.

| They ask about | Goes to / lives in |
|---|---|
| 88B, Form 2, fencing, stat dec | `PROCEDURES & FORMS\FENCING\` + subfolder |
| Archicad, CAD template | `DRAFTING\Archicad\` |
| Bank statement, reconciliation | `ACCOUNTS\BANKS STATEMENTS & RECONCILIATIONs\` *(restricted)* |
| BASIX, energy assessment (blank) | `ADMINISTRATION\COUNCIL\BASIX - ENERGY FORMS\` |
| Bill of quantities, BOQ | `ESTIMATING\6. Sales Estimating\7. Master Bill of Quantities\` |
| Brochure, company profile, logo | `COMPANY GENERAL INFORMATION\` |
| Certificate of currency | `WORKPLACE HEALTH AND SAFETY\SWMS and Certs of Currency\<subbie>\` |
| Certifier, private building certifier | `PROCEDURES & FORMS\PRE-CONSTRUCTION\CERTIFIERS\` or `ADMINISTRATION\COUNCIL\` |
| Code, standard, product literature | `DRAFTING\Codes & Products\` |
| Colour selection (a client's) | `<job>\COLOUR SCHEMES\` or `<job>\ESTIMATING\1. SALES\4. CUSTOMER SELECTIONS\` |
| Contract, executed / signed | `<job>\CONTRACT\CONTRACT DOCUMENTATION\` |
| Contract pricing | `<job>\ESTIMATING\1. SALES\1. CONTRACT PRICING\` |
| Contours, site survey | `<job>\DRAFTING\ADDITIONAL INFORMATION & CONTOURS\` |
| Council application, DA, CDC | `<job>\COUNCIL\APPLICATION FORMS\` |
| Council fees, credit card form | `ADMINISTRATION\COUNCIL\COUNCIL FEES & CREDIT CARD FORMS\` |
| Covenant | `<job>\COUNCIL\COVENANT\` |
| Credit application | `ACCOUNTS\CREDIT APPLICATIONS\` *(restricted)* |
| DataBuild price file, cost centre | `ESTIMATING\4. Databuild Price File Database\` |
| DataBuild process, how-to | `ESTIMATING\11. Databuild Processes\` |
| Defects, warranty claim (a job's) | `<job>\MAINTENANCE\` |
| Defect register, blank defects form | `MAINTENANCE\` and `MAINTENANCE\FORMS\` |
| Design guideline register | `ESTATES INFORMATION\` |
| Dilapidation report, booking sheet | `MAINTENANCE\FORMS\` |
| Driveway application | `ADMINISTRATION\COUNCIL\DRIVEWAY APPLICATION FORMS\` |
| Driveway gradients / regulations | `ESTATES INFORMATION\<NSW\|SEQ> - Driveway Regs\<council>\` |
| Email template, standard wording | `ADMINISTRATION\EMAIL TEMPLATES\` |
| EOI (subcontractor) | `CONSTRUCTION MANAGER\Subcontractor Expression of Interest\<trade>\` |
| EOI (sales / house & land) | `SALES\` |
| Estate, stage number | `ESTATES INFORMATION\<NSW\|SEQ>\<estate>\` |
| Facade, floor plan idea | `SALES\NEW FACADE IDEAS\`, `SALES\FLOOR PLAN IDEAS\`, `SALES\MARKETING FLOOR PLAN\` |
| Finance approval (P&C lot) | `SALES\6. FINANCE APPROVALS - P&C LOTS\` |
| Fire ants | `PROCEDURES & FORMS\CONSTRUCTION\FIRE ANTS\` (controlled) or `CONSTRUCTION MANAGER\FIRE ANTS\` |
| Gas, power, utility connection | `ADMINISTRATION\UTILITIES - GAS & POWER\<retailer>\` |
| Handover pack, standards & tolerances | `ADMINISTRATION\HANDOVER\` |
| House & land package | `SALES\1. NSW PACKAGES\` or `SALES\2. QLD PACKAGES\` + estate |
| House design, master design | `DRAFTING\Transpire Master Designs\` |
| Incident, injury report | `WORKPLACE HEALTH AND SAFETY\INCIDENT REPORTS\<year>\` *(restricted)* |
| Insurance (company) | `ADMINISTRATION\INSURANCE\` |
| Insurance certificate (a job's) | `<job>\COUNCIL\INSURANCES\` |
| Invoice, payment, receipt, rebate | `ACCOUNTS\` + matching subfolder *(restricted)* |
| Key register | `ADMINISTRATION\KEY REGISTER\` |
| Land contract, put and call | `SALES\5. P&C DOCS & LAND CONTRACTS\` |
| Marketing / agency agreement | `SALES\4. MARKETING AGREEMENTS\<agency>\` |
| Marketer report, stage chart | `ADMINISTRATION\MARKETERS REPORTS\` |
| OnSite Companion, OSC | `ESTIMATING\10. OnSite Companion Database\` |
| Plans, working drawings | `<job>\DRAFTING\WORKING DRAWINGS\` |
| Prelim plans | `<job>\DRAFTING\CONTRACT-PRELIM PLANS\` |
| Procedure, blank form (any kind) | `PROCEDURES & FORMS\<department>\` |
| Promotional offer | `ESTIMATING\6. Sales Estimating\8. Current Promotional Offers\` |
| Purchase order, production quote | `<job>\ESTIMATING\2. PRODUCTION\ORDERS\` or `\QUOTES\` |
| QA form, site inspection | `PROCEDURES & FORMS\CONSTRUCTION\QA Forms\` |
| Quote (sales stage) | `<job>\ESTIMATING\1. SALES\3. QUOTES\` |
| Safety audit | `WORKPLACE HEALTH AND SAFETY\Audits\` |
| Safety pack | see [Same document, different homes](#same-document-different-homes) |
| Slab design, soil report | `PROCEDURES & FORMS\PRE-CONSTRUCTION\` + subfolder |
| Social media post, photo | `ADMINISTRATION\SOCIALS\` |
| Software certificate, user manual | `SOFTWARE\` *(key files blocked)* |
| Staff list, photo, licence | `COMPANY GENERAL INFORMATION\` *(restricted)* |
| Standard construction detail | `DRAFTING\Standard Details\Transpire Construction Details\` |
| Structural steel | `DRAFTING\Structural Steel\` |
| Subcontractor rates | `ESTIMATING\3. Subcontractor Rates\<region>\` |
| Subcontractor org details form | `WORKPLACE HEALTH AND SAFETY\Organisational Details Forms\<subbie>\` |
| Subcontractor pack (accounts) | `ACCOUNTS\SUBCONTRACTOR PACK DOCUMENTS\` *(restricted)* |
| Supplier agreement, price list | `ESTIMATING\2. Supplier Agreements & Information\<supplier>\` |
| Supplier statement | `ACCOUNTS\SUPPLIER STATEMENTS\` *(restricted)* |
| SWMS | see [Same document, different homes](#same-document-different-homes) |
| System and Procedures Manual | `PROCEDURES & FORMS\` (also a copy in `CONSTRUCTION MANAGER\`) |
| Toolbox talk | `WORKPLACE HEALTH AND SAFETY\Tool Box Talks\` |
| Tree removal application | `ADMINISTRATION\COUNCIL\TREE REMOVAL APPLICATION FORMS\` |
| Variation (a job's) | `<job>\ESTIMATING\1. SALES\2. VARIATIONS\VAR-###\` |

Not in this index? Fall back to the three questions above, then the per-folder
sections below. If still nothing fits, say so and suggest the closest match —
never invent a folder.

## Top-level folders

`Loose` = files dumped at the folder's own root rather than in a subfolder. High
numbers are the drive's most widespread clutter problem — see
[Housekeeping findings](#housekeeping-findings).

| Folder | Holds | Loose | Notes |
|---|---|---|---|
| `ACCOUNTS` | Finance: receivables, bank statements and reconciliations, invoicing, payments, receipts, rebates, credit applications, subcontractor pack documents | 66 | **Restricted** — see the skill's safety rules |
| `ADMINISTRATION` | Day-to-day admin across 19 subfolders | 3 | See [ADMINISTRATION](#administration) |
| `CLAUDE CODE` | This automation project and its Cowork projects | — | Not business records. Don't file business documents here |
| `COMPANY GENERAL INFORMATION` | Company identity: logo, profile, brochure, licences, staff lists and photos, supervisors | 5 | Contains a **blocked** credentials folder and staff personal information |
| `CONSTRUCTION MANAGER` | Construction management: site visits, feedback, fire ants, subcontractor EOIs, a large reference library of standards and product literature | **80** | Worst loose-file count on the drive |
| `DRAFTING` | Archicad, standard details, structural steel, master designs, codes and products | 9 | Holds a **partial** `ESTATES INFORMATION` stub — see findings |
| `ESTATES INFORMATION` | Estate and stage information by region, driveway regulations by council | 1 | The authoritative estates source. Used by the new-job workflow for stage numbers |
| `ESTIMATING` | Contracts and inclusions, supplier agreements, subcontractor rates, DataBuild price file, OnSite Companion database, production and sales estimating | 4 | Numbered `1.`–`13.` prefixes. Writable — see findings |
| `IMPORTED` | Genuinely empty — 0 files, 0 subfolders | 0 | See findings |
| `MAINTENANCE` | Maintenance forms, booking sheets, dilapidation reports, plus a per-address archive | 5 | |
| `OPERATIONS` | **Unknown — access denied** | ? | Cannot be assessed. Do **not** describe as empty, and never propose removing it |
| `PROCEDURES & FORMS` | The company's procedures and blank forms, mirrored by department | 4 | *Procedure and template* material — the blank form, not a completed one |
| `PROJECTS` | **All job records.** See below | 1 | The job-shaped part of the drive |
| `SALES` | Packages by region, marketing brochures and agreements, land contracts, finance approvals, floor plan ideas | 13 | Loosest structure on the drive |
| `SOFTWARE` | Software certificates and user manuals | 4 | Contains a real `.pfx` key file — blocked, see safety rules |
| `WORKPLACE HEALTH AND SAFETY` | Audits, SWMS and certificates of currency, toolbox talks, safety packs | 26 | `INCIDENT REPORTS` holds personal/health information — handle with care |
| `Z. SUPERSEDED` | Mixed archive: an old DA search, a council application, a region folder, stray files | 5 | General archive, **not** a per-job lifecycle stage |

The `Z:\` root itself holds two loose files: a `Thumbs.db` and a drive shortcut
whose **filename contains the server name**. Filter both out, and never repeat
the shortcut's filename — see the skill's rule on server names.

## Inside `Z:\PROJECTS`

**Regions:** `CUDGEN` (9 jobs), `GUNNEDAH` (15), `SEQ` (185), `SYDNEY` (122),
`TAMWORTH` (11).

### Lifecycle sits at TWO levels — search both

This is the most common cause of a "job not found" that actually exists.

1. **Beside the regions:** `COMPLETED CONTRACTS` (249 jobs) and
   `CANCELLED CONTRACTS` (182) are siblings of the region folders, and are flat —
   not subdivided by region.
2. **Inside the regions**, each with its own lifecycle subfolders:
   - `SEQ\ARCHIVE-HANDED OVER` — 398 jobs
   - `SYDNEY\HANDED OVER` — 199 jobs
   - `SYDNEY\CANCELLED` — 73 jobs
   - `SEQ\CANCELLED` — 58 jobs
   - `GUNNEDAH\CANCELLED` and `TAMWORTH\CANCELLED` — 1 each

That is **730 job folders that a region-level look will miss**, more than the
342 sitting in the live region folders. Two further folders are mis-parented and
hold 7 job folders each: one under `SEQ` prefixed `DRAFT_`, one under `SYDNEY`
named as a lot rather than a job.

**Search order for a job number:** the region → that region's own lifecycle
subfolders → the top-level `COMPLETED CONTRACTS` and `CANCELLED CONTRACTS`. Only
after all of those may you say a job doesn't exist.

Also present: `MARK UP'S` and `z.SS` (another archive).

### Job folder names

The intended pattern is `<5-digit job number> - LOT <lot> <STREET>, <SUBURB>
<STATE>`, first two digits being the year (`26###` = 2026).

**Real names vary around the separator** and any search or duplicate check must
tolerate it. All of these exist on the drive:

- `26049 - LOT …` — intended form
- `26003- LOT …`, `26038- LOT …`, `18054- LOT …` — no space before the dash
- `16001 -LOT …`, `18041 -LOT …` — space on the wrong side
- `25115- LOT 4699  SUNLIGHT …` — double space inside the title
- Some folders carry no job number at all

So **match on the leading 5 digits, not on `"<number> - "`**. Searching by job
number is still the most reliable approach; street spellings and punctuation vary
far more.

Job folder names also routinely contain brackets, e.g. a lot number in
parentheses. Always use literal-path handling, never wildcard matching, on these.

### The document-type template

Every region contains `00000 - LOT MASTER FOLDER` — the template copied for each
new job (verified present in all five regions). This is the authoritative answer
to "which subfolder?":

```
COLOUR SCHEMES
CONSTRUCTION
CONTRACT
  └ CONTRACT DOCUMENTATION
COUNCIL
  ├ APPLICATION FORMS
  ├ COVENANT
  └ INSURANCES
DRAFTING
  ├ ADDITIONAL INFORMATION & CONTOURS
  ├ CONTRACT-PRELIM PLANS
  └ WORKING DRAWINGS
      └ BASIX Report
ESTIMATING
  ├ 1. SALES
  │   ├ 1. CONTRACT PRICING
  │   ├ 2. VARIATIONS
  │   │   └ VAR-001
  │   ├ 3. QUOTES
  │   └ 4. CUSTOMER SELECTIONS
  └ 2. PRODUCTION
      ├ ORDERS
      └ QUOTES
MAINTENANCE
```

Common mappings, for save advice:

| Document | Goes to |
|---|---|
| Signed or draft variation | `ESTIMATING\1. SALES\2. VARIATIONS\VAR-###\` |
| Contract pricing | `ESTIMATING\1. SALES\1. CONTRACT PRICING\` |
| Supplier or trade quote (sales stage) | `ESTIMATING\1. SALES\3. QUOTES\` |
| Client colour or product selections | `COLOUR SCHEMES\` or `ESTIMATING\1. SALES\4. CUSTOMER SELECTIONS\` — check which the job already uses |
| Executed contract documents | `CONTRACT\CONTRACT DOCUMENTATION\` |
| DA/CDC, covenant, insurance certs | `COUNCIL\` + matching subfolder |
| Plans, contours, BASIX | `DRAFTING\` + matching subfolder |
| Purchase orders, production quotes | `ESTIMATING\2. PRODUCTION\` |
| Defects, warranty, post-handover | `MAINTENANCE\` |

Older jobs predate the current template and won't all have these folders. Match
what that job actually has rather than the template.

**Region naming differs between systems:** the drive uses `GUNNEDAH` / `SEQ` /
`SYDNEY` / `TAMWORTH` / `CUDGEN`; OnSite Companion uses codes like `SEQ1` /
`SYDNEY01`. Always report the drive names — that's what people see in Explorer.

---

# The department folders

Everything below is company-wide, not job-specific. Each section gives the
subfolders and a save-location table.

## ADMINISTRATION

19 subfolders: `ADMIN` (14 sub), `CONSTRUCTION`, `COUNCIL` (12 sub),
`EMAIL TEMPLATES`, `FEEDBACK`, `FLOW`, `HANDOVER`, `IMAGES OF COMPLETED ITEMS`,
`INSURANCE`, `KEY REGISTER`, `MARKETERS REPORTS`, `MEETINGS`, `ONENOTE`,
`RAIN GARDEN TANK INFO`, `REPORTS`, `SIGN`, `SOCIALS` (14 sub),
`SUPERVISOR FILE`, `UTILITIES - GAS & POWER`.

| Document | Goes to |
|---|---|
| Standard email wording | `EMAIL TEMPLATES\` |
| Handover pack, warranty, standards & tolerances | `HANDOVER\` (+ `NSW WARRANTY` / `QLD WARRANTY`) |
| Certifier / town planner / council forms and fees | `COUNCIL\` + the matching body or form subfolder |
| BASIX and energy forms | `COUNCIL\BASIX - ENERGY FORMS\` |
| Driveway or tree removal application | `COUNCIL\DRIVEWAY APPLICATION FORMS\` / `…TREE REMOVAL…\` |
| Company insurance certificates | `INSURANCE\` |
| Key handover register | `KEY REGISTER\` |
| Marketer / stage chart reporting | `MARKETERS REPORTS\` |
| Gas and power connections | `UTILITIES - GAS & POWER\` + retailer |
| Social media photos and posts | `SOCIALS\` |
| Internal procedures, labels, misc templates | `ADMIN\` + matching subfolder |

## PROCEDURES & FORMS

**Blank forms and procedures only — never a completed document.** Mirrored by
department, 18 subfolders: `ACCOUNTS`, `ADMINISTRATION`, `COLOURS`,
`CONSTRUCTION`, `CONTRACTS`, `COUNCIL DOCS & NCC2019`, `DRAFTING`, `ESTIMATING`,
`FENCING` (13 sub), `JOB FLOW CHART (SYDNEY)`, `MAINTENANCE`, `MARKETING`,
`PRE-CONSTRUCTION`, `REPORTS`, `SAFETY`, `SAFETY PACK FOR SUBBIES`, `SALES`,
`TO REVIEW`.

| Document | Goes to |
|---|---|
| Blank contract template | `CONTRACTS\REGION - <GUNNEDAH, NSW / SEQ / SYDNEY>\` |
| System and Procedures Manuals | `PROCEDURES & FORMS\` root (also in `CONSTRUCTION MANAGER`) |
| Blank QA / construction form, specification | `CONSTRUCTION\FORMS\` or `\QA Forms\` |
| Fencing Form 2, 88B, stat dec, client authority | `FENCING\` + matching subfolder |
| Certifier, contour survey, slab design, soil report templates | `PRE-CONSTRUCTION\` + matching subfolder |
| Standard colour schemes | `COLOURS\{EXTERNAL,INTERNAL} COLOUR SCHEMES\` |
| Subbie safety pack (issue copy) | `SAFETY PACK FOR SUBBIES\` |
| Milestone / status report template | `REPORTS\` + matching subfolder |

`TO REVIEW` contains folders explicitly prefixed `Do Not Use` — never recommend
saving there, and flag a hit from there as probably superseded.

## ESTIMATING

Writable (see findings). Numbered `1.`–`13.`: `1. Contracts & Inclusions`,
`2. Supplier Agreements & Information` (142 supplier folders, grouped by region
at `1. SEQ & NORTHERN NSW` / `2. SYDNEY` / `3. TAMWORTH & GUNNEDAH`),
`3. Subcontractor Rates` (by region), `4. Databuild Price File Database` (267
numbered cost-centre folders), `5. Production Estimating`, `6. Sales Estimating`
(11 sub), `7. Therefore Invoicing`, `8. Spreadsheets Backup`,
`9. Databuild Pictures`, `10. OnSite Companion Database`,
`11. Databuild Processes`, `12. Townhouse contractors`, `13. Superseded`.

| Document | Goes to |
|---|---|
| Supplier agreement or price list | `2. Supplier Agreements & Information\<supplier>\` |
| Subcontractor rate schedule | `3. Subcontractor Rates\<region>\` |
| DataBuild cost-centre pricing | `4. Databuild Price File Database\<numbered cost centre>\` |
| Sales-stage pricing, BOQ, promotional offer | `6. Sales Estimating\` + matching numbered subfolder |
| OSC database material | `10. OnSite Companion Database\` |
| DataBuild process notes | `11. Databuild Processes\` |

## SALES

Loosest structure on the drive — 31 subfolders, a mix of numbered
(`1. NSW PACKAGES` 29 estates, `2. QLD PACKAGES` 251 estates,
`3. MARKETING BROCHURES`, `3. TAMWORTH REGION` — note the duplicated `3.`,
`4. MARKETING AGREEMENTS` 80 agencies, `5. P&C DOCS & LAND CONTRACTS`,
`6. FINANCE APPROVALS - P&C LOTS`) and many ad-hoc ones. Expect searches here to
need more than one attempt.

| Document | Goes to |
|---|---|
| House & land package | `1. NSW PACKAGES\` or `2. QLD PACKAGES\` + estate |
| Marketing / agency agreement | `4. MARKETING AGREEMENTS\<agency>\` |
| Put & call, land contract | `5. P&C DOCS & LAND CONTRACTS\` |
| Finance approval for a P&C lot | `6. FINANCE APPROVALS - P&C LOTS\` |
| Brochure, floor plan, facade concept | `3. MARKETING BROCHURES\`, `MARKETING FLOOR PLAN\`, `NEW FACADE IDEAS\` |
| Sales stock list | `SALES STOCK LIST\` |

`MASTER FOLDER TEMPLATE\LOT` is a **sales package template** — a third template
on the drive. Copy it rather than hand-building a package folder.
`To be done` and `To Package Up` are working queues, not filing destinations.

## WORKPLACE HEALTH AND SAFETY

`Audits`, `INCIDENT REPORTS` (by year — **personal/health information**),
`JSEAsy`, `Organisational Details Forms`,
`SAFETY PACK FOR METERBOX (SUPERVISOR FILE)`, `SAFETY PACK FOR SUBBIES`,
`Standard SWMS`, `SWMS and Certs of Currency` (49 subcontractor folders),
`Tool Box Talks`.

| Document | Goes to |
|---|---|
| Subcontractor SWMS or certificate of currency | `SWMS and Certs of Currency\<subcontractor>\` |
| Transpire's own standard SWMS | `Standard SWMS\` |
| Safety audit | `Audits\` |
| Toolbox talk | `Tool Box Talks\` |
| Subcontractor org details form | `Organisational Details Forms\<subcontractor>\` |
| Meterbox / subbie safety pack | the matching `SAFETY PACK FOR …\` |
| Incident or injury report | `INCIDENT REPORTS\<year>\` — restricted, confirm with a person first |

## ESTATES INFORMATION

The authoritative estates source. `NSW` (11 estates), `SEQ` (385 estates),
`NSW - Driveway Regs` (20 councils), `SEQ - Driveway Regs` (10 councils), and an
intake folder `NEW JOBS AND INFORMATION TO BE ENTERED INTO ESTATES INFOMATION
FOLDER` (`NSW` / `QLD`) — note the misspelling in the real folder name.

Both `NSW` and `SEQ` contain `000 A MASTER_ESTATE_FOLDER (do not change)` — the
estate template, and the drive's **third** template pattern. New estate → copy
it; never hand-build.

Stage numbers for the new-job workflow come from here.

## DRAFTING

`Archicad`, `Codes & Products` (10 sub), `Development & Site Visits`,
`Drafting Admin` (14 sub), `ESTATES INFORMATION` (a stub — see findings),
`Standard Details`, `Structural Steel`, `Transpire Master Designs` (13 sub,
organised by storey/type: facades, single, double, auxiliary, once-off, split
level, NDIS, co-living, rear lane), plus several personal working folders.

| Document | Goes to |
|---|---|
| Standard construction detail | `Standard Details\Transpire Construction Details\` (`- DWG` for CAD) |
| House design / facade | `Transpire Master Designs\` + matching numbered subfolder |
| Code, standard, product literature | `Codes & Products\` + matching subfolder |
| Archicad template or CAD admin | `Archicad\` |
| Structural steel module | `Structural Steel\` |

## CONSTRUCTION MANAGER

`CONSTRUCTION` (mirrors `PROCEDURES & FORMS\CONSTRUCTION`), `FEEDBACK` (empty),
`FIRE ANTS`, `maintenance`, `Photos` (empty),
`Subcontractor Expression of Interest` (by trade), plus a scenario folder and a
saved-webpage folder. **80 loose files at the root** — a large uncurated
reference library of standards, product literature and one-off documents. Treat a
hit here as "someone's reference copy", and check `PROCEDURES & FORMS` for the
controlled version.

| Document | Goes to |
|---|---|
| Subcontractor EOI | `Subcontractor Expression of Interest\<trade>\` |
| Fire ant compliance material | `FIRE ANTS\` |
| Site inspection / QA form | `CONSTRUCTION\QA Forms\` |

## MAINTENANCE, SOFTWARE, Z. SUPERSEDED, ACCOUNTS

- **`MAINTENANCE`** — `FORMS` (`BOOKING SHEETS`, `DILAPIDATION REPORTS`) and
  `SS`, an archive holding one folder per completed address. Blank defect forms
  and the defect register sit at the root.
- **`SOFTWARE`** — `Cert 11072025`, `TS02 Cert`, `THEREFORE - USER MANUALS`,
  `Temp`. Contains a real `.pfx` private key at the root plus two executables.
  **Certificate and key material here is blocked** by the skill's safety rules.
- **`Z. SUPERSEDED`** — `DA search`, `Imported` (empty),
  a council application folder, and `SYDNEY` holding two old job folders. Also
  two extensionless files and a `.reg` file. Archive; never a save destination.
- **`ACCOUNTS`** — **restricted.** 17 subfolders (receivables, bank statements,
  credit applications, invoicing, manual invoices, payments, rebates, receipts,
  subcontractor pack documents and payment summaries, supplier statements) plus
  **66 loose files at the root** and one personal desktop archive. Search only
  when that is the explicit request; never in a bulk scan, and never quote
  personal or financial detail out of it.

## Naming conventions observed

- **UPPERCASE** dominates for folders and most documents, but `DRAFTING`,
  `ESTIMATING` and parts of `SALES` use mixed case. Match the local folder.
- **Numbered prefixes** (`1.`, `2.`) order folders in `ESTIMATING`, `SALES`,
  `PROCEDURES & FORMS\FENCING` and the job template — not elsewhere. Numbering
  is not always unique: `SALES` has two `3.` folders.
- **Job number leads** the name for job-specific documents.
- **Variations** use `VAR-###` folders.
- **Archives are the least consistent thing on the drive** — at least ten
  spellings: `SS` (by far the most common, appearing as a subfolder in about 15
  department folders), `1.SS`, `z.SS`, `Z. SUPERSEDED`, `SUPERSEDED`,
  `Superseded`, `13. Superseded`, `ARCHIVED`, `ARCHIVE-HANDED OVER`, `Imported`.
  Match the convention already used in that branch; don't standardise on your
  own initiative.

Before advising a filename, look at neighbouring files and copy their pattern.
It beats any rule written here.

## Housekeeping findings

Observed 10 Aug 2026. These are **reportable suggestions**, not licence to act —
every one is a change requiring approval.

- **Loose files dumped at folder roots — the drive's biggest structural problem.**
  `CONSTRUCTION MANAGER` 80, `ACCOUNTS` 66, `WORKPLACE HEALTH AND SAFETY` 26,
  `SALES` 13, `DRAFTING` 9, and 2 at the `Z:\` root itself. These are the files
  least likely to be findable by anyone but the person who saved them.
- **`OPERATIONS` cannot be read** — access denied to the account running this
  survey. It is *not* known to be empty, and must not be proposed for removal.
  Someone with access needs to say what's in it.
- **`IMPORTED` is genuinely empty** (0 files, 0 subfolders) — verified, not
  inferred from an error. A removal candidate, subject to approval.
- **`ESTATES INFORMATION` appears twice, and the top-level copy is clearly the
  live one**: it holds 11 NSW estates, 385 SEQ estates and driveway regulations
  for 30 councils, while `DRAFTING\ESTATES INFORMATION` holds a single `NSW`
  folder and one file. Treat the top-level folder as authoritative and the
  `DRAFTING` one as an abandoned stub; worth confirming before anyone deletes it.
- **730 job folders sit in in-region lifecycle folders** (`HANDED OVER`,
  `ARCHIVE-HANDED OVER`, `CANCELLED`) — more than in the live region folders.
  Two further folders under `SEQ` and `SYDNEY` are mis-parented and hold 7 job
  folders each. Worth consolidating with the top-level `COMPLETED` / `CANCELLED
  CONTRACTS`, which do the same job differently.
- **Ten archive conventions** (see above) — no single "superseded" location.
- **Personal working folders** named after individuals appear in `ACCOUNTS`,
  `DRAFTING`, `SALES` and `PROCEDURES & FORMS`. Common on shared drives and a
  real risk: when that person is away, nobody knows what's in there or whether
  it's authoritative. Flag if a search result lands in one; never recommend
  saving into one.
- **`Do Not Use` folders** in `PROCEDURES & FORMS\TO REVIEW` — clearly labelled,
  but still live. A hit from there is almost certainly superseded.
- **Duplicated reference libraries**: `CONSTRUCTION MANAGER\CONSTRUCTION` mirrors
  `PROCEDURES & FORMS\CONSTRUCTION`, and the System and Procedures Manuals exist
  in both. No indication which is controlled.
- **Server names in filenames**: drive shortcuts whose names embed the file
  server appear at the `Z:\` root and in `CONSTRUCTION MANAGER`, `DRAFTING`,
  `MAINTENANCE` and `Z. SUPERSEDED` — and they name **two different** servers, so
  at least one is stale. Filter these out of results and never repeat the
  filenames, per the skill's rule on server names.
- **Leftover files**: `Thumbs.db`, `desktop.ini`, `~$…` Office lock files, and
  extensionless junk in `Z. SUPERSEDED`. Filter out of reports rather than
  listing.
- **`ESTIMATING` is writable.** Its ReadOnly flag is folder customisation
  (`desktop.ini` is present) and Windows ignores that attribute on directories;
  its permissions match `SALES`. Earlier guidance to avoid saving there was
  wrong — treat it as writable, subject to the usual approval for any change.
- **Passwords written into filenames.** One template in the job template's
  `ESTIMATING\1. SALES\4. CUSTOMER SELECTIONS` folder carries its opening
  password in the filename, in brackets. Because it sits in
  `00000 - LOT MASTER FOLDER`, it has been copied into **every job folder**
  created from it. Anyone with drive access can read it, and it travels with
  every copy. Worth remediating (protect the file properly, or drop the password
  from the name). Handle per the skill's safety rules: give the folder path,
  never repeat the filename in full, never copy the password anywhere.

## Open questions

Needs a person to decide. Don't guess these into an answer.

- **`OPERATIONS`** — what is in it, and who has access?
- **Staleness** — how long untouched, for which document types, before something
  is worth flagging in an active job?
- **Authority** — when two versions genuinely disagree (not just one being
  older), what decides which is the real one, beyond asking? The duplicated
  reference libraries and manuals make this a live question.
- **Archive conventions** — should the ten spellings consolidate, and does any of
  it relate to job lifecycle?
- **Job lifecycle** — should in-region `HANDED OVER` / `CANCELLED` folders merge
  into the top-level `COMPLETED` / `CANCELLED CONTRACTS`?
- **`DRAFTING\ESTATES INFORMATION`** — safe to remove now the top-level copy is
  established as authoritative?
- **`IMPORTED`** — delete, or intended for something?
- **Job numbers** — issued by OnSite Companion or DataBuild? Still open in the
  Contract-Admin rules, and it affects how a new job folder gets named.
