# DocuSign tab placement on the job's own PDFs

Findings and a check procedure, 13 October 2026. Follows the switch of
`/new-contract-template` step 8 to the `docusign-upload` server (CD-10). The
evidence images stay in the git-ignored `runtime\docusign-sandbox\evidence\`;
the PR body carries the summary.

## Why a visual check is needed

Every tab on the six templates is fixed to a page and an x/y position; none is
anchored. The server carries a template's tabs onto a job document only when
the page counts match, and its read-back confirms the draft holds the same
number of tabs per role and page as the template. Neither shows that a tab
sits on the job document's own line. A job PDF can match the page count and
still have its signature line somewhere else, and DocuSign then asks the buyer
to sign beside it. Only an image of the page with the tabs drawn on shows
that.

The draft's tab positions are the template's, page for page: the server
gives each carried document the template document's id, so DocuSign applies
that document's tabs unchanged. One sandbox draft confirms this. After that,
the template's own geometry drawn over a job PDF shows what the draft would
show, for every template, without creating more envelopes. That matters
because the restricted sandbox plan rejected a five-recipient draft, so sandbox
drafts use the two-recipient QLD Single Buyer template.

## What the templates' geometry shows (read-only, 13 October 2026)

Read from the six templates through the hosted sandbox server. Positions only;
no names, emails, labels or values were kept. Points from the page's top-left.

| Template | Contract tabs | Inclusions pages | Inclusions body initials (first buyer) | Inclusions last three pages: signature heights | Plans pages: signature x |
|---|---|---|---|---|---|
| `NSW Build _ Single Buyer` | 44 | 16 | 356, 789 | 520 to 707 | 3: 470 to 479 |
| `NSW Build _ 2 Buyers` | 73 | 16 | 356, 789 (second buyer 420) | 520 to 710 | 12: 472 to 657 |
| `NSW Build _ Company` | 43 | 18 | 356, 789 | 529 to 690 | 5: 446 to 479 |
| `QLD Build _ Single Buyer` | 36 | 15 | 356, 795 | 522 to 715 | 4: 420 to 438 |
| `QLD Build _ 2 Buyer` | 69 | 16 | 361, 794 (second buyer 419) | 521 to 715 | 4: 407 to 500 |
| `QLD Build _ Company` | 36 | 16 | 362, 788 | 533 to 669 | 5: 403 |

The patterns:

- **Inclusions.** Initials sit at one footer position on every page except the
  last three. The last three hold the signature and date blocks: the
  third-last has the builder and the buyers, the last two the buyers. The same
  block sits at different heights on different templates: the first buyer's
  signature within 13 to 33 points, the builder's within 46 (669 to 715).
  Each placeholder was a different job, so the likely cause is inclusions
  that ran to a different length.
- **Plans.** One signature per buyer on every page, in the title block near
  the bottom right. Within one plan set the position mostly holds; between
  sets it moves by up to 250 points across the page.
- **Build contract.** Initials at one footer position on the body pages
  (NSW about 540, 745; QLD 545, 753) and signatures on fixed pages (NSW pages
  12 and 35, QLD pages 3 and 13, plus the Company signing page). A few
  initials sit beside a particular clause or checkbox.
- **Preliminary agreement (NSW).** The buyers sign each of the three pages;
  the builder and the date field are on page 3.

## Risk per document

| Document | Page count | The tabs land on the job's line when | Risk |
|---|---|---|---|
| Build contract | Must match the template's (45 NSW, 37 QLD), or the step stops | the interim Word build keeps the licensed PDF's layout page for page | Medium. The page count matches by design, but Word can move a line within a page. Check once per interim template version |
| Preliminary agreement | Three pages, fixed | the fill keeps the layout | Low |
| Inclusions | Varies by job (15 to 18 in the placeholders) | the page count matches **and** the last three pages' blocks sit where the placeholder's did | High on the last three pages, even at a matching count; low on the body pages |
| Plans | Varies by job (3 to 12) | the page count matches **and** the title block is the same drafter's layout | High |

## Inclusions: a re-basing rule to consider (not implemented)

Today an inclusions PDF whose page count differs goes in untagged and flagged.
If the check shows the company's inclusions always end on the same three
signature pages, the server could build the tabs itself instead:

1. For a job inclusions of N pages from a template inclusions of M pages,
   put each buyer's body initial (the template's most common position over
   pages 1 to M-3) on pages 1 to N-3.
2. Put the template's tabs from pages M-2, M-1 and M on pages N-2, N-1 and N,
   at the same x/y.
3. Apply it only when the draft report's visual check has passed for that
   region's current inclusions template, and keep flagging when N is under 4.

This needs the job's last three pages to share the template's layout, which
the spread above (up to 46 points between templates for the same block)
argues against unless the current templates end on a fixed signature page.
The evidence from the check decides it; the owner decides whether to build
it. It would change the server's draft building (inline tabs on the
composite instead of the server template's), so it is its own PR.

## Plans: keep them flagged

Fixed positions cannot follow a title block that moves by 250 points between
drafters, so plans stay carry-or-flag, and staff tag them. A text anchor in
the title block (for example a "CLIENT SIGNATURE" label) would place them
reliably, but only if every drafter uses the same words; that has not been
checked.

## If the build contract's tabs are off

The interim Word templates already carry e-sign anchor strings at source
(`/bs1/\builder_sig`, `/i1/\signer1_sig`, `/na/`), which these DocuSign
templates do not use. If the check shows fixed tabs off the contract's lines,
anchor tabs on those strings are the lasting fix. That changes the DocuSign
templates (a DocuSign admin's job) and is out of scope here.

## Check procedure (sandbox, synthetic jobs only)

Runs on the Windows server, where `Z:`, Word, the interim templates and the
`docusign-upload` venv are (owner's choice, 13 October 2026). The commands are
in the run kit,
[`job-roles/contract-admin/fixtures/docusign-sandbox/`](../../../job-roles/contract-admin/fixtures/docusign-sandbox/README.md):
six synthetic job JSONs (one per template), `synthetic_plans_pdf.py` and
`docusign_tab_overlay.py`. In outline:

1. **Prerequisites.** The DocuSign admin steps in the
   [upload design](2026-10-13-docusign-upload-mcp.md#prerequisites-for-the-docusign-admin)
   are done and `python -m docusign_upload.selftest` passes. A
   verification-only venv (`runtime\.venv-verify`) holds pypdfium2 and
   Pillow, approved 13 October 2026 and never a server dependency.
2. **Fill each fixture** through the driver into a job folder inside
   `runtime\docusign-sandbox\PROJECTS\<region>\...`, so the documents route
   PRODUCTION and export through Word as on a real run, then add a synthetic
   five-page plans PDF so the flag path runs too.
3. **One draft** (`qld-single`, the template inside the sandbox recipient
   cap): step 8 as written, approved at the prompt. Expected: status
   `created`, the contract and inclusions carried, the plans flagged, two
   recipients, `JobNo`, subject and message as sent.
4. **Positions.** The hosted `listRecipients` (`include_tabs=true`) and
   `listEnvelopeDocuments`, read-only, saved as returned. Each carried tab's
   page and x/y must equal the template's.
5. **Images.** The overlay draws the draft's tabs on its documents, and each
   template's own tabs on the other five fixtures' PDFs (no envelopes).
6. **Verdict** per document: **OK**, **misplaced** (page and tab), or
   **missing** (tabs past the last page).
7. **Duplicate check.** A second preview for job 99981 stops on the draft.
8. **The draft** stays until the owner decides; it is never voided or
   deleted without that decision.

The overlay was tried on this clone with synthetic plans and the QLD Single
Buyer template's own tabs (13 October 2026): the tabs drew beside the plans'
"CLIENT SIGNATURE" line where the geometry puts them, and a three-page plans
PDF reported the fourth page's tab as missing.

## Verdicts

Filled in from the run, per template and document: pages (job and
template), tabs carried, and OK, misplaced or missing.
