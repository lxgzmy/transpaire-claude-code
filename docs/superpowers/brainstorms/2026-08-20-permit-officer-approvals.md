# Brainstorm: permit officer approvals automation

Source: AI-consultation discovery meeting, 20 Aug 2026 (recording + transcript
kept outside the repo — client PII). De-identified extraction; the resulting
implementation plan is
[../plans/2026-08-20-permit-officer-approvals-automation.md](../plans/2026-08-20-permit-officer-approvals-automation.md).

## The approval workflow (as run today)

```mermaid
flowchart TD
    A["Job ready to lodge<br/><small>land settled, drawings signed</small>"]
    A --> QLD["QLD lodgement<br/><small>certifier portal, all comms</small>"]
    A --> NSW["NSW lodgement<br/><small>email only, officer orders more</small>"]
    QLD --> RFI["RFI received<br/><small>always issued, 2-3 week wait</small>"]
    NSW --> RFI
    RFI --> OWN["Own actions<br/><small>insurances, energy, orders</small>"]
    RFI --> COORD["Coordination<br/><small>OSC alerts to GM, drafting</small>"]
    OWN --> BA["Building approval<br/><small>issued by the certifier</small>"]
    COORD --> BA
```

Notes from discovery:

- Lodgement itself is quick — the package (soil report, contours, registered
  plans, contract) is already in OSC's Document Manager. The pain starts at
  RFI stage.
- QLD: the certifier's portal holds the whole conversation and the certifier
  places most orders. NSW: no portal, everything is email, and the officer
  additionally orders the s10.7 certificate, water-authority approvals, and
  lodges via the NSW Planning Portal — NSW is the hard tracking case.
- Internal comms are always OSC alerts on the job (visible to everyone);
  external comms are email, dragged into OSC as `.msg` unless sent from OSC.
- The energy assessment nearly always returns required upgrades → GM
  decision → variation.
- Tracking all of this by hand feeds the **Monday weekly BA report** — every
  outstanding item re-derived job-by-job from OSC, the QLD portal, and the
  mailbox. That report is the single biggest time sink named in the meeting.

## Automation targets and their gates

```mermaid
flowchart LR
    G1["Gate: OSC API<br/><small>arrives 21 Aug</small>"] --> T1["1. Weekly BA report draft<br/><small>pre-fill red items + ageing flags</small>"]
    G2["Gate: RFI corpus<br/><small>past RFIs onto the Z: folder</small>"] --> T2["2. Pre-lodgement checklist<br/><small>predict RFI items and orders</small>"]
    G3["Gate: blank forms<br/><small>collect, then spec</small>"] --> T3["3. Form pre-fill<br/><small>council and certifier forms</small>"]
```

## Fixed non-goals (agreed in the meeting)

- No AI judgement on RFI responses — analysis and decisions stay with the
  permit officer.
- No automation of certifier / council / NSW Planning / utility portals — no
  credentials to AI.
- DataBuild is retiring and out of scope.

## Business owner review (21 Aug 2026)

Written input from the business owner confirms the discovery extraction —
observations, the three automations, and both hard exclusions restate the
meeting. New information from that review:

- **NSW first.** AI integration starts with NSW approvals. Structurally right:
  QLD status lives in the certifier portal AI cannot touch, while NSW data
  (email + OSC) is reachable.
- **AI testing folder exists**: `Z:\AI test\Permit Officer` — the agreed drop
  point for past RFIs, blank forms, and the report layout.
- **Dashboard reporting** raised as a fourth scope item — undefined (audience,
  cadence, relationship to the Monday Excel); scope with the business before
  any spec. Likely a by-product of the BA-report pipeline.
- **Estimator Companion** named as the DataBuild replacement; DataBuild stays
  out of scope until it is live.
- **OSC workflow update** re-committed: standard RFI tasks to be added as
  detailed OSC activities. Coordinate the activity names with the RFI corpus
  so checklist, OSC workflow, and BA report share one item vocabulary.
- Business to assess what is readable from OSC + email, then issue an
  information-request list for anything missing (add the unconfirmed
  amber ≤5d / red >5d ageing thresholds to that list).
