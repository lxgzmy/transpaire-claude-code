# docusign-sandbox fixtures: the tab placement run kit

Synthetic job JSONs for the DocuSign sandbox tab check, one per company
template. Every person, lot, address and job number is invented; every email
is `@example.com`. No price figures (CD-5.4). Why the check exists and what it
decides: [`docs/superpowers/brainstorms/2026-10-13-docusign-tab-placement.md`](../../../../docs/superpowers/brainstorms/2026-10-13-docusign-tab-placement.md).

| Fixture | Template it picks | Job | Region folder |
|---|---|---|---|
| `qld-single.json` | `QLD Build _ Single Buyer` (the sandbox draft) | 99981, lot 981 | `SEQ` |
| `qld-two.json` | `QLD Build _ 2 Buyer` | 99982, lot 982 | `SEQ` |
| `qld-company.json` | `QLD Build _ Company` | 99983, lot 983 | `SEQ` |
| `nsw-single.json` | `NSW Build _ Single Buyer` | 99984, lot 984 | `SYDNEY` |
| `nsw-two.json` | `NSW Build _ 2 Buyers` | 99985, lot 985 | `SYDNEY` |
| `nsw-company.json` | `NSW Build _ Company` | 99986, lot 986 | `SYDNEY` |

Only `qld-single` becomes a DocuSign draft: it is the one template with two
recipients, and the restricted sandbox plan rejected five. The other five are
checked by drawing the template's own tabs over their PDFs, with no envelope.

## Run it (Windows server, `pwsh`, repo root)

Evidence pending until the DocuSign admin prerequisites are done
(`python -m docusign_upload.selftest` passes in
`shared\mcp\docusign-upload`). Everything below writes only under the
git-ignored `runtime\`.

**Once: the verification venv** (pypdfium2 + Pillow, approved 13 Oct 2026 for
drawing the check images only; never a server dependency):

```powershell
python -m venv runtime\.venv-verify
runtime\.venv-verify\Scripts\python.exe -m pip install pypdfium2 Pillow
```

**Per fixture** (`qld-single` shown; change the four names for the others):

```powershell
$fx   = "job-roles\contract-admin\fixtures\docusign-sandbox\qld-single.json"
$work = "runtime\docusign-sandbox\work\99981"
$job  = "runtime\docusign-sandbox\PROJECTS\SEQ\99981 - LOT 981 SAMPLEVILLE\CONTRACT\CONTRACT DOCUMENTATION"
$sfx  = "LOT 981_SAMPLEVILLE_TESTBUYER"
New-Item -ItemType Directory -Force $work, $job | Out-Null
Copy-Item $fx "$work\job.json"
# the inclusions blank step 3 picks for the region (references/contract-template-map.md);
# NSW fixtures add --prelim
python job-roles\contract-admin\scripts\draft_contract.py --job "$work\job.json" --template "<inclusions blank>" --job-dir $job
python job-roles\contract-admin\scripts\synthetic_plans_pdf.py --out "$job\PLANS_$sfx.pdf" --pages 5
python job-roles\contract-admin\scripts\docusign_payload.py --job "$work\job.json" --job-dir $job
```

The `PROJECTS\<region>` segments inside the sandbox folder let the driver and
the payload read the region, as for a real job; the folder stays inside
`runtime\docusign-sandbox`, the only place the sandbox server reads. The
payload must say `server : docusign-upload (SANDBOX, synthetic jobs only)`.

**The draft (`qld-single` only)**, in a Claude Code session in the repo:
step 8 for `$work` per
[`references/docusign-draft.md`](../../../../.claude/skills/new-contract-template/references/docusign-draft.md):
`docusign_token_info`, `docusign_draft_preview`, then `docusign_create_draft`,
approved at the prompt. Expected: status `created`; the contract (37 pages)
and the inclusions carried when their page counts match the template's (37
and 15); the plans (5 pages against 4) flagged; two recipients; `JobNo`,
subject and message as sent. Then save, as returned, the hosted
`listRecipients` (`include_tabs=true`) and `listEnvelopeDocuments` for the
envelope id into `runtime\docusign-sandbox\evidence\<date>\qld-single\`
(`draft-recipients.json`, `draft-documents.json`). Both calls are read-only.

**The images:**

```powershell
$ev = "runtime\docusign-sandbox\evidence\<date>\qld-single"
runtime\.venv-verify\Scripts\python.exe job-roles\contract-admin\scripts\docusign_tab_overlay.py `
  --recipients "$ev\draft-recipients.json" --documents "$ev\draft-documents.json" `
  --pdf "BUILD CONTRACT=$job\BUILD CONTRACT_$sfx.pdf" --pdf "INCLUSIONS=$job\INCLUSIONS_$sfx.pdf" `
  --out "$ev\draft"
```

For the template's own tabs (every fixture, and the plans a draft leaves
untagged), save the hosted `assessTemplatesForDV` (with `template_ids`) and
`getTemplates` (`include=documents`) results as returned, and run the same
tool with `--recipients <template read> --documents <templates read>
--template "<template name>"`, plus `--pdf "PLANS=..."` and, for NSW,
`--pdf "PRELIMINARY AGREEMENT=..."`.

**Verdict per document:** look at every page image. **OK**: every tab sits
on its line. **Misplaced**: name the page and the tab. **Missing**: the
summary's `MISSING` lines (tabs past the last page). Record the table in the
tab placement write-up and the PR, never the images.

**After the draft:** a second `docusign_draft_preview` with the same
arguments must stop on the existing `JobNo` 99981 draft. The draft stays
until the owner decides; nobody voids or deletes it without that decision.
