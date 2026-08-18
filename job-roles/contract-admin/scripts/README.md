# scripts/

Scripts for the new-contract workflow (`../workflows/new-contract.md`).
(The new-job intake scripts — `extract_eoi.py`, `test_extract_eoi.py`,
`osc_entry.py` — were removed with the `/ca-new-job` skill, 18 Aug 2026.)

| Script | Status | Does |
|---|---|---|
| `msg_extract.py` | **Working — the .msg route, no install** | Pure-stdlib OLE/CFBF reader for Outlook `.msg`: `--list` attachments, `-a <dir>` saves them, `-o` saves the body text. Built 16 Aug 2026 because `extract_msg` isn't installed anywhere (installing needs approval) and the job folders keep the original request `.msg` whose attachments (signed land contracts, EOIs, plans) are the field sources. Use this first for `.msg` files. |
| `msg_to_text.py` | Superseded by `msg_extract.py` | Outlook `.msg` → plain text; needs `pip install extract-msg`, which no server has. Kept only for environments that already carry the package. |
| `fill_inclusions.py` | **Working, validated against 12 real jobs across 3 regions** | Blank inclusions template + job JSON → filled `.docx` (`CD-2`, `CD-3`). Stdlib only — edits `word/document.xml` in place inside the zip, inserting values as new runs after each label the way Word does, so the template's wording, styles and inclusion text are untouched. Fills every occurrence, because the signature pages are duplicated for the builder's and owner's copies. `--check` verifies every anchor exists and writes nothing — **run it first**; a missing anchor means the template was revised. One deliberate deletion (`DELETE_PARAS`): the SEQ narrow-lot instruction line, which every completed SEQ job removes — the follow-on block decision (≤12.5m ⇒ a person deletes the block too) is printed every time. |
| `draft_contract.py` | **Working — the pipeline driver** | One timed command for a whole job, ending in the save (the preview/approval stop was removed 17 Aug 2026): anchor check (aborts the document on a miss), fill (inclusions and/or `--prelim`), blank-vs-filled diffs, complete PDF exports through a **single Word launch**, then **`--job-dir` routing** — the job's `CONTRACT DOCUMENTATION` already holding contract docs (SS\ included) = TEST (finals + `temp\` to `template-testing\<job>\` only, `--real-dir` defaulting to the job folder for REAL_ exports + worddiffs); empty = PRODUCTION (final `.docx`+`.pdf` pair into the job folder, never overwriting). A failed stage blocks the save. Typical run 25–50s, ~85% of it Word PDF export. **`--deliver <folder>`** stays for explicit handover folders (refuses `Z:\PROJECTS`; `--deliver-force` for test refreshes) — end users see only the finals. Company/trust owners name correctly (`_VWJJ`, never `_LTD`). |
| `fill_prelim.py` | **Working — reproduces both completed Tamworth agreements text- and structure-identically** | Blank `NSW PRELIMINARY AGREEMENT 2024.docx` + job JSON → filled `.docx` (`CD-4`). Same stdlib run-editing approach. Client row (single-client also removes the tab so the name flows after "And", as every completed single does), addresses, fee and the three signing-line names, per the conventions verified across eight completed agreements (CD-4.5). **Refuses to run without `prelim_fee`** — the template's $30,000 is not the job's fee (CD-4.3). `--check` first, as with the inclusions. |
| `regress_prelim.py` | **Passing** | Fills the blank prelim with each completed Tamworth job's values and requires the result to be **text-identical AND structure-identical** (tabs/breaks/cells via the `docx_text` view) to the real executed agreement, plus a two-client structural smoke test. Run after any `fill_prelim.py` change, alongside `regress_inclusions.py`. |
| `test_job_search.py` | **Passing** | Keeps the job-location logic in step with its owner. The canonical "where can a job folder be" logic is the org z-drive-ops skill's `find_job.ps1`; `probe_job.py` mirrors it in Python. This checks the two agree, that every lifecycle-like folder on the live drive is covered, and that a real job in each location is actually found. `probe_job.py` missed `SYDNEY\HANDED OVER` (199 jobs) before this existed. |
| `docx_text.py` | **Working** | Dumps a `.docx`'s visible text as numbered blocks, tables in document order. Stdlib only — no `python-docx` on the server. |
| `regress_inclusions.py` | **Passing** | Per family: reads the page-1 indent convention off every completed job, fills the blank with a sample job's values, and checks the filler reproduces the convention **and** the acknowledgements site-address line word-for-word (where `at;Lot` — the missing SEQ space — hid until 16 Aug). Run after any `fill_inclusions.py` change. |
| `docx_diff.py` | **Working** | Block-level diff of two `.docx` files, printing only what differs. Used after a fill to prove nothing but the fields changed. |
| `docx_worddiff.py` | **Working** | Word-level diff of a chosen block, with context. For when a block-level diff says "changed" and you need to see exactly what. |
| `docx_runs.py` | **Working** | Shows the runs around a text anchor. **The tool for re-deriving anchors when a template is revised** and `fill_inclusions.py --check` reports a miss. |
| `pdf_probe.py` | **Working** | Reports whether a PDF has fillable form fields, and its producer. Establishes CD-5.1 — re-run it if a contract template is replaced, in case a fillable one appears. |
| `pdf_text.py` | **Working** | Extracts text from a PDF's content streams (stdlib zlib, no PDF library). Enough to pull house size and garage side off Archicad plans (CD-2.7, CD-2.9). `--grep PATTERN` filters. |
| `pdf_images.py` | **Working** | Lifts embedded JPEGs out of a PDF byte-for-byte (`/DCTDecode`). EOIs and client IDs arrive as phone photos wrapped in a PDF (CD-0.2) and the server has no rasteriser, so the photos are read as images instead. |
| `probe_job.py` | **Working, parity-tested** | One call answering everything new-contract step 2 asks about a job: folder location across every lifecycle level, existing contract docs, cancelled twin at the same lot, neighbours. Mirrors `z-drive-ops/scripts/find_job.ps1`; `test_job_search.py` fails if the two drift. |
| `export_pdf.ps1` | **Working, verified against lot 144's real PDF** | `.docx` → PDF via Word COM, the same Save-as-PDF a person does after finishing the document (CD-7.4 — every completed job keeps the pair). Accepts **arrays** (`-Docx a,b -Out x,y`) and exports them all through one Word instance — start-up dominates the cost, so batch every PDF a run needs. Defaults to the same base name beside the docx; `-From`/`-To` for page-range previews; refuses to overwrite without `-Force`. Needs Word on the machine. |
| `new_job_folders.ps1` | **Working, dry-run tested on Z:** | Copies the region's `00000 - LOT MASTER FOLDER` to `<jobno> - <title>` under `Z:\PROJECTS\<region>\` (JD-10). Dry-run by default; `-Commit` asks the operator to re-type the job number; never overwrites. PowerShell 7. Duplicate check matches on the leading 5 digits (real folder names vary around the dash: `26003- LOT`, `16001 -LOT`) and covers the live region, that region's `HANDED OVER` / `ARCHIVE-HANDED OVER` / `CANCELLED` subfolders, and the top-level `COMPLETED` / `CANCELLED CONTRACTS`. |

