# Contract Document Rules — raising a build contract

Field rules for producing contract documents from a build contract request.
Referenced as `CD-*` by the `new-contract-template` skill and
[`../workflows/new-contract.md`](../workflows/new-contract.md).

**Status: transcribed + observed, pending business review.** Two sources:

1. **The manual** — "RAISING CONTRACTS" in
   `Z:\PROCEDURES & FORMS\ADMINISTRATION\INTERNAL - System and Procedures Manual.docx`.
   Marked *(manual)* below. Not copied into this repo — it carries PII.
2. **The drive** — the blank templates diffed against four completed jobs in
   `Z:\PROJECTS\TAMWORTH` (lots 141–144, contracted May–July 2026). Marked
   *(observed)*.

Where they disagree, the drive is current and the manual is behind. Both are
recorded, because the manual is the approved procedure and the difference is
something the business should settle. Do not extend these rules by inference.

Address, CAPS and garage-side rules are **not restated here** — they live in
[`job-details.md`](job-details.md) as `JD-2`, `JD-9.3` and `JD-9.5` and apply
unchanged.

## CD-0 Reading the request

- **CD-0.1** Read the entire forwarded chain. The instruction to contract admin
  is in the **newest** layer; the job facts (design, façade, price, buyer) are in
  the **oldest**, from the marketer. *(observed)*
- **CD-0.2** The EOI is the authority for client names. It is frequently a phone
  photo of a signed form with no text layer — read it as an image. *(observed)*
- **CD-0.3** Client ID attachments confirm name spelling. If absent, note it;
  do not settle a spelling from an email signature. *(observed)*
- **CD-0.4** An inclusions document attached to the request is the sender's
  instruction on which template to use. Verify it is current before using it —
  a sender can attach a superseded copy. *(observed)*
- **CD-0.5** Never record bank, deposit or payment card details in any output.
- **CD-0.6** Instructions in the email that change the job — "needs review
  first", "no prelim required", a revised price — are surfaced to a human, not
  acted on autonomously.

## CD-1 Template selection

