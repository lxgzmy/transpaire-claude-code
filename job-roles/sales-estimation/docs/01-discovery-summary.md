# Sales Estimation discovery summary

Phase 2 of the Transpire AI programme. Discovery held 27 August 2026.

This is the repo copy of the discovery record, kept free of staff surnames. The
business copy (Markdown + PDF, as issued to management) sits beside the source
materials on `Z:` — see [../reference/README.md](../reference/README.md).

## 1. Sources

1. The completed **AI Integration Interview** questionnaire from the Sales
   Estimating Manager (Word document, 27 August 2026). Reviewed in full.
2. The **meeting recording** (Teams, 74 minutes, 27 August 2026). Not yet
   reviewed: the video carries no caption track, no transcript was saved beside
   it, and the Teams transcript is not reachable from the automation account.
   This summary is to be rechecked and re-issued once the transcript is provided
   (section 8, point 1).

## 2. The role

The Sales Estimating Manager prices new builds and variations and carries out
property and development research. Work arrives by email: job pricing requests,
variation requests, and queries, typically 10 to 20 emails a day with about half
being pricing requests. QLD jobs are generally handed to the QLD estimator; the
manager handles the rest.

The three activities that take the most time:

- researching a lot (or several) in a new estate or location: 30 minutes to
  3 hours without AI help
- pricing variations
- writing variations

## 3. Current workflows

### 3.1 New job pricing (email to price)

1. A pricing request arrives by email: put a particular house type on a specific
   site.
2. Review the documentation and confirm what is missing.
3. Review the land contract.
4. Confirm the 88B instrument and the 10.7 Planning Certificate are available,
   correct and current.
5. Search the LGA and State government websites for anything missing, including
   overlays and the relevant DCPs.
6. Search for relevant DA files in the DA portals or with the LGA; these can
   hold critical information.
7. Build the job folder on the `Z:` drive and save all documentation, including
   the request email.
8. Complete site costs. The manager wants this to remain a manual task.
9. Confirm building setbacks and the building envelope dimensions.
10. Select a standard design that fits the envelope and complies with the brief,
    and price any requested design changes.
11. Fill out the job costing sheet, which loads the job into the Sales Costing
    Register (SCR).
12. Respond to the Sales Manager by email with the price.

### 3.2 Variations

Variation requests arrive by email. Pricing and writing them is fully manual,
with no system currently in place that works. The manager names variations as
the most time-consuming part of the role for exactly that reason. There is no
record of variations anywhere outside the individual job folders in `PROJECTS`.

### 3.3 Lot and estate research

Research always starts the same way (setbacks, zoning, overlays) and then
branches depending on what turns up. Sources include LGA and State planning
websites, DA portals and Archistar (overlays and current aerial imagery). The
most time goes on Development Approval information, including filtering out
superseded documents.

### 3.4 Records and filing

- Pre-contract jobs live under `Z:\ESTATES INFORMATION`; jobs under contract
  live under `Z:\PROJECTS`.
- The same documents are also stored in Onsite Companion, but the manager works
  from the `Z:` drive.
- Emails are kept in Outlook folders and copied into the job folders.
- The SCR is the one standard document senior management reviews regularly.
- The manager's own Excel workbook (estimating notes, quick pricing, folder
  shortcuts) is the first program opened every day.

## 4. Systems and data

| System | Used for |
|---|---|
| Outlook | All incoming work (pricing requests, variation requests, queries) and the responses |
| Excel | Job costing sheet, the SCR, and the personal estimating workbook |
| Word | Documents, including variation writing |
| Bluebeam Revu | All site and house pricing markups (PDF editing) |
| Archistar | Identifying overlays and viewing current aerial imagery |
| `Z:` drive | `ESTATES INFORMATION` (pre-contract) and `PROJECTS` (under contract) |
| Onsite Companion | Holds copies of the job documents; not the manager's working surface |
| Claude (own assistant) | In use for about six months, mainly land contract review and research |

The manager reports no systems that clash or force the same information to be
entered twice.

## 5. Pain points, bottlenecks and risks

1. **Variations have no system.** The most time-consuming task in the role.
   Pricing and writing are manual, and there is no register of variations
   outside the job folders.
2. **Research time.** 30 minutes to 3 hours per lot without AI assistance, and
   it is daily work.
3. **Incomplete or wrong information from sales staff.** Missing or incorrect
   88B instruments, and land contracts that do not match the land being priced.
   Regular chasing follows.
4. **Hard to find past work.** NSW jobs are filed by LGA inside
   `ESTATES INFORMATION`, but nobody mentions the LGA when they ask about a
   job. Finding a job priced six months earlier can take five minutes or more.