## Pipeline

```
.msg file ──> msg_extract.py ──> email text + attachments (stdlib, no install)

new-contract workflow, once the plans are in — one driver command, fill to save:

blank template ─┐
job.json ───────┴─> draft_contract.py [--prelim] --job-dir "<job's CONTRACT DOCUMENTATION>"
                      = check ─> fill ─> blank-diff ─> complete PDF exports
                        (one Word launch) ─> REAL_ exports + worddiffs (test mode)
                                        │
                                        ├─ job folder already has contract docs
                                        │  = TEST: finals + temp\ ONLY to
                                        │    template-testing\<job>\  (CD-7.7)
                                        ▼
                                  else PRODUCTION: .docx + .pdf pair into the
                                  job's CONTRACT DOCUMENTATION\ (CD-7.4, never
                                  overwrites; flags reported after, not gated)
```

## Deliberately not automated

- **OSC job entry** — the `/ca-new-job` intake and its `osc_entry.py` skeleton
  were removed 18 Aug 2026; OSC write-automation stays deferred until the
  technical session with the IT specialist (Adam), per `../CLAUDE.md`.
- **The build contract itself** (CD-5.1). The current NSW and SEQ contracts are
  flat PDFs with no form fields, so there is nothing to fill; `fill_inclusions.py`
  deliberately has no contract equivalent. The workflow drafts a data sheet and a
  person keys it in.
- **Auxiliary/dual-key inclusions text** (CD-6.3) — a pricing and specification
  decision. Fields are filled, the wording is not.
- **Whether a job needs a preliminary agreement at all** (CD-4.4) — the request
  email's word has been wrong in practice; a person decides, `fill_prelim.py`
  only fills.
- Signatures, initials, dates and witness fields (CD-3.7) — never filled.
