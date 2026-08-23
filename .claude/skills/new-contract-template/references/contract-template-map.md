# Contract template map — `Z:\PROCEDURES & FORMS\CONTRACTS\`

Which blank template to copy, and what is superseded. Verified against the live
drive **11 Aug 2026**. Read this before picking a template; do not reason from
filenames alone, because several look current and are not.

`PROCEDURES & FORMS` holds **blank forms only** — never a completed document.
The filled copy always goes to the job folder (see [Output](#output-where-the-filled-copy-goes)).

## The one rule that prevents most mistakes

**`SS` means superseded. Never copy anything from an `SS` folder.** Every level of
this tree has one. The root `SS\` folder holds 66 files dated 2015–2018,
including a dozen near-identical `NSW CONTRACT BLANK - INCLUDING COMSUMER GUIDE`
variants (the misspelling is in the real filenames). They look like templates.
They are not.

Also never use a file whose name tells you not to:
`HIA BUILD CONTRACT 30.07.2026 - DONT USE UNTIL MCR APPROVES.pdf`, and anything
under `REGION - SYDNEY\INCLUSIONS\TO BE AMENDED - NMA\`.

## Region → template

The drive's job regions are `GUNNEDAH`, `SEQ`, `SYDNEY`, `TAMWORTH`, `CUDGEN`,
but there are only **three** contract-template folders. They do not line up
one-to-one, which is the main trap here:

| Job region | Inclusions template folder | Build contract / prelim |
|---|---|---|
| `TAMWORTH`, `GUNNEDAH` | `REGION - GUNNEDAH, NSW\` | NSW — from `REGION - SYDNEY\CONTRACT\` |
| `SYDNEY` | `REGION - SYDNEY\INCLUSIONS\` | `REGION - SYDNEY\CONTRACT\` |
| `SEQ`, `CUDGEN` | `REGION - SEQ\INCLUSIONS\` | `REGION - SEQ\CONTRACT\` |

There is **no Tamworth contract folder**. Tamworth jobs take the
`REGION - GUNNEDAH, NSW` inclusions and the NSW build contract that happens to
be filed under Sydney. Verified: the four Westdale/Tamworth jobs (lots 141–144)
all derive from the Gunnedah INTEGRITY template.

`REGION - GUNNEDAH, NSW\` is small on purpose — one live inclusions document:

```
Gunnedah INTEGRITY Range + Turnkey Inclusions - NCC 2022 - V4 Transpire 08.11.24.docx
```

Despite the 08.11.24 in the name it was last changed 24 Apr 2026, and it is the
current one. `SS\` beside it holds the V3.

## Current live templates

Everything below is outside an `SS` folder and outside a "do not use" folder.

**Root of `CONTRACTS\`** — region-independent:

| File | Use |
|---|---|
| `Contract Cover.docx` | Cover sheet for the contract pack |
| `Gunnedah Agreement.docx` | Gunnedah/NSW agreement |
| `Authority to Commence.docx` | Authority to start work |
| `Lot xxx Deed of Rescission Building Contract.docx` | Rescinding an existing contract |

**`REGION - SYDNEY\CONTRACT\`** — also the source of the NSW documents:

| File | Notes |
|---|---|
| `NSW BUILD CONTRACT.pdf` | 45 pages, **not a fillable form** — see below |
| `NSW PRELIMINARY AGREEMENT 2024.docx` | Fillable. Fee in the template is **not** the job's fee |
| `NSW PRELIMINARY AGREEMENT 2024 - STAGE F2 - LOTS 12XX AND 18XX.docx` | Gables stage F2 only |
| `BUILD CONTRACT - GABLES B-205.pdf`, `SALES CONTRACT - GABLE STAGE F2 …` | Gables-specific |
| `Consumer_Building_Guide - May 2016.pdf` | Goes in the pack |

**`REGION - SEQ\CONTRACT\`**: `HIA BUILD CONTRACT 09.02.2023_Template Updated 30.07.26.pdf` (37 pages),
`HIA - General Conditions - able to add to contract.pdf`.

**Inclusions, by client type** — SEQ splits by who the client is, Sydney by range
and promotion. Pick on client type first, then range, then any promotion:

- `REGION - SEQ\INCLUSIONS\INVESTOR & FIRST HOME OWNER\` — eight numbered
  ESSENTIALS Range variants, several named for a specific marketer or estate.
- `REGION - SEQ\INCLUSIONS\OWNER OCCUPIER\` — `Owner Occupier Essentials Range of Inclusions`.
- `REGION - SYDNEY\INCLUSIONS\` — `1.`–`4.` Sydney INTEGRITY Range: standard and
  auxiliary, each with and without the 10 year celebration promotion. Plus
  `5. Contract Clauses.docx` and `INTEGRATED LOTS - GABLES INCLUSIONS\`.

A marketer or estate name in a template filename means it is **for that marketer
or estate only**. Do not use it as a generic template.

## The build contract is not a fillable template

This is the boundary of what can be drafted here, and it should be stated to the
user rather than worked around.

`NSW BUILD CONTRACT.pdf` and the SEQ HIA contract are flat PDFs — no form
fields at all (probed: `AcroForm` present but zero text fields, zero widgets).
The completed article in a job folder runs to ~90 pages, roughly double the
blank, because it is the **assembled pack**: contract, general conditions,
inclusions and concept plan together, per the manual's "Add your contract
documents" step.

So: the inclusions and the preliminary agreement can be produced as completed
Word documents. The build contract itself is keyed in and assembled by a person.
Draft the values for it; do not claim to have produced it.

The manual still describes editing a **Word** HIA contract
(`QLD HIA Contract 1.docx`). Every Word contract of that name now sits in `SS\`,
dated 2016–2017. The manual is behind the drive on this point.

**HIA licensing (17 Aug 2026):** the business holds a valid HIA licence, so
HIA-branded PDF output is permitted, and the standing requirement (CD-5.2a) is
that the HIA build contract ship as a filled `.docx` + `.pdf` pair. That stays
**blocked** until a current fillable HIA Word template reaches this tree — the
`SS\` Word versions remain forbidden, and
`HIA BUILD CONTRACT 30.07.2026 - DONT USE UNTIL MCR APPROVES.pdf` remains
off-limits until MCR approves, licence or not.

Detection is automated (18 Aug 2026): `hia_probe.py` classifies every
build-contract blank in this tree (SUPERSEDED / OFF-LIMITS / FLAT PDF /
FILLABLE PDF / CANDIDATE) and `draft_contract.py --job-dir` runs it on every
routed save, so each run reports the current status instead of restating this
paragraph from memory.

The unblock candidates are staged in
`runtime\contract-admin\outputs\_hia-word-templates\` (README there has the
full audit), deliberately OUT of this tree until MCR files one here as the
live blank:

- **NSW — the team's own Word build** (`NSW.BUILD.CONTRACT.Final.docx`,
  built 21 Aug 2026, staged 23 Aug 2026). Word-native layout, price
  placeholders, prefilled builder block; it replaced the earlier repaired
  PDF conversion, whose reflow artifacts were what the end users flagged in
  the first testing round. What remains is MCR's read-through of a filled
  test output against the licensed PDF, then filing the blank here.
- **QLD — still the repaired conversion** (18 Aug 2026: `pdf_to_docx.ps1` +
  `pdf_docx_fidelity.py` to 100.00% text completeness, insertions
  highlighted). A person still reviews the highlights and repairs layout
  page by page against the PDF before MCR approval — or better, the team
  provides a QLD Word build like the NSW one.

The fill step is built and driver-integrated (18 Aug 2026; NSW re-anchored
to the team build 23 Aug 2026): `fill_hia.py` (NSW + QLD anchor sets,
`regress_hia.py` passing, verified on 26045/26032/25163) runs inside every
`draft_contract.py --job-dir` fill — staged template in TEST runs under a
`- TEST UNAPPROVED TEMPLATE` name, and the moment an approved blank lands
here the probe reports CANDIDATE (its name match tolerates the team's dotted
file naming) and the same run fills it under the real deliverable name
(anchor `--check` gates it; eye-verify the first fill after any template
lands). (The 17 Aug reflow trial in `_hia-conversion-trial\` is superseded.)

## Output: where the filled copy goes

```
Z:\PROJECTS\<REGION>\<job folder>\CONTRACT\CONTRACT DOCUMENTATION\
```

**Unless the job already exists in production** — that folder already holding
any contract document makes the run a test run (CD-7.6/7.7), and everything
saves to `Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\`
instead. `draft_contract.py --job-dir` routes this automatically.

Current filename convention, counted across every `CONTRACT DOCUMENTATION`
folder in `TAMWORTH` and `GUNNEDAH`:

```
INCLUSIONS_LOT <lot>_<SUBURB>_<SURNAME>.docx      (25 files)
BUILD CONTRACT_LOT <lot>_<SUBURB>_<SURNAME>.pdf   (17)
PLANS_LOT <lot>_<SUBURB>_<SURNAME>.pdf            (11)
PRELIMINARY AGREEMENT_LOT <lot>_<SUBURB>_<SURNAME>.docx  (7)
```

Suburb and surname in CAPS; underscores between parts; the `.docx` is kept
alongside the `.pdf` export. Superseded versions move to an `SS\` subfolder
inside the job's own contract folder, suffixed ` V2`, ` V3`.

**The manual gives a different, older convention** —
`J# L# Street, Estate Stage - Inclusions`. No file on the drive uses it now.
Follow the files, not the manual, and flag the discrepancy if it matters.

## Related folders worth knowing

- `Z:\ESTATES INFORMATION\NSW\TAMWORTH\WESTDALE\` — per-lot folders, certified
  construction plans, 88B, section 10.7 planning certificate. Where lot-specific
  facts come from when the email doesn't carry them.
- `Z:\PROCEDURES & FORMS\COLOURS\` — the internal colour selection options that
  go out with the contract.
- `Z:\ESTIMATING\1. Contracts & Inclusions\` — specification changes and upgrade
  packs. Not contract templates; check it when an inclusion looks out of date.
