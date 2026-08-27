# Sales Estimation discovery summary

Phase 2 of the Transpire AI programme. Discovery held 27 August 2026. **Version 2**
(supersedes version 1 of the same date: adds the meeting transcript and the review
of the manager's handed-over materials).

This is the repo copy of the discovery record, kept free of staff surnames. The
business copy (Markdown + PDF, as issued to management) sits beside the source
materials on `Z:` — see [../reference/README.md](../reference/README.md).

## 1. Sources

All three reviewed in full:

1. The completed **AI Integration Interview** questionnaire from the Sales
   Estimating Manager (Word document, 27 August 2026).
2. The **meeting transcript** (Teams recording, 74 minutes, 27 August 2026;
   automated transcript, so garbled passages were treated with caution and
   nothing uncertain is stated as fact).
3. The manager's **handed-over materials**: six files in
   `Z:\AI test\Sale Estimating\` (project instructions, NSW and QLD estimating
   rules, a packaged lot-research skill, a state government link library, his
   NSW house siting guide). Reviewed in section 6; reviewed, not copied.

The meeting confirmed the delivery model contract-admin already runs: rules and
skills formalised in this repository, simulation-tested, released as a draft
version to the role for feedback, promoted only when accuracy is proven (the
target discussed was 95 to 98 per cent).

## 2. The role

The Sales Estimating Manager assesses lot feasibility and prices site works,
new builds and variations, with property and development research underneath
all of it. **Land itself is never priced.** Work arrives by email: job pricing
requests, variation requests, and queries, typically 10 to 20 emails a day with
about half being pricing requests. QLD jobs are generally handed to the QLD
estimator; the manager handles the rest. Feasibility reports are reviewed by
the Estimating Manager (the manager's direct report line). In the meeting the
manager confirmed the role is essentially two streams, job pricing and
variations, with little outside them.

The manager is also the most experienced Claude user in the office: about six
months building his own assistant, including a packaged skill, two maintained
rules documents and a working error-correction habit. He agreed to co-lead the
role's build, was set up with Claude Code on this repository during the
session, and handed his materials over the same day.

The three activities that take the most time:

- researching a lot (or several) in a new estate or location: 30 minutes to
  3 hours without AI help
- pricing variations
- writing variations

## 3. Current workflows

### 3.1 New job pricing (email to price)

A pricing request arrives by email from sales staff: put a particular house
type on a specific site. The research runs in a consistent order:

1. Determine the environmental planning zone and which code the lot is
   assessed under (NSW Planning Portal; the siting guide documents the
   Greenfield versus non-Greenfield determination, SEPP Codes Part 3C versus
   Part 3).
2. Find the setbacks (NSW Planning Portal; time consuming; the siting guide
   codifies the method: setback tables by lot area, articulation zone, garage
   rules, wall heights).
3. If development documentation is missing, search PD Online or the council's
   website for the development approvals and pull the documents.
4. Identify overlays: Archistar or the NSW Planning Portal in NSW; in QLD,
   council websites or the Queensland Globe, which the manager finds very
   difficult to navigate.
5. Review the land contract and the 88B instrument. The 88B directs the review
   onward to further documents (acoustic reports, bushfire reports); sometimes
   the supplied report is not the one the 88B refers to, which sends the search
   back to the DA records. Mining subsidence (MSDG) is always checked, with
   Guideline 7 a hard stop escalated to the Estimating Manager. Land contracts
   can run past 900 pages and must be split before review.
6. Build or verify the lot folder under the estate in `Z:\ESTATES INFORMATION`
   and save all documentation including the request email. Sales staff usually
   create lot folders but the manager often does, along with a
   `SALES ESTIMATING` subfolder that sales staff never create.
7. Complete site costs. The manager wants this to remain manual.
8. Confirm the building envelope, select a standard design that fits, and
   price any requested design changes.
9. Fill out the job costing workbook (one for NSW, one for QLD, macro-enabled,
   built by the manager). Hitting print updates the Sales Costing Register
   automatically, writes a backup, and saves Excel and PDF copies of the sheet,
   which he files into the job folder. The old SCR needed every formula entered
   by hand and was where nearly every error came from; the workbooks eliminated
   that.
10. Respond to the Sales Manager by email with the price, from template
    responses.

### 3.2 Variations

Two streams. Pre-contract: the client requests changes before the contract;
the manager prices them and accepted items go into the contract as special
inclusions or conditions (the same material the contract-admin automation must
pick up, which is why a standardised request format is planned there too).
Post-contract: after signing, clients raise further changes, usually upgrades.

The flow today: a variation request email lists items often written by the
client in non-technical language, sometimes on a wrong understanding, so they
need human interpretation. The manager prices each item or explains why it is
not doable, fills out a variation sheet (Excel) that goes to the client for a
yes or no per item, and once items are confirmed, contract administration
creates the formal variation document in Onsite Companion and DataBuild;
customer service sends the PDF for signing.

There is no system behind any of this. Pricing and writing are manual, and
there is no register of variations outside the job folders in `PROJECTS`. The
manager previously built an HTML tool holding a library of past variations that
suggested matching wording; it is lost, but it is the direction he wants.
Master variation books exist for NSW and QLD (different items and prices), and
the meeting's estimate was that around half of variation requests are standard
items that could be matched and priced from them.

### 3.3 Records and filing

- Pre-contract jobs live under `Z:\ESTATES INFORMATION` (NSW and SEQ, then
  estate, stage, lot); jobs under contract under `Z:\PROJECTS`.
- The same documents are also stored in Onsite Companion, but the manager works
  from the `Z:` drive.
- Emails are kept in Outlook folders and copied into job folders.
- The SCR is the one standard document senior management reviews regularly.
- Sales staff drag documents loose into estate folders and re-save documents
  already held (some folders hold ten identical design guidelines); the manager
  re-files and filters.
- The manager's own Excel workbook (notes, quick pricing, folder shortcuts) is
  the first program opened every day.

## 4. Systems and data

| System | Used for |
|---|---|
| Outlook | All incoming work and responses |
| Excel | Job costing workbooks (NSW and QLD, macro-enabled), the SCR, the variation sheet, the personal workbook |
| Word | Documents, including variation writing and feasibility reports |
| Bluebeam Revu | All site and house pricing markups (manual) |
| Archistar | Primary research tool: zone, overlays, planning rules, Nearmap imagery. Professional Standard subscription; no public API |
| NSW Planning Portal Spatial Viewer | Zoning, codes, setbacks, overlays, MSDG levels (NSW) |
| PD Online and council websites | Development approvals and documents |
| Queensland Globe | QLD overlays; difficult to navigate |
| Public registers | Subsidence Advisory NSW, NSW EPA and QLD DES contaminated land registers, NSW RFS bushfire mapping, QLD Flood Check, Urban Utilities GIS, Defence aircraft noise (from the manager's curated link library) |
| `Z:` drive | `ESTATES INFORMATION` (pre-contract) and `PROJECTS` (under contract) |
| Onsite Companion | Holds document copies; not the working surface. Connecting Claude to OSC is the programme's current top priority, waiting on the vendor |
| Claude | Six months on a personal account, moving onto the company setup; Claude Code for automation, Cowork for simple local work |

No systems clash or force double entry. DataBuild appears only downstream in
contract administration's variation documents and has no API (confirmed
23 August 2026).

## 5. Pain points, bottlenecks and risks

1. **Variations have no system.** The most time-consuming work; manual pricing
   and writing; no register outside job folders.
2. **Research time.** 30 minutes to 3 hours per lot, daily.
3. **Queensland overlays.** The Queensland Globe is very hard to navigate; QLD
   differs from NSW throughout (planning framework, documents, no 10.7
   certificate), which the manager's rules documents capture properly.
4. **Incomplete or wrong information from sales staff.** Missing or wrong 88B
   instruments, land contracts that do not match the land, supplied reports
   that are not the ones the 88B names. Regular chasing.
5. **Very large land contracts.** 900-plus pages; must be split before AI
   review (his skill already carries the splitting and chunked-reading
   procedure).
6. **Estate folder hygiene.** Loose documents, duplicates saved repeatedly,
   missing `SALES ESTIMATING` subfolders, and the risk of filing a lot against
   the wrong stage in complex staged estates.
7. **Hard to find past work.** NSW jobs filed by LGA that nobody mentions;
   five minutes or more to find a job priced six months ago.
8. **SCR entry errors (historic).** Fixed by the costing workbooks.
9. **Overlooked contract notes (historic).** Fixed by his AI review;
   self-assessed above 90 per cent accuracy, known failure mode is the
   occasional false positive (one wrongly flagged acoustic report in an 85-lot
   batch), and his standing rule is: not 100 per cent certain, do not guess,
   say so.
10. **Key-person dependency.** The method now exists on paper (section 6), but
    the accumulated corrections from six months of use live in his personal
    account's project, not yet in the handed-over documents.

## 6. Review of the manager's handed-over materials

Six files in `Z:\AI test\Sale Estimating\`, all reviewed in full. A working
copy of the unpacked skill sits in the role's git-ignored runtime evidence
folder; nothing has been copied into the repo.

| File | What it is |
|---|---|
| `Sales_Estimating_Project_Instructions.docx` | The governance layer: purpose and scope (feasibility and site works, never price land), hard rules, people and reporting lines, tools, report standards, a maintenance loop |
| `NSW_estimating_rules.docx` (updated Aug 2026) | NSW knowledge base: MSDG rules including the Guideline 7 hard stop, contamination checks, acoustic categories, 13 site cost flag items (BONS, tight site under 12.5 m frontage, BAL, E class soil, retaining, deepened edge beam with its m² formula, piering and more), setback rules, draft-document handling, plus live sections for council and estate quirks and an errors log |
| `Transpire_QLD_Estimating_Rules.docx` (updated Jun 2026) | QLD knowledge base, deeper again: QLD planning framework (Planning Act 2016, council schemes, assessment categories), QLD document types (Disclosure Plan, Plan of Development, body corporate), SEQ overlays (flood, acid sulfate soils, vegetation, character, waterway corridors, aircraft noise), 17 flag items including the Small Job Fee under 170 m², and a registration-estimates policy (never trust developer dates; use Nearmap imagery and his own estimate) |
| `lot-research.skill` | A packaged, properly structured Claude skill (SKILL.md plus NSW and QLD report-structure references): state detection, large-document handling (upload failure workarounds, 15 to 20 page chunked reading, scanned-page flags), web-search fallback against named public registers labelled "web-verified — confirm in Archistar", MSDG Guideline 7 hard-stop logic, and a nine-section Lot Feasibility Report ending in "Key Risks and Actions Required" written for the Estimating Manager to read first, produced as Word output with a set filename convention |
| `State Government URL's.docx` | Curated link library: SEPP Codes (Housing, Greenfield, Inland), Spatial Viewer, DA tracking, Subsidence Advisory, QLD Flood Check, Queensland Globe, Urban Utilities GIS, aircraft noise |
| `NSW_House_Siting_Guide - Nick.pdf` | The siting method as a reference card: Greenfield determination, gross floor area exclusions, setback tables, articulation zone, garage and driveway rules, including at least one Transpire-specific rule (the 3 m secondary-frontage garage setback) |

**Assessment.** Much further along than discovery usually finds. The
architecture is already right: a stable workflow (the skill) kept separate from
evolving rules (the two knowledge bases), with an explicit precedence rule that
the knowledge bases win. That maps directly onto this repo's `rules/` versus
`workflows/`/`skills/` split, so the land assessment build is a transcription
and hardening job, not an invention job. The safety habits the programme
requires are already encoded: never guess, cite the source of every figure and
flag, label web-sourced data as needing confirmation, flag draft documents,
treat setbacks as indicative, escalate the hard stop.

**Conflicts and gaps found in review** (each needs the manager's confirmation
before rules are transcribed — this is why the materials are reviewed, not
copied):

1. **Dollar amounts in reports contradict across the documents.** The project
   instructions say include pricing when it can be sourced (documents, model
   knowledge, web search) with the source stated. The QLD rules and the skill
   say never include dollar amounts; the Excel workbook is the source of truth.
   The NSW rules contain a half-edited sentence that reads both ways. The
   report template hangs off this rule, so it is settled first.
2. **The MSDG Guideline 7 trigger changed at some point.** The skill and
   instructions let a clear document statement trigger the NSW hard stop
   directly ("no longer requires manual confirmation"); the QLD document still
   requires manual confirmation in all cases (consistent for QLD, but wording
   should be aligned when transcribed).
3. **The living sections are empty.** Known Council and Estate Rules and the
   Errors and Corrections Log are scaffolds with no entries; six months of
   accumulated corrections live in the personal account's project memory and
   should be harvested before that account is wound back.
4. **New design pricing is marked "details TBC"** in his own instructions.
5. **Nothing in the handover covers variations.** The lost HTML tool leaves the
   variations build starting from the master variation books and the meeting's
   description only.
6. **The costing workbooks, SCR, variation books and template emails were
   named but not provided.**
7. **The skill is written for a chat-upload environment** (upload timeouts,
   drag-and-drop). Here the same workflow reads directly from the `Z:` drive
   and Outlook, so those steps get re-targeted rather than copied.

## 7. AI use cases, prioritised

The meeting settled the build order explicitly: **land assessment first, then
variations.** Specs (all **proposed, not built**) live in
[../workflows/README.md](../workflows/README.md).

| # | Use case | Value | Feasibility | Risk |
|---|---|---|---|---|
| 1 | Land assessment, end to end (**agreed first build**): pricing request from email → research (zone/code, setbacks, overlays incl. QLD sources, DA documents with superseded flagged) → land contract, 88B and dependent reports reviewed under the no-guessing rule, oversized documents split → nine-section feasibility report, every claim cited → estate/stage/lot folder and `SALES ESTIMATING` subfolder created or verified → report and documents saved | High | High (working personal v0 exists; transcription and hardening once the section 6 conflicts are settled) | Medium |
| 2 | Variations assistant (**agreed second**): recognise the request email; match standard items to the NSW/QLD master variation book with reference price (~half of requests); search past variations within an agreed window; rewrite client wording into correct terminology; pre-populate the variation sheet; keep a register. Every figure is a draft a person confirms | High | Medium (starts from far less material) | Medium |
| 3 | Price response email drafts from the completed costing, using existing templates; drafted, never sent automatically (agreed in the meeting) | Medium | High | Low |
| 4 | SCR reporting: produce reports out of the SCR on request or schedule (the manager's own ask; the register itself does not need automating). Role dashboards are on the programme roadmap for later | Medium | High | Low |
| 5 | Priced-job finder by lot, address, client or estate, regardless of LGA folder (the org-wide `z-drive-ops` skill already covers much of this) | Medium | High | Low |
| 6 | Duplicate document detection in estate folders; report-only drive hygiene | Low | High | Low |

**Boundaries (standing):** site costs stay manual, Bluebeam markups stay with
the manager, land is never priced, nothing prices a job or sends anything on
its own, every output is a draft for review. Plan-geometry pricing was parked
as the long-term goal.

**Supporting decisions from the meeting:** a standardised pricing-request email
format (matching the contract-request standardisation underway) so requests
state the estate and stage reliably; a folder and naming convention for sales
estimating outputs, which the manager was asked to nominate; and the Onsite
Companion connection, the programme's current top priority.

## 8. Missing information and questions

The transcript and the handover closed most of version 1's questions (portals
confirmed; Archistar is Professional Standard with Nearmap, no API; the
existing assistant is documented and being handed over; QLD differences are
documented). Still open:

1. **The pricing-in-reports rule** (section 6, item 1): dollars included with
   sources, or flags only. Settle before the report template is transcribed.
2. **The corrections history**: harvest the accumulated corrections and
   council/estate quirks from the personal account's project before it is
   wound back; seed the Errors and Corrections Log with them.
3. **Folder structure and naming**: the manager to nominate the structure
   (action from the meeting, feedback expected within the week).
4. **Remaining documents to collect**: the two costing workbooks, the current
   SCR, the master variation books, the variation sheet, two or three completed
   variations, the template response emails.
5. **Variation price escalation**: confirmed policy for aging past prices
   (his example: three or six per cent over 12 months) before pricing
   suggestions are built.
6. **Onsite Companion connection**: vendor-dependent; land assessment is being
   built against the `Z:` drive in the meantime.
7. **Volumes and targets**: jobs priced and variations completed per week, and
   expected turnaround (not covered in the meeting).
8. **Access**: confirm the automation account can read `ESTATES INFORMATION`,
   `PROJECTS`, `ESTIMATING` and `SALES`.
9. **The estates filing problem**: fix the LGA-folder layout or let the finder
   cope; restructuring live folders affects other staff, so it is a separate
   decision.

## 9. Next steps

1. Settle the two rule conflicts with the manager (pricing in reports; MSDG
   trigger wording) and harvest the corrections history from his personal
   project.
2. Transcribe his knowledge bases and skill into this role's `rules/` and
   `workflows/` (formalisation, not copying; re-targeted to read from the `Z:`
   drive and Outlook). **Nothing is being built yet** — transcription and specs
   precede any skill authoring, per the org rule.
3. The manager nominates the folder and naming structure and drops the
   remaining documents into `Z:\AI test\Sale Estimating\`.
4. Then build land assessment version 0.1: simulation-tested, released to the
   role for real-use feedback, promoted only when accuracy is proven.
   Variations follow as the second build.
5. Progress the Onsite Companion connection with the vendor (programme-level
   priority).
