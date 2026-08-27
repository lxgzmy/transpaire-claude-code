# CLAUDE.md — Sales Estimation (job-role)

Scoped context for the Sales Estimation job-role. The org-wide guardrails in the
repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Sales estimating for Transpire (Australian residential home builder): pricing new
builds and variations, plus property and development research. The role is held by
the Sales Estimating Manager, with a second estimator covering QLD. Claude assists
by reading requests, researching lots and approvals, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only.

## Status

**Discovery complete, nothing built.** Discovery ran on 27 August 2026: the
completed AI Integration Interview questionnaire has been reviewed in full; the
meeting recording (74 min, Teams) is pending its transcript (see
`reference/README.md`). The discovery record is
[docs/01-discovery-summary.md](docs/01-discovery-summary.md); use-case priorities
still need the Sales Estimating Manager's confirmation.

**Propose any workflow or skill before building it** (org rule), and do not build
against guessed rules — no rules have been transcribed yet.

## Scope (proposed, not built)

Seven candidate use cases from discovery, in suggested order. Specs live in
[workflows/README.md](workflows/README.md).

1. **Lot and DA research brief** — the manager's explicit first ask.
2. **Pricing request intake and completeness check** (land contract, 88B, 10.7).
3. **Land contract / 88B / 10.7 review checklist** — formalises the manager's
   existing AI-assisted review.
4. **Variation writing and a variation register** — the biggest structural gap;
   pricing assistance only after rate sources are settled.
5. **Priced-job finder** across the LGA-filed estates folders.
6. **Price response email drafts** from the completed costing.
7. **SCR validation checks** (later; the manual-entry risk is already fixed).

**Boundaries set in discovery:** site costs stay manual, Bluebeam pricing markups
stay with the manager, and nothing prices a job on its own.

## Systems

Outlook (all work arrives by email: 10 to 20 a day, about half pricing requests),
Excel (job costing sheet, which loads the Sales Costing Register; the SCR is
reviewed by senior management), Word, Bluebeam Revu (all site and house pricing
markups — manual), Archistar (overlays and current imagery; licence and API status
unconfirmed), the `Z:` share (`ESTATES INFORMATION` pre-contract, `PROJECTS` under
contract), Onsite Companion (holds document copies; not the working surface).

DataBuild has no API (confirmed org-wide 23 August 2026) — if variation pricing
ever uses its price file, that is an exported file a person provides, never a
system integration.

## Rules & knowledge

- `rules/` — **none transcribed yet.** First needed: pricing-request completeness
  rules (88B, 10.7, land contract currency and lot match), variation rules for
  sales, and SCR / job costing sheet conventions. Do not author skills before
  these exist and are reviewed.
- [docs/01-discovery-summary.md](docs/01-discovery-summary.md) — the discovery
  record this role was founded on.
- `reference/` — pointers to the source materials on `Z:` (questionnaire, meeting
  recording). They stay on `Z:` and are never copied into the repo.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\sales-estimation\{state,evidence,outputs,logs,reports,temp}\`
— git-ignored. Created 27 August 2026.

## Human-in-the-loop

Every price, research brief, variation document, register entry, chase-up and
response email is a **draft with an evidence bundle** for review. Research output
cites its sources (which portal, which document, retrieved when) so a person can
verify before a price relies on it. No sanctioned automation exceptions exist for
this role — contract-admin's CD-7.7 save exception does not extend here. Nothing
is sent, filed as final, or written to a system of record without explicit
approval.
