# Permit Officer — Building Approvals (job-role)

Builder-side permits and approvals for Transpire (QLD + NSW residential jobs).
Start with [CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the
repo-root `CLAUDE.md` also apply).

Discovery completed 20 Aug 2026 (AI-consultation session with the permit
officer), business-owner review 21 Aug 2026 (**NSW approvals first**).
Proof-of-concept, read-only and draft-first. Three workflows, in build order:

1. **Weekly BA report pre-population** (spec written; access gate cleared —
   the read-only `osc-api` MCP is live) — draft the Monday building-approval
   status report by reading OSC job activities, alerts and documents, carrying
   forward last week's report, and flagging item age. Spec:
   `workflows/ba-weekly-report.md`.
2. **Pre-lodgement checklist** (spec written; build gated on the RFI corpus)
   — before a job is lodged, predict the certifier's likely RFI items and the
   orders the permit officer must place (energy assessment, 10.7, utility
   authority), from job attributes plus past RFIs. Spec:
   `workflows/pre-lodgement-checklist.md`.
3. **Council / certifier form pre-fill** (not started) — pre-fill recurring
   application forms from OSC job data. Flagged in the meeting as the easy
   win; needs the blank forms collected into the AI testing folder first.

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow (above). |
| `rules/` | De-identified, testable business rules transcribed from discovery (`PO-*`). |
| `reference/` | Pointers to source material (recording, AI testing folder) kept on `Z:` — never in the repo. |
| `skills/` | Role-only skills. None built yet; proposals listed in `skills/README.md`. |

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\permit-officer\{state,evidence,outputs,logs,reports}\`
(git-ignored) — see the org [CLAUDE.md](../../CLAUDE.md).