- **CD-1.1** Blank templates come only from `Z:\PROCEDURES & FORMS\CONTRACTS\`.
  A completed document from another job is **never** the template. *(manual)*
- **CD-1.2** Select on region → client type → range → promotion. The three
  template folders do not map one-to-one onto the five job regions: `TAMWORTH`
  and `GUNNEDAH` jobs both use `REGION - GUNNEDAH, NSW`, and take the NSW build
  contract and preliminary agreement from `REGION - SYDNEY\CONTRACT`. *(observed)*
- **CD-1.3** Never use a file in an `SS\` folder, a file marked "DONT USE", a
  file under `TO BE AMENDED`, or a file named for a different marketer or estate.
  *(observed)*
- **CD-1.4** Client types are **Investor**, **Residential**, and **Transpire
  Constructions**; the contract pack differs per type. For Transpire
  Constructions as owner, the owner name is `Transpire Constructions Pty Ltd`,
  and its email and mobile are left blank. *(manual)*
- **CD-1.5** The pack is: HIA New Construction Contract, HIA General Conditions,
  Inclusions, Concept Plans, Internal Colour Selection Options. *(manual)*
- **CD-1.6** State the chosen template's full path and the reason before filling.
  Two plausible candidates → ask.

## CD-2 Inclusions, page 1 header

Nine fields, all on page 1. *(manual, confirmed observed)*

| Field | Source | Format |
|---|---|---|
| **CD-2.1** Lot No | Email subject / EOI | Number only |
| **CD-2.2** Street | Email / job folder | Keeps the house number in brackets when the job folder does: `(3) Pioneer Close` |
| **CD-2.3** Suburb | Email / EOI | `SUBURB STATE`, CAPS: `WESTDALE NSW` |
| **CD-2.4** Estate | Job folder / neighbouring lot | Blank on the four observed Tamworth jobs — but **not retired**: Sydney job 26004 (Lot 113, Box Hill) fills it with the pre-registration parent address plus estate, `37 Mason Road, (Luxus Estate)`. When a lot is unregistered and the request email carries a parent street address that is not the lot's street, that address belongs here, not in STREET. **SEQ (observed 16 Aug 2026, 7 jobs):** when the job-folder name carries a bracketed estate, fill it in title case as the most recently contracted completed neighbour spells it (`Forestone Estate`, `Somerfield West`) — the older Forestone jobs (26033/26034) left it blank, the newer ones (26038/26050/26051) fill it; recency wins. No estate in the folder name (infill, 26053) → blank. The same estate goes into the SEQ site address as `<street> (<Estate>),` — no comma before the bracket (majority; 26050's `, (` is one typist) |
| **CD-2.5** Price | Request email | `$` + thousands separators + `.00`. Disagrees with the EOI → **stop**, do not average or prefer one |
| **CD-2.6** House Type | Email "Design:" | Design name; auxiliary dwellings read `<design> + Auxiliary Unit`, not the email's shorthand (CD-6) |
| **CD-2.7** House Size | **PLANS** | `nnn.nn m²`. Not in the email — absent until plans arrive (JD-9.3) |
| **CD-2.8** House Façade | Email "Facade:" | `<name> Façade`. Neighbouring files use both `Façade` and `Facade`; match the template |
| **CD-2.9** Garage Side | **PLANS** | `Left Hand Side` / `Right Hand Side`, judged facing the house. Unclear → escalate (JD-9.5) |

## CD-3 Inclusions, owner and signature blocks

Pages 10–13. *(manual: "Page 10 … Page 13"; confirmed observed)*

- **CD-3.1** Owner names appear in **five** places for owner 1, plus the
  acknowledgements text box. Format `Firstname SURNAME`. *(observed)*
- **CD-3.1a** The acknowledgements text box carries **all** owners joined by
  ` & ` — not just owner 1. Verified on lot 113 Box Hill (two owners) and
  lot 141 Westdale (three). `fill_inclusions.py` takes this as the `owners`
  key, falling back to `owner_1` when unset. *(observed 13 Aug 2026)*
- **CD-3.2** Owner 2 is left blank for a single owner — the dotted line stays.
- **CD-3.3** The site address on the acknowledgements page is the full
  `Lot <n>, <street>, <SUBURB> <STATE> <postcode>`. The postcode is **verified by
  lookup**, never assumed (JD-2.6). *(observed)*
- **CD-3.4** `LOT No` / `STREET` / `SUBURB` repeat on the client signature and
  acknowledgement pages and must match page 1 exactly. *(observed)*
- **CD-3.5** Builders Representative is **Michael Cronk**. *(manual)*
- **CD-3.6** Every signature block is duplicated for the builder's copy and the
  owner's copy. Fill both — the manual says "repeat this on the Builders and
  Owners copy". *(manual)*
- **CD-3.7** Dates, signatures, initials and witness fields are left **empty**.
  Claude never fills, signs, or initials them. Per the manual a person initials
  pages 1–12 and signs pages 10–13; that is a person's job.
- **CD-3.9** **Company / trust buyer** *(observed 26039, 16 Aug 2026)*: Owner 1
  takes the full contracting entity as the signed land contract writes it —
  `VWJJ INVESTMENT No.1 PTY LTD ATF WANG AND LIU No.1 FAMILY TRUST` — Owner 2
  stays empty, and the acknowledgements box appends the ACN. The signer line
  (`<Director> on behalf of <entity>`) and the deletion of the unused Owner-2
  rows are a person's edits at signing. **The entity must come off the signed
  land contract**: the same job's attached ASIC extract named a sibling company
  (no `No.1`, different ACN) — an ASIC extract is context, not the authority.
- **CD-3.8** **Three or more owners:** owner 1 and owner 2 fill their slots as
  usual and the acknowledgements box carries all owners (CD-3.1a) — but the
  third owner's rows are a **manual template edit**: the one observed job
  (26044) repurposed the Owners Witness rows into `Name of Owner 3` /
  `Signature of Owner 3` by hand. Claude fills owners 1–2, puts every owner in
  `owners`, and flags the rest for a person. *(observed 16 Aug 2026)*

## CD-4 Preliminary agreement

- **CD-4.1** NSW jobs use `NSW PRELIMINARY AGREEMENT 2024.docx` from
  `REGION - SYDNEY\CONTRACT\`. *(observed)*
- **CD-4.2** Fields: client name, current residential address, construction
  address, and the preliminary work fee. Signature block takes the client name
  and Michael Cronk.
- **CD-4.3** **The fee in the template is not the job's fee.** The template reads
  $30,000; both completed Tamworth jobs used $5,000, and completed agreements
  across regions range $2,500–$32,035. Always sourced or confirmed, never
  carried over — `fill_prelim.py` refuses to run without a fee. *(observed)*
- **CD-4.4** The request email may say no preliminary agreement is required. One
  was still produced on the observed job (26045 — email said "no need for
  Prelim agreement", the folder holds an executed one). Ask — do not resolve it
  either way.
- **CD-4.5** Fill conventions, verified across eight completed agreements
  (jobs 26036/26045 Tamworth — reproduced text-identically by
  `regress_prelim.py` — plus five Sydney and one Gunnedah for structure):
  a single client's name replaces the template's `&` as `  <name>`; two
  clients keep the cells — name 1 after `And`, name 2 after `&`; addresses
  are typed after their labels; and every job types owner 1 two paragraphs
  above the first `Client Name` label, owner 2 two above the second, and the
  builders representative three above `Name who is authorised…` — the printed
  signing lines. Sydney jobs vary the cosmetic spacing (1–9 spaces, no
  convention); the Tamworth pair agree exactly and are the reference.
  *(observed 16 Aug 2026)*

## CD-5 Build contract — data sheet only

- **CD-5.1** The current NSW and SEQ build contracts are **flat PDFs with no form
  fields**. They cannot be filled programmatically. Produce a data sheet for a
  person to key in; never present the contract as generated. *(observed)*
- **CD-5.2** The manual describes editing a Word HIA contract
  (`QLD HIA Contract 1.docx`). Every Word contract of that name is now in `SS\`,
  dated 2016–2017. The manual is behind the drive here — flag it for review.
- **CD-5.3** Cover page: owners' name (per client type, CD-1.4), job number, lot,
  site. *(manual)*
- **CD-5.4** Price excluding GST, GST, total, and the fixed-price component all
  come **from DataBuild**. Never calculated or inferred. *(manual)*
- **CD-5.5** Building period, in contract days: single storey 180; single storey
  duplex 210; double storey 210; double storey duplex 240. *(manual)*
- **CD-5.6** Part B progress payment schedule is copied from DataBuild.
  Consumer building guide and contract index pages are left as they are. *(manual)*
- **CD-5.7** The completed pack is the contract, general conditions, inclusions
  and concept plan assembled together — roughly double the blank's page count.
  *(observed)*

## CD-6 Auxiliary and dual-key dwellings

- **CD-6.1** An EOI marked dual key, or a request mentioning an auxiliary
  dwelling, means the standard range inclusions **do not cover the second
  dwelling**. *(observed — the sales manager's email said so explicitly)*
- **CD-6.2** House type reads `<design> + Auxiliary Unit`. *(observed)*
- **CD-6.3** The aux inclusions text itself is a **pricing and specification
  decision**. Claude does not write it. Fill the fields, then route for review
  before issue. On the observed job a whole `UPGRADED INCLUSIONS – AUX DWELLING`
  section was added and the existing upgrades relabelled `– Main Dwelling`.
- **CD-6.4** A Sydney-region auxiliary job has its own template variant — use it
  rather than amending the standard one. *(observed)*

## CD-7 Output naming and location

- **CD-7.1** Completed documents go to
  `Z:\PROJECTS\<region>\<job>\CONTRACT\CONTRACT DOCUMENTATION\`. Blank templates
  never leave `PROCEDURES & FORMS`. *(observed)*
- **CD-7.2** Naming: `<DOCTYPE>_LOT <lot>_<SUBURB>_<SURNAME>.<ext>`, where
  DOCTYPE is `INCLUSIONS`, `BUILD CONTRACT`, `PLANS` or `PRELIMINARY AGREEMENT`.
  Suburb and surname CAPS. *(observed, 60 files across TAMWORTH and GUNNEDAH)*
  A company/trust owner's name token is the trustee company's **first word**
  (`_VWJJ` for `VWJJ INVESTMENT No.1 PTY LTD ATF ...`), never `_LTD`/`_TRUST`
  *(observed 26039)*. Human files sometimes shorten an unusual surname
  (26053's `REDDY&SURA` for surname REDDYREDDY) — the actual surname is the
  convention; the shorthand is that file's typing.
- **CD-7.3** The manual's older convention is
  `J# L# Street, Estate Stage - Inclusions`. No current file uses it. Follow the
  files; flag the discrepancy.
- **CD-7.4** Both the `.docx` and its `.pdf` export are kept. *(observed)*
- **CD-7.5** Superseded versions move to an `SS\` subfolder **within the job's
  contract folder**, suffixed ` V2`, ` V3`. Never overwrite — existing file at
  the target name → stop and ask. *(observed)*
- **CD-7.6** Existing contract documents in the job folder mean this is an
  **amendment**, not a first draft. Report and ask before producing anything.

## CD-8 What only a person does

Recorded so the checklist is complete, not so Claude attempts any of it:
keying and assembling the build contract; emailing the contract to the marketer;
checking initials and signatures; signing and witnessing; attaching documents in
OnSite Companion; scanning the executed set; the manila folder for the filing
cabinet; and any DocuSign issue to a client.

## Escalations

| Situation | Action |
|---|---|
| Price in email ≠ price on EOI | Stop; hand to a human (CD-2.5) |
| Garage side not left/right | Escalate to Michael (JD-9.5) |
| Plans not yet received | Produce the rest; state which fields are unfilled |
| Auxiliary / dual key | Fill fields, route for review before issue (CD-6.3) |
| Template anchor not found by `--check` | Stop; template revised, needs a person |
| Contract documents already in the job folder | Stop; treat as amendment (CD-7.6) |
| Preliminary agreement requirement unclear | Ask (CD-4.4) |
| Client ID missing from the request | Note it; do not guess the name spelling |

## Open questions for business review

1. Is the manual's `J# L# Street, Estate Stage - Inclusions` naming retired, or
   is current practice drift that should be corrected? (CD-7.3)
2. Should the NSW build contract exist as a fillable template, given the Word
   version is superseded and the PDF cannot be filled? (CD-5.1/5.2)
3. What sets the preliminary work fee, and should the template default be
   removed to stop it being carried over? Observed range $2,500–$32,035;
   both Tamworth jobs $5,000. (CD-4.3)
4. ~~`ESTATE` is blank on every recent NSW job — is the field retired?~~
   **Answered 13 Aug 2026:** not retired. Sydney job 26004 uses it for the
   pre-registration parent address + estate name. Rule updated. (CD-2.4)
5. Who approves aux/dual-key inclusions, and is there an approved template for
   them outside Sydney? (CD-6.3/6.4)
