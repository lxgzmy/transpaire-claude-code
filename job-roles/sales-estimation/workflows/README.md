# workflows/ — Sales Estimation

**All proposed, none built.** These are the use cases from the discovery of
27 August 2026 ([../docs/01-discovery-summary.md](../docs/01-discovery-summary.md),
version 2). The meeting fixed the build order: **land assessment first, then
variations.** Each workflow gets its own spec file here before anything is
authored, and no skill is built until the rules it depends on are transcribed
into `../rules/` and reviewed (org rule: propose before building).

| # | Proposed workflow | Depends on | Status |
|---|---|---|---|
| 1 | **Land assessment, end to end** (agreed first build) — pricing request from email → research (zone/code, setbacks, overlays incl. Queensland Globe, DA documents with superseded flagged) → land contract, 88B and dependent reports reviewed under the no-guessing rule, oversized documents split → nine-section feasibility report, every claim cited → estate/stage/lot folder + `SALES ESTIMATING` subfolder created or verified → saved | The two rule conflicts settled (pricing in reports; MSDG trigger wording); knowledge bases transcribed into `../rules/`; the manager's folder-naming nomination; corrections history harvested | Proposed — transcription source exists (the manager's handed-over skill and knowledge bases) |
| 2 | **Variations assistant** (agreed second) — recognise the request email; match standard items to the NSW/QLD master variation books with reference price; search past variations within an agreed window; rewrite client wording into correct terminology; pre-populate the variation sheet; keep a register | Master variation books, variation sheet and sample variations collected; price-escalation policy confirmed; variation rules transcribed | Proposed — starts from far less material |
| 3 | **Price response email drafts** — drafted from the completed costing using the manager's templates; never sent automatically | Template emails collected | Proposed |
| 4 | **SCR reporting** — reports out of the Sales Costing Register on request or schedule; the register itself stays as built | The costing workbooks and current SCR collected | Proposed |
| 5 | **Priced-job finder** — by lot, address, client or estate, regardless of LGA folder | Nothing beyond read access; largely covered by the org-wide `z-drive-ops` skill | Proposed |
| 6 | **Duplicate document detection** in estate folders — report-only drive hygiene | Nothing beyond read access | Proposed (later) |

**Boundaries (from discovery, standing):** site costs stay manual, Bluebeam
pricing markups stay with the manager, land is never priced, nothing prices a
job or sends anything on its own, and every output is a draft with evidence for
human review. Plan-geometry pricing is parked as the long-term goal.

**Supporting decisions from the meeting:** a standardised pricing-request email
format is planned org-wide (it also serves contract-admin); the manager
nominates the folder and naming structure for sales estimating outputs; the
Onsite Companion connection is the programme's current top priority and
workflow 1 is built against the `Z:` drive until it lands.