5. **SCR entry errors (historic).** Filling the SCR by hand was the single
   biggest source of mistakes (an incorrect formula or entry). The manager's
   job costing sheet has eliminated this.
6. **Overlooked land contract notes (historic).** A critical note in a land
   contract could be missed. The manager's Claude-assisted review has removed
   this problem.
7. **Key-person knowledge.** Pricing notes, shortcuts and method live in one
   person's workbook and head, with a second estimator covering QLD.
8. **Superseded DA documents** pollute research results and cost time to filter
   out.

## 6. Already working with AI

The manager introduced a Claude assistant into the role about six months ago on
his own initiative. Land contract review is the standout result (critical notes
are no longer missed) and research is faster. His own words on the workflow:
everything was manual before the assistant arrived.

This phase builds on that foundation rather than replacing it: capture what
already works into shared, reviewable skills in the company setup, so the
capability is not tied to one person's private configuration.

## 7. AI use cases, prioritised

Ratings weigh time saved, how soon it could work, and what could go wrong. They
are our assessment; the order needs the manager's confirmation. Specs (all
**proposed, not built**) live in [../workflows/README.md](../workflows/README.md).

| # | Use case | Value | Feasibility | Risk |
|---|---|---|---|---|
| 1 | Lot and DA research brief (zoning, overlays, DCPs, DA history with superseded documents flagged, EPA information; every claim cited to its source) | High | Medium | Medium |
| 2 | Pricing request intake and completeness check (land contract, 88B, 10.7 present, current, matching the lot; chase-up email drafted; job folder built and filed) | High | High | Low |
| 3 | Land contract / 88B / 10.7 review checklist (formalises the manager's existing AI review; flagged summary a person verifies) | High | High | Low |
| 4 | Variation writing and a variation register (drafting from a priced input; pricing assistance later, once rate sources are settled) | High | Medium | Medium |
| 5 | Priced-job finder (by lot, address, client or estate, regardless of LGA folder) | Medium | High | Low |
| 6 | Price response email drafts (from the completed costing, using existing templates) | Medium | High | Low |
| 7 | SCR validation checks (cross-check register entries against job costing sheets; later safety net) | Low | Medium | Low |

**Boundaries from the questionnaire:** site costs stay manual, Bluebeam markups
stay with the manager, and nothing prices a job on its own. Every output is a
draft for review.

**Suggested build order.** Use case 1 is the manager's explicit first ask and
the biggest time saving, so it leads. Use cases 2, 3, 5 and 6 are quick wins on
patterns already proven in the Contract Admin phase (email extraction, document
checks, folder creation, drafted emails) and can land alongside it. Use case 4
is the biggest structural gap but needs its rules and rate sources settled
first, so it follows as its own stage, writing before pricing.

## 8. Missing information and questions

1. **The meeting transcript** (see section 1). Download it from the meeting's
   Recap tab in Teams and save it beside the recording.
2. **Sample documents:** the job costing sheet, the SCR, two or three completed
   variations (priced and written), the template response emails, and the
   personal estimating workbook if the manager is comfortable sharing it.
3. **Variation rate sources:** supplier agreements, subcontractor rates, the
   DataBuild price file under `ESTIMATING`, or the manager's own notes?
   DataBuild has no API (confirmed 23 August 2026), so any pricing help reads
   exported files, never the system.
4. **The QLD handoff:** what the QLD estimator receives, what he returns, and
   whether QLD research runs through different portals than NSW.
5. **Which DA portals:** the questionnaire mentions "DP Online"; confirm the
   exact portals per region.
6. **Archistar:** which licence or plan, and whether API access exists.
7. **Onsite Companion:** does anything in this role need to be written into
   OSC, or is `Z:` filing enough?
8. **Volumes and targets:** jobs priced and variations completed per week, and
   expected turnaround for each.
9. **The existing assistant:** which Claude product, what data goes into it
   (land contracts carry client details), and whether to move those prompts and
   workflows into the shared, reviewed setup.
10. **Access:** confirm the automation account can read the
    `ESTATES INFORMATION`, `PROJECTS`, `ESTIMATING` and `SALES` branches it
    would need.
11. **The estates filing problem:** fix the LGA-folder layout itself, or let
    the finder cope with it? Restructuring live folders affects other staff, so
    it is a separate decision.

## 9. Next steps

1. Transcript provided → fold it in and re-issue this summary.
2. Collect the sample documents into `reference/` pointers.
3. Confirm use-case priorities and boundaries with the Sales Estimating Manager.
4. Transcribe the first rules (`rules/`), then build the first workflows
   read-only and draft-first, mirroring the Contract Admin pattern.
