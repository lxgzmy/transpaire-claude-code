# CLAUDE.md — Contract Administration (job-role)

Scoped context for the Contract Administration job-role. The org-wide guardrails in
the repo-root `CLAUDE.md` always apply and are **not** restated here.

## What this role does

Builder-side contract administration for Transpire (Australian residential home
builder). Claude assists by reading requests, applying rules, and producing
**drafts + evidence** for human review. Read-only and draft-only first.

## Scope

1. **New Job Creation** (retired 18 Aug 2026). The `/ca-new-job` intake skill,
   its workflow spec and scripts were removed in favour of
   `/new-contract-template`. OSC intake is now integrated into that skill
   through the existing MCP (issue #34, 11 September 2026); no separate intake
   skill is restored. The rules transcribed from the OSC new-job manual
   (`rules/job-details.md`, `JD-*`) remain — the contract-documents workflow
   relies on them.
2. **Contract documents** (built; fills **and saves** with automatic routing —
   issuing and every outward act stays human). Build contract request → filled
   templates, saved in the same pass into the job's `CONTRACT DOCUMENTATION`,
   per document: a document it does not hold yet is the first version; one
   it already holds is a revision, saved there with the version it replaces
   moved into `SS\` once the new one is in (CD-7.5-7.7; revisions since
   9 Nov 2026, job 26061 feedback — until then they went to the
   template-testing folder; no preview stop since 17 Aug 2026). Rules from
   the manual's "RAISING CONTRACTS" section plus the blank templates diffed
   against completed jobs (`rules/contract-docs.md`); workflow spec
   `workflows/new-contract.md`; skill `/new-contract-template`. Produces the
   inclusions, the preliminary agreement, and — since 18 Aug 2026 — the HIA
   build contract in the same pass whenever a usable Word template exists
   (`fill_hia.py`, NSW+QLD; CD-5.2a/5.2b: approved blank → real name,
   otherwise the staged interim template → real name too, in production as
   well as test since 8 Sep 2026, no template at all → data sheet only; both
   staged templates are the team's own Word builds plus a sanctioned interim
   repair each — NSW v1.1 TABLES, QLD v2.1 LAND TABLES, 3 Sep 2026. NSW
   item 2 and the progress schedule are worked from the request price since
   15 Oct 2026, keyed DataBuild figures winning with a flag (CD-5.4, issue
   #62); QLD item 2 and Part B the same way since 27 Oct 2026 (the job
   26059 review, reversing issue #73's "never worked out"), the DataBuild
   figures the person gives - any time, typed or a screenshot read back to
   them, with no gate - winning; legal statements are
   never filled, except an amendment the request approves on its own line in
   the three kinds of CD-10 - the interest rate, a struck NSW clause, prelim
   clause words - issue #61). **Sydney
   inclusions content is edited by the run since 10 Sep 2026** (CD-9, from
   the NSW inclusions feedback sheet 9.9 / issue #35; the AUXILIARY blanks'
   MAIN and AUX DWELLING sections too since 15 Oct 2026, issue #63): section 18 area,
   Bathroom 2 and air-con notes, `UPGRADED INCLUSIONS` items from the job's
   `upgrades` block, black except the blue package headings, then a Word
   layout pass keeps the two
   columns level and a quality gate blocks the save on any miss. Mapping a
   request to a Standard Variation row, and any custom wording, stay a
   person's call — proposed in the job JSON, applied, reported with a
   confidence flag. **SEQ `PROMOTIONAL UPGRADES` the same way since 28 Oct
   2026** (CD-9.12, contract admin review of job 26059): the named promotion
   copied in (`promotion.py`), then the request's upgrades from the QLD sheet.
   **Gunnedah since 9 Nov 2026** (CD-6.6, job 26061 feedback sheet row 5): a
   request that sends another job's inclusions as the base is built from the
   current blank with the sample's specification (`sample_base.py`), so every
   client value is this job's. The request's removals are the only content
   edit: a label goes with its last line. The same layout pass and gate
   follow, then a scan that nothing of the sample's client is left. Writing
   Gunnedah upgrade lines stays a person's edit.
3. **Variation Stage 1** (not started). Blocked on transcribing the variation
   manual into `rules/variation-rules.md` — do not build against guessed rules.

General `Z:` drive help (finding files, save-location advice, duplicate reports)
is **not** a Contract-Admin deliverable — it is the org-level
[`z-drive-ops`](../../.claude/skills/z-drive-ops/SKILL.md) skill, shared with
every other role. This role keeps only the job-specific `Z:` rules: `JD-10` in
`rules/job-details.md` and `scripts/new_job_folders.ps1`.

OSC new-contract intake follows the
[execution reference](../../.claude/skills/new-contract-template/references/osc-new-contract.md):
client/job creation, sourced details, evidenced activities, request-email uploads
and contacts through approved MCP writes. Missing API mappings are manual fields,
never guessed. Existing document-only refreshes do not replay OSC mutations.
Other OSC write workflows remain outside this integration.
DataBuild automation is **ruled out entirely** (23 Aug 2026): the vendor
confirmed it provides no API access, so no MCP server, adapter, or import
automation can be built against it. DataBuild stays manual — a person keys its
figures into the job JSON where they should override the ones worked from the
price (CD-5.4). The legacy JD-6 handoff and wait are excluded
from the integrated OSC intake; contacts and document drafting proceed without
them. OSC activity 6 ("Create Job within Databuild") is completed at the job's
set-up, in stage 2 with activities 1 and 2, whether or not DataBuild has the job
yet: DataBuild work can only start once it is complete (job 26061 feedback
sheet, 9 Nov 2026 row 2; until then it waited for the person's word that the
DataBuild entry was done). It is never marked N/A.
It is retiring in favour of Estimator Companion. Background on the
tool: `docs/01-solution-architecture.md`.

## Systems

OnSite Companion (OSC), DataBuild (manual only — no API access, confirmed
23 Aug 2026), the `Z:` share, Microsoft 365 / Outlook (a shared
Contract-Admin mailbox), DocuSign. The **authoritative record varies per field** and
must be confirmed — the canonical job record is not tied to any single system.

Contract drafts reach DocuSign through the local `docusign-upload` MCP server, which
puts the job's own PDFs in the draft: `docusign-upload-prod` for real jobs (registered
at production Go-Live) and `docusign-upload` (sandbox) for synthetic jobs only. The
hosted `docusign-demo` server (sandbox, sign-in required) stays connected for read-only
checks; its writes are gated per call. Connection details and the production steps
live in [`docs/mcp-servers.md`](../../docs/mcp-servers.md), not restated here, since
the servers are shared with every other role.

## Changing the pipeline

A fix reaches every family and region, not only the one it was reported on.
Four of job 26061's ten feedback rows (9 Nov 2026) were fixes already made for
Sydney, SEQ or QLD that had never reached Gunnedah or the NSW build contract.
So a fix adds its outcome as a row in `scripts/regress_families.py`, which
checks every row on every live blank and both build contracts; a family that
does not take the outcome is named in its `EXEMPT` table with the reason.
Run it before a PR that changes the fill, edit, gate or build contract
scripts, and with `--e2e` before the PR merges.

## Rules & knowledge

- `rules/variation-rules.md` — variation type/numbering, workflow & document
  templates, file naming, activities, alert recipients.
- `rules/job-details.md` — new-job address / CAPS / certifier / council / marketer rules.
- `rules/contract-docs.md` — contract template selection, inclusions and
  preliminary agreement fields, build contract data, aux/dual-key handling,
  output naming (`CD-*`).
- `reference/` — pointers to the source manuals (kept on `Z:`, never in the repo).

> `rules/job-details.md` and `rules/contract-docs.md` are **transcribed**
> (pending business review); `rules/variation-rules.md` is still a **stub**. Do
> not author skills against guessed rules. `contract-docs.md` carries an open-
> questions list where the manual and the live drive disagree — worth settling.

## Runtime workspace (server)

`Z:\CLAUDE CODE\transpire-claude-code\runtime\contract-admin\{state,evidence,outputs,logs,reports}\`
— git-ignored. Naming / CAPS conventions from the manuals are enforced in outputs.

## Human-in-the-loop

Every externally visible artefact (job summary, variation document, alert, email,
DocuSign) is produced as a **draft with an evidence bundle** for review. Nothing is
sent to a client/owner or written to a system of record without explicit approval.

**Sanctioned exception (17 Aug 2026):** the `/new-contract-template` save is
automatic — routed by CD-7.6/7.7 per document into the job folder — with the
full report following the save. **Since 9 Nov 2026** (job 26061 feedback, by
the same kind of explicit instruction) a revision is saved there too and the
version it replaces moves into the folder's `SS\`: the new copy is in place
before anything moves, a failure puts everything back, nothing in `SS\` is
overwritten, and a signed or executed copy stops the run. That move inside
the job's own `CONTRACT DOCUMENTATION` is the only business-file move a run
makes. Issuing, sending, signing, and OSC/DataBuild writes outside the gate
stay human.

**DocuSign draft (13 Oct 2026):** after a build contract saves into the job
folder, `/new-contract-template` creates a DocuSign envelope with
`status: created`, a draft that is never sent, with the job's own PDFs in it,
through the gated `docusign_create_draft` call on the `docusign-upload`
server. The approval prompt on that call is the person's yes, per call. This
is a gated external write, not an extension of the automatic save. Until
`docusign-upload-prod` is connected at production Go-Live, a real run creates
no draft and reports why; any fallback is an open owner decision (CD-11.8).
Tagging any document the report flags, fixing witness/date roles and sending
stay human (CD-11).

**Where the contract documents go (four rules; rule 3 since 9 Nov 2026)**

1. Every `/new-contract-template` run first looks in the job's
   `Z:\PROJECTS\<region>\<job>\CONTRACT\CONTRACT DOCUMENTATION\` folder and
   notes which contract documents are already there: inclusions, preliminary
   agreement, build contract (`SS\` included).
2. A document the job folder does **not** have is its **first version**.
   Its `.docx` + `.pdf` are saved straight into that `CONTRACT
   DOCUMENTATION` folder.
3. A document the job folder **already** has is a **revision**. The new
   `.docx` + `.pdf` are saved into the same `CONTRACT DOCUMENTATION` folder
   and the version they replace moves into its `SS\` subfolder (made if
   missing) - only after the new copy is safely in the folder, so a failed
   save never loses the current contract. An archived copy is never
   overwritten: a name `SS\` already holds takes the next ` V2`, ` V3`.
   A signed or executed copy stops the run instead (job 26061 feedback,
   9 Nov 2026; until then a revision went to the template-testing folder
   for a person to swap in).
4. The build contract is **no longer blocked**. While NSW / QLD has no
   MCR-filed Word blank in its `CONTRACT\` template folder, the run fills the
   staged interim template under the real file name; the run report names
   the template, and a person reads the draft against the licensed HIA PDF
   before it is issued.
