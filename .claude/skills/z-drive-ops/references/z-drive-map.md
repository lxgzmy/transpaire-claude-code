# Map of the Z: share

What lives where on `Z:`, so save advice and searches land in the right place.

**How this was built:** a read-only, depth-2 listing of folder *names* on
4 Aug 2026. No business file was opened. Folder contents below depth 2 are
described only where they were checked directly.

**Deliberately not recorded here:** client names and addresses, staff names,
server names. Job folders are described by *pattern*, not listed. Several
folders are named after individual staff members — treat those as personal
working folders (see [Housekeeping findings](#housekeeping-findings)) rather
than a filing location to recommend.

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
the relevant department folder.

## Top-level folders

| Folder | Holds | Notes |
|---|---|---|
| `ACCOUNTS` | Finance: receivables, bank statements and reconciliations, invoicing, payments, receipts, rebates, credit applications, subcontractor pack documents | **Restricted** — see the skill's safety rules |
| `ADMINISTRATION` | Day-to-day admin: email templates, handover, key register, insurance, meetings, reports, supervisor file, utilities, socials | Broad; check subfolders before advising |
| `CLAUDE CODE` | This automation project and its Cowork projects | Not business records. Don't file business documents here |
| `COMPANY GENERAL INFORMATION` | Company identity: logo, profile, brochure, licences, staff lists and photos, supervisors | Contains a **blocked** credentials folder and staff personal information |
| `CONSTRUCTION MANAGER` | Construction management material, site visits, feedback, maintenance, photos, subcontractor EOIs | |
| `DRAFTING` | Archicad files, standard details, structural steel, master designs, codes and products, site visits | Also has its own `ESTATES INFORMATION` copy — see findings |
| `ESTATES INFORMATION` | Estate and stage information by region (NSW, SEQ), driveway regulations, design guideline register | Used by the new-job workflow for stage numbers |
| `ESTIMATING` | Contracts and inclusions, supplier agreements, subcontractor rates, DataBuild price file and processes, OnSite Companion database, production and sales estimating | Numbered `1.`–`13.` prefixes. Marked read-only at the folder level — don't propose writing here without checking |
| `IMPORTED` | Nothing — completely empty | See findings |
| `MAINTENANCE` | Maintenance forms and an archive subfolder | |
| `OPERATIONS` | Nothing — completely empty | See findings |
| `PROCEDURES & FORMS` | The company's procedures and blank forms, mirrored by department; includes the System and Procedures Manuals and the variation contract templates | This is *procedure and template* material — the blank form, not a completed one |
| `PROJECTS` | **All job records.** See below | The job-shaped part of the drive |
| `SALES` | Packages by region, marketing brochures and agreements, land contracts, finance approvals, floor plan ideas | Loosest structure on the drive — many ad-hoc folders |
| `SOFTWARE` | Software certificates and user manuals | Certificate files are blocked — see safety rules |
| `WORKPLACE HEALTH AND SAFETY` | Audits, SWMS, certificates of currency, toolbox talks, safety packs | `INCIDENT REPORTS` holds personal/health information — handle with care |
| `Z. SUPERSEDED` | Mixed archive: an old DA search, a named council application, a region folder, stray files | General archive, **not** a per-job lifecycle stage |

## Inside `Z:\PROJECTS`

**Regions:** `CUDGEN`, `GUNNEDAH`, `SEQ`, `SYDNEY`, `TAMWORTH`.

**Lifecycle sits beside the regions, not inside them:** `CANCELLED CONTRACTS`
and `COMPLETED CONTRACTS` are siblings of the region folders. A finished job
moves out of its region folder into `COMPLETED CONTRACTS`. So **searching one
region is not searching all jobs** — if a job isn't in its region, check the
completed and cancelled folders before concluding it doesn't exist.

Also present: `MARK UP'S` and `z.SS` (another archive).

**Job folder names** follow: `<5-digit job number> - LOT <lot> <STREET>,
<SUBURB> <STATE>`. The number's first two digits are the year (e.g. `26###` =
2026). Searching by job number is the most reliable way to find a job; street
spellings and punctuation vary.

**The document-type template.** Every region contains
`00000 - LOT MASTER FOLDER` — the template copied for each new job. This is the
authoritative answer to "which subfolder?":

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

## Naming conventions observed

- **UPPERCASE** dominates for folders and most documents.
- **Numbered prefixes** (`1.`, `2.`) order folders in `ESTIMATING` and `SALES`
  and inside the job template — but not elsewhere on the drive.
- **Job number leads** the name for job-specific documents.
- **Variations** use `VAR-###` folders.
- **Archives** are inconsistent: `Z. SUPERSEDED`, `z.SS`, `SS`, `13. Superseded`
  all appear. When advising, match the convention already used in that branch;
  don't standardise on your own initiative.

Before advising a filename, look at neighbouring files and copy their pattern.
It beats any rule written here.

## Housekeeping findings

Observed on 4 Aug 2026. These are **reportable suggestions**, not licence to
act — every one is a change requiring approval.

- **`IMPORTED` and `OPERATIONS` are completely empty** (no files, no subfolders).
  Candidates for removal, or they're placeholders someone intended to use.
- **`ESTATES INFORMATION` exists twice**: at the top level and inside
  `DRAFTING`. Unclear which is current. Worth confirming, since the new-job
  workflow reads estate/stage information — searching the wrong one gives stale
  answers. Check both until this is resolved.
- **Four different archive conventions** (see above) — no single "superseded"
  location.
- **Personal working folders** named after individuals appear inside `ACCOUNTS`,
  `DRAFTING`, and `SALES`. Common on shared drives and a real risk: when that
  person is away, nobody knows what's in there or whether it's authoritative.
  Flag if a search result lands in one; don't recommend saving into one.
- **`SALES` has the loosest structure** — many one-off folders alongside the
  numbered ones. Expect searches here to need more than one attempt.
- **Leftover files**: `Thumbs.db` and `~$…` Office lock files scattered around,
  including at the drive root. Harmless but noise in search results — filter
  them out of reports rather than listing them.
- **`ESTIMATING` is marked read-only** at the folder level. Check before
  suggesting anything be saved there.
- **Passwords written into filenames.** At least one variation template carries
  its opening password in the filename, in brackets. Because it sits in the
  `00000 - LOT MASTER FOLDER` template, it has been copied into **every job
  folder** created from it. Anyone with drive access can read it, and it travels
  with every copy. Worth remediating (protect the file properly, or drop the
  password from the name). Handle per the skill's safety rules: give the folder
  path, never repeat the filename in full, never copy the password anywhere.

## Open questions

Needs a person to decide. Don't guess these into an answer.

- **Staleness** — how long untouched, for which document types, before something
  is worth flagging in an active job?
- **Authority** — when two versions genuinely disagree (not just one being
  older), what decides which is the real one, beyond asking?
- **`Z. SUPERSEDED`, `z.SS`, `SS`** — should these consolidate, and does any of
  it relate to job lifecycle?
- **`ESTATES INFORMATION`** — which copy is authoritative?
- **`IMPORTED` / `OPERATIONS`** — delete, or are they intended for something?
- **Job numbers** — issued by OnSite Companion or DataBuild? Still open in the
  Contract-Admin rules, and it affects how a new job folder gets named.
