# Contract Administration (job-role)

Builder-side contract administration for Transpire, on Windows Server 2022. Start
with [CLAUDE.md](CLAUDE.md) for role context (the org guardrails in the repo-root
`CLAUDE.md` also apply).

Proof-of-concept, read-only and draft-first. Three workflows:

1. **New Job Creation** (retired 18 Aug 2026) — the `/ca-new-job` intake skill,
   `workflows/new-job.md` and its scripts were removed in favour of
   `/new-contract-template`. OSC intake is now integrated into workflow 2 through
   the existing MCP (11 September 2026). The `JD-*` rules remain.
2. **Contract documents** (built; fills and saves in one pass) — build contract
   request → filled inclusions + preliminary agreement + HIA build contract
   (`.docx` + PDF export each; the build contract fills whenever a usable Word
   template exists — approved blank → real name, otherwise the staged interim
   template → real name too, in production as well as test since 8 Sep 2026,
   no template at all → data sheet, CD-5.2b) → saved to the routed
   destination per document: the job folder for a document not yet there,
   the template-testing folder for a document the job already holds
   (CD-7.6/7.7 — no preview stop; issuing stays human).
   Verified character-for-character against completed jobs in all three
   template families. Skill: `/new-contract-template`. It now includes
   [OSC job setup](../../.claude/skills/new-contract-template/references/osc-new-contract.md)
   from issue #34's Word items 1–9: client/job, detail fields, activities,
   request-email attachments and contacts. OSC writes are approved per call;
   DataBuild is excluded and does not block this intake.
3. **Variation Stage 1** (not started) — variation type decision → OSC variation +
   workflow templates → Z-Drive Excel variation → OSC document generation → PDF
   filing → staff alert. Blocked on transcribing `rules/variation-rules.md`.

General `Z:` drive help (search, save-location advice, duplicate/clutter
reporting) is **company-wide, not role-specific** — it lives in the org-level
[`z-drive-ops`](../../.claude/skills/z-drive-ops/SKILL.md) skill. This role keeps
only the job-specific `Z:` rules (`JD-10`, `scripts/new_job_folders.ps1`).

## Where the documents go

**Where the contract documents go (four rules, 8 Sep 2026)**

1. Every `/new-contract-template` run first looks in the job's
   `Z:\PROJECTS\<region>\<job>\CONTRACT\CONTRACT DOCUMENTATION\` folder and
   notes which contract documents are already there: inclusions, preliminary
   agreement, build contract (`SS\` included).
2. A document the job folder does **not** have is a **real contract, not a
   test**. Its `.docx` + `.pdf` are saved straight into that `CONTRACT
   DOCUMENTATION` folder. It never goes to template-testing.
3. A document the job folder **already** has is treated as a **test /
   refresh**. Its `.docx` + `.pdf` go only to
   `Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\`.
   The original in the job folder is never overwritten; a person swaps it in
   (old version to `SS\`).
4. The build contract is **no longer blocked**. While NSW / QLD has no
   MCR-filed Word blank in its `CONTRACT\` template folder, the run fills the
   staged interim template under the real file name; the run report names
   the template, and a person reads the draft against the licensed HIA PDF
   before it is issued.

## Folder map

| Folder | Purpose |
|---|---|
| `CLAUDE.md` | Role context, scope, systems, rules pointers, HITL. |
| `workflows/` | One spec per workflow. `new-contract.md` built; variation stage 1 to come. |
| `rules/` | Transcribed, testable business rules. `job-details.md` (`JD-*`) and `contract-docs.md` (`CD-*`) transcribed; `variation-rules.md` still a stub. |
| `scripts/` | The workflow pipeline: email → extraction → template fill → PDF export, plus probes, diff tools and the three test suites. See [scripts/README.md](scripts/README.md). |
| `skills/` | Role-only skills, authored and documented here. `new-contract-template` built (registered in `../../.claude/skills/`). |
| `reference/` | Pointers to source manuals (never the manuals themselves). |
| `templates/` | Sanitised prompt / document / output templates. |
| `fixtures/` | Synthetic test data only. |
| `docs/` | Operational docs & solution design (below). |

## Documentation

| Doc | Contents |
|---|---|
| [docs/01-solution-architecture.md](docs/01-solution-architecture.md) | Draft solution: architecture, integration tiers per system, workflow design, HITL, rollout, risks. |
| [docs/02-windows-server-setup.md](docs/02-windows-server-setup.md) | Software/config on Windows Server 2022 for the OSC UI-automation skill. |
| [docs/03-automation-flow.md](docs/03-automation-flow.md) | How Claude Code and UI automation fit together at runtime. DataBuild is manual-only — no integration. |

> Note: `docs/01–03` predate the read-only-first direction and describe the fuller
> OSC automation. Treat those OSC parts as historical design; the current
> new-contract integration is the MCP reference linked above, with approved OSC
> writes and automatic document saves under CD-7.7. The DataBuild integration they once proposed (SQL/MCP
> adapter, import routines) was **dropped 23 Aug 2026** — DataBuild confirmed it
> provides no API access — so DataBuild stays manual and appears in the docs as
> background only. The docs will be refreshed as the workflows are built.

## Source manuals

The authoritative manuals (e.g. *Creating a Variation — Stage 1*, the discovery
record, the OSC new-job manual) contain client PII and server names, so they are
**not** stored in this repo. They live on `Z:` and are pointed to from
[reference/](reference/README.md); only de-identified rules are transcribed into
[rules/](rules/README.md).

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\` (git-ignored) — see
the org [CLAUDE.md](../../CLAUDE.md).
