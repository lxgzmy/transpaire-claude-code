# Approval workflow rules (`PO-*`)

Transcribed from the 20 Aug 2026 AI-consultation discovery meeting with the
permit officer. **Pending business review.** Each rule is written to be
testable; open questions are marked ❓.

## Role and preconditions

- **PO-1 — Role scope.** The permit officer secures (a) council approvals,
  (b) covenant approvals from the developer, and (c) the building approval
  issued by the private certifier, and performs lodgements for both QLD and
  NSW jobs.
- **PO-2 — Lodgement preconditions.** A job is lodged only when the land has
  settled **and** the owner has signed the working drawings. The trigger is
  an OSC alert from the customer liaison that the job is ready to lodge; the
  OSC workflow tracks the preconditions.
- **PO-3 — Lodgement package.** The initial package is compiled from the
  job's OSC Document Manager and at minimum comprises the soil report,
  contour plans, registered plans, and (when present) the contract. Document
  hunting is *not* a pain point at lodgement — it starts at RFI stage.

## State differences

- **PO-4 — QLD.** The certifier operates an online portal: the job is
  created and documents uploaded there, and **all** certifier communication
  happens in the portal (each side gets email notifications). The certifier
  also places council/covenant/QLD-specific orders on the builder's behalf.
  QLD status can therefore be read at a glance from the portal.
- **PO-5 — NSW.** No certifier portal — all certifier correspondence is by
  email, which makes NSW status the hard tracking case. The permit officer
  additionally orders what the QLD certifier would order: the s10.7 planning
  certificate (before lodgement — the certifier will not assess without it;
  a colleague notifies the permit officer ahead of lodgement so it can be
  ordered early; some councils take a day, others need chasing), plus
  utility-authority (water) approvals where the job's region requires them,
  and lodges the CC/CDC through the NSW Planning Portal.

## RFI lifecycle

- **PO-6 — RFI is universal.** Every job receives at least one RFI
  (request for information) from the certifier after lodgement; first
  assessment turnaround is typically 2–3 weeks (extremes to 4). One RFI per
  job is the norm; a further RFI appears only to correct a certifier error
  or to reset the statutory assessment clock on long-running jobs, and
  substantially repeats the outstanding items.
- **PO-7 — RFI intake.** On receipt: update the OSC milestones (RFI
  received) and upload the RFI document to the job, then work the item list.
- **PO-8 — RFI triage.** Each RFI item is either **own-action** (the permit
  officer orders/supplies it: insurances such as home-warranty and
  long-service levies, purchase orders, the energy-efficiency assessment,
  certificates) or **coordination** (another team decides: e.g. a
  non-compliant setback goes by OSC alert to the GM and the drafting manager
  with the options — amend plans or lodge a council referral — and their
  decision comes back before the certifier is notified). Judgement about
  what each item needs **stays human** (see PO-13).
- **PO-8a — Energy efficiency.** Ordered for every job (QLD and NSW) at or
  shortly after lodgement. The assessment almost always returns required
  upgrades; upgrades trigger an OSC alert with the options, a GM
  cost-efficiency decision, then drafting + contracts raise a variation.
  The Document Manager description encodes state: an *energy application*
  document means not yet assessed (or upgrades pending); an *energy report*
  means completed/approved.

## Communication conventions

- **PO-9 — Internal = OSC alerts.** All internal RFI communication is an OSC
  alert on the job activity (never plain email): alerts are visible to
  everyone on the job, carry history, and let others pick up a stalled item.
  Follow-up on an unanswered alert is face-to-face or email. External
  parties (engineers, energy assessor, certifier in NSW) are emailed;
  engineering emails sent *from* OSC save to the job automatically, and all
  other external email must be dragged into OSC manually as `.msg`.

## Weekly BA report

- **PO-10 — Cadence and base.** The report is produced every Monday as the
  whole-of-business status view of jobs in the approval stage. Last week's
  report is the base; items completed during the week are removed and new
  ones added.
- **PO-11 — Content and sources.** One row per job: job number, client,
  site, key dates, and the **outstanding RFI items** (currently typed
  manually in red). Sources, in order: OSC (job activities, alerts,
  Document Manager descriptions per PO-8a) → QLD certifier portal → the
  mailbox (NSW especially). Items live outside OSC workflow activities
  today, which is why compilation is manual. Wanted additions from the
  meeting: per item, **who it is with, the date it was handed to them, and
  days outstanding**, with an age flag — ❓ default from the meeting:
  amber within 5 days, red past 5 days; confirm thresholds with the
  business.

## Pre-lodgement checklist

- **PO-12 — Predicted checklist.** Once per job, before lodgement (timing ❓
  — the more Transpire documentation is ready, the better), produce a
  job-specific checklist of (a) items the certifier's RFI is likely to
  raise, learned from past RFIs — NSW RFIs are near-standard forms, ideal
  training material — and (b) role-owned orders the job's attributes
  trigger (energy assessment always; s10.7 for NSW; utility-authority
  approval when the job falls in an applicable water region). Purpose: a
  head start and a forget-proof reminder across many simultaneous jobs.

## Non-goals (fixed at discovery)

- **PO-13 — No RFI judgement by AI.** Analysing the RFI and deciding
  responses is the permit officer's role.
- **PO-14 — No portal automation, no DataBuild.** No AI access or
  credentials to certifier/council/NSW-Planning/utility portals. DataBuild
  is retiring and out of scope; revisit only once its replacement
  (Estimator Companion) is live.
