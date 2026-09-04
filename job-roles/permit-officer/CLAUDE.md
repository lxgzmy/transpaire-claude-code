# CLAUDE.md — Permit Officer / Building Approvals (job-role)

Scoped context for the Permit Officer job-role. The org-wide guardrails in the
repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Secures council approvals, covenant (developer) approvals, and the building
approval issued by the private certifier, for QLD and NSW jobs. Prepares and
lodges approval packages, works certifier RFIs to completion, orders
role-owned items (energy assessment, insurances, planning certificates,
utility-authority approvals), and coordinates every other RFI item to the
staff member who owns it. Claude assists by reading, tracking, drafting and
reporting — never by deciding an RFI response or touching a portal.

## Scope

Sequencing fixed by the business owner (21 Aug 2026): **AI integration starts
with NSW approvals** — NSW status lives in email + OSC and is reachable, while
QLD status sits in the certifier's portal, which AI cannot touch.

1. **Weekly BA report pre-population** (spec written; the OSC access gate has
   cleared — the read-only `osc-api` MCP server is live against the vendor's
   dev instance). Draft the Monday report from OSC + last week's report; flag
   item age. Spec: `workflows/ba-weekly-report.md`; rules `PO-9`–`PO-11`.
2. **Pre-lodgement checklist** (spec written, build gated on collecting the
   RFI corpus into the AI testing folder on `Z:`). Once per job, before
   lodgement. Spec: `workflows/pre-lodgement-checklist.md`; rule `PO-12`.
3. **Form pre-fill** (not started; needs blank council/certifier forms
   collected). No spec yet — write one before building.

## Systems

OnSite Companion (OSC) is the primary record: job activities/milestones,
alerts (the internal communication channel), and the per-job Document
Manager. Claude reads OSC through the **`osc-api` MCP server** (project-scoped,
read-only, writes disabled — see `.claude/skills/osc-api/` and
`docs/mcp-servers.md`); the nominal dev instance serves **live client data**,
so treat every read accordingly. Microsoft 365 / Outlook carries all external
correspondence. QLD jobs: the certifier's online portal holds lodgement + all
certifier communication (notifications land in the mailbox). NSW jobs: no
certifier portal — everything is email — plus the NSW Planning Portal for
CDC/CC lodgement and council/utility-authority portals for role-owned orders.
DataBuild (purchase orders) is retiring and **out of scope**.

## Rules & knowledge

- `rules/approval-workflow.md` — the transcribed discovery rules (`PO-*`):
  lodgement preconditions and package, QLD/NSW differences, RFI intake and
  triage, communication conventions, report content, non-goals.

> `rules/approval-workflow.md` is **transcribed from the 20 Aug 2026
> discovery meeting** (pending business review by the permit officer). Do
> not author skills against guessed rules; where a rule carries an open
> question, settle it with the business first.

## Hard limits fixed at discovery

- **No portal automation.** Certifier, council, NSW Planning Portal and
  utility portals are operated by humans only; no credentials to AI.
- **No RFI judgement.** Analysing an RFI and deciding the response is the
  permit officer's job. Claude tracks, drafts and reports around it.
- **DataBuild out of scope** (retiring; its replacement is Estimator
  Companion — revisit only once that is live).

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\permit-officer\{state,evidence,outputs,logs,reports}\`
— git-ignored.

## Human-in-the-loop

Every artefact (report draft, checklist, alert text, form fill) is a draft
with an evidence bundle for the permit officer to review. Nothing is sent,
lodged, uploaded, or written to OSC without explicit human approval. This
role has **no** sanctioned auto-save exception.
