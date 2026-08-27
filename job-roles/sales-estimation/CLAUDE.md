# CLAUDE.md — Sales Estimation (job-role)

Scoped context for the Sales Estimation job-role. The org-wide guardrails in the
repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Sales estimating for Transpire (Australian residential home builder): lot
feasibility assessment, pricing new builds and variations, and property and
development research. **Land itself is never priced.** The role is held by the
Sales Estimating Manager, with a second estimator covering QLD; feasibility
reports are reviewed by the Estimating Manager. Claude assists by reading
requests, researching lots and approvals, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only.

## Status

**Discovery complete, nothing built.** Discovery ran on 27 August 2026 from
three sources, all reviewed in full: the questionnaire, the meeting transcript,
and the manager's handed-over materials in `Z:\AI test\Sale Estimating\` (see
`reference/README.md`). The discovery record is
[docs/01-discovery-summary.md](docs/01-discovery-summary.md), version 2.

The meeting fixed the build order: **land assessment first, then variations.**
The manager handed over a working personal setup (project instructions, NSW and
QLD knowledge bases, a packaged lot-research skill), so the land assessment
build is transcription and hardening, not invention. Two rule conflicts found
in the materials review block transcription until the manager settles them:

1. **Pricing in reports** — his project instructions say include sourced
   figures with attribution; his QLD rules and skill say never include dollar
   amounts (Excel is the source of truth); his NSW rules carry a half-edited
   sentence that reads both ways. The report template hangs off this.
2. **MSDG Guideline 7 trigger** — newer materials let a clear document
   statement trigger the NSW hard stop directly; older wording requires manual
   confirmation. Align when transcribing (QLD never auto-triggers).

**Propose any workflow or skill before building it** (org rule), and do not
build against untranscribed rules. Do not transcribe past an unresolved
conflict.

## Scope (proposed, not built)

Six candidate use cases from discovery. Specs live in
[workflows/README.md](workflows/README.md).

1. **Land assessment, end to end** — agreed first build. Pricing request from
   email → research → nine-section feasibility report (every claim cited) →
   estate/stage/lot folder and `SALES ESTIMATING` subfolder created or
   verified → saved.
2. **Variations assistant** — agreed second. Standard-item matching against the
   NSW/QLD master variation books, historical lookup, terminology rewrite,
   pre-populated variation sheet, and a variation register. Every figure is a
   draft a person confirms.
3. **Price response email drafts** — drafted from the completed costing, never
   sent automatically.
4. **SCR reporting** — reports out of the register on request or schedule; the
   register itself stays as the manager built it.
5. **Priced-job finder** — largely covered by the org-wide `z-drive-ops` skill.
6. **Duplicate document detection** in estate folders — report-only.

**Boundaries set in discovery:** site costs stay manual, Bluebeam pricing
markups stay with the manager, land is never priced, nothing prices a job on
its own. Plan-geometry pricing is parked as the long-term goal.

## Systems

Outlook (all work arrives by email: 10 to 20 a day, about half pricing
requests), Excel (the manager's macro-enabled job costing workbooks for NSW and
QLD, which update the Sales Costing Register on print; the SCR is reviewed by
senior management), Word, Bluebeam Revu (manual markups), Archistar
(Professional Standard subscription with Nearmap; primary research tool; no
public API), NSW Planning Portal Spatial Viewer, PD Online and council sites,
Queensland Globe (QLD overlays; hard to navigate), public registers (subsidence,
contamination, bushfire, flood, aircraft noise), the `Z:` share
(`ESTATES INFORMATION` pre-contract; `PROJECTS` under contract), Onsite
Companion (document copies; the OSC connection is the programme's current top
priority, vendor-dependent).

DataBuild has no API (confirmed org-wide 23 August 2026) — it appears only
downstream in contract administration's variation documents.

## Rules & knowledge

- `rules/` — **none transcribed yet.** The transcription sources are the
  manager's handed-over knowledge bases (NSW and QLD estimating rules, project
  instructions, siting guide, link library — see `reference/README.md`), not
  guesses. Transcription starts after the two conflicts above are settled, and
  the accumulated corrections from his personal account's project should be
  harvested first so the Errors and Corrections Log starts populated.
- [docs/01-discovery-summary.md](docs/01-discovery-summary.md) — the discovery
  record this role was founded on, including the materials review.
- `reference/` — pointers to the source materials on `Z:`. They stay on `Z:`
  and are never copied into the repo.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\sales-estimation\{state,evidence,outputs,logs,reports,temp}\`
— git-ignored. Created 27 August 2026. `evidence\nick-materials\` holds the
unpacked working copy of the manager's packaged skill.

## Human-in-the-loop

Every price, research brief, feasibility report, variation document, register
entry, chase-up and response email is a **draft with an evidence bundle** for
review. Research output cites its sources (which portal, which document,
retrieved when) so a person can verify before a price relies on it; the
manager's own no-guessing rule (not 100 per cent certain → say so, do not
guess) is adopted as a role rule. The MSDG Guideline 7 hard stop is always
escalated to the Estimating Manager. No sanctioned automation exceptions exist
for this role — contract-admin's CD-7.7 save exception does not extend here.
Nothing is sent, filed as final, or written to a system of record without
explicit approval.
