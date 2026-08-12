# scripts/

Scripts for the new-job workflow (`../workflows/new-job.md`) and the
new-contract workflow (`../workflows/new-contract.md`).

| Script | Status | Does |
|---|---|---|
| `msg_to_text.py` | **Working** | Outlook `.msg` → plain text (headers + body + attachment names); `-a <dir>` also saves the attachments (EOI PDF, inclusions doc) so Claude can read them. Needs `pip install extract-msg`. |
| `fill_inclusions.py` | **Working, validated against a real job** | Blank inclusions template + job JSON → filled `.docx` (`CD-2`, `CD-3`). Stdlib only — edits `word/document.xml` in place inside the zip, inserting values as new runs after each label the way Word does, so the template's wording, styles and inclusion text are untouched. Fills every occurrence, because the signature pages are duplicated for the builder's and owner's copies. `--check` verifies every anchor exists and writes nothing — **run it first**; a missing anchor means the template was revised. |
| `extract_eoi.py` | **Working, tested** | Request-email text → job-data JSON draft sheet per the `JD-*` rules, plus human-attention flags. Handles labelled emails and free-form forwarded chains (subject-line lot/suburb, e-sign client, `$` price, "site a X with a Y façade"). Read-only; touches nothing. |
| `test_extract_eoi.py` | **Passing** | Regression test against `../fixtures/eoi-sample-01.md` / `-expected.md`. Run `python test_extract_eoi.py` after any rule change. |
| `osc_entry.py` | **Skeleton — not runnable live** | pywinauto entry script mirroring manual steps 4–10. Dry-run by default; live mode is blocked until control IDs are captured. |
| `docx_text.py` | **Working** | Dumps a `.docx`'s visible text as numbered blocks, tables in document order. Stdlib only — no `python-docx` on the server. |
| `docx_diff.py` | **Working** | Block-level diff of two `.docx` files, printing only what differs. Used after a fill to prove nothing but the fields changed. |
| `docx_worddiff.py` | **Working** | Word-level diff of a chosen block, with context. For when a block-level diff says "changed" and you need to see exactly what. |
| `docx_runs.py` | **Working** | Shows the runs around a text anchor. **The tool for re-deriving anchors when a template is revised** and `fill_inclusions.py --check` reports a miss. |
| `pdf_probe.py` | **Working** | Reports whether a PDF has fillable form fields, and its producer. Establishes CD-5.1 — re-run it if a contract template is replaced, in case a fillable one appears. |
| `export_pdf.ps1` | **Working, verified against lot 144's real PDF** | `.docx` → PDF via Word COM, the same Save-as-PDF a person does after finishing the document (CD-7.4 — every completed job keeps the pair). Defaults to the same base name beside the docx; `-From`/`-To` for page-range previews at the review gate; refuses to overwrite without `-Force`. Needs Word on the machine. |
| `new_job_folders.ps1` | **Working, dry-run tested on Z:** | Copies the region's `00000 - LOT MASTER FOLDER` to `<jobno> - <title>` under `Z:\PROJECTS\<region>\` (JD-10). Dry-run by default; `-Commit` asks the operator to re-type the job number; never overwrites. PowerShell 7. Duplicate check matches on the leading 5 digits (real folder names vary around the dash: `26003- LOT`, `16001 -LOT`) and covers the live region, that region's `HANDED OVER` / `ARCHIVE-HANDED OVER` / `CANCELLED` subfolders, and the top-level `COMPLETED` / `CANCELLED CONTRACTS`. |

## Pipeline

```
.msg file ──> msg_to_text.py ──> email.txt
email.txt ──> extract_eoi.py ──> job.json + flags
                                        │  (human reviews sheet, resolves flags,
                                        │   verifies postcode + council by search)
                                        ▼
                                  osc_entry.py --dry-run   (narrates steps)
                                  osc_entry.py --live      (blocked, see below)

new-contract workflow, once the plans are in:

blank template ─┐
job.json ───────┴─> fill_inclusions.py --check   (anchors present?)
                    fill_inclusions.py --out ... ──> INCLUSIONS_LOT ….docx
                                        │  (human reviews field table + diff
                                        │   + a page-1 PDF preview via export_pdf.ps1)
                                        ▼
                                  saved to the job's CONTRACT DOCUMENTATION\
                                  as .docx + .pdf  (export_pdf.ps1, CD-7.4)
```

## Before `--live` can ever run (technical session)

1. On the server with OSC open, capture real control identifiers:
   `inspect.exe` or pywinauto `print_control_identifiers()`; fill the `CTRL`
   map and `OSC_EXE` in `osc_entry.py`.
2. Confirm the approach per `../CLAUDE.md` — OSC write-automation is deferred
   until the technical session with the IT specialist (Adam).
3. Test end-to-end against a **throwaway/test job** in OSC, never a real one.
4. Live mode keeps a HITL gate per screen; the duplicate-search judgment,
   DataBuild email send, and price-mismatch resolution stay human.

## Deliberately not automated

- Lot-number duplicate **judgment** (JD-0.2) — script only reminds.
- Sending the DataBuild email (JD-6.1) — drafted via `transpire-writing`,
  human sends.
- Price comparison resolution (JD-6.2) — hard stop for a human.
- Phase 2 plan updates — pending the same control-mapping session.
- **The build contract itself** (CD-5.1). The current NSW and SEQ contracts are
  flat PDFs with no form fields, so there is nothing to fill; `fill_inclusions.py`
  deliberately has no contract equivalent. The workflow drafts a data sheet and a
  person keys it in.
- **Auxiliary/dual-key inclusions text** (CD-6.3) — a pricing and specification
  decision. Fields are filled, the wording is not.
- Signatures, initials, dates and witness fields (CD-3.7) — never filled.
