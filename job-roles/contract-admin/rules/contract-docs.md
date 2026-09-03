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
  acknowledgements text box. Format **`First name + Middle name + LAST NAME`**,
  surname in CAPS. The middle name is included whenever the client ID shows
  one — it is the half most often missed, because it rarely appears in the
  request email and has to be read off the licence or passport (CD-0.3). The
  same name is typed in the preliminary agreement (CD-4.5), so both documents
  read alike. *(Format confirmed by the team 28 Aug 2026; observed on executed
  25176, which carries `Shaun Leslie MCMEEKEN` in the inclusions and the
  agreement alike. Earlier revisions of this rule said `Firstname SURNAME`.)*
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
- **CD-4.3** **$30,000 is the standard preliminary fee — it stands unless the
  request names another.** *(Reversed 28 Aug 2026 by the team's review of the
  AI-filled documents — `AI.Manual.comparison (2).xlsx`, Preliminary Agreement
  sheet: "$30,000 is the standard prelim fees amount, please proceed the
  preliminary agreement prepare without asking even not specify in the email.
  Prelim agreement fee is only amended when specify request in the contract.")*
  A job JSON without `prelim_fee` keeps the template's figure; a supplied fee
  replaces it. Do not stop or ask for a missing fee. History: the rule
  originally required a sourced fee because completed agreements ranged
  $2,500–$32,035 (both Tamworth jobs $5,000) — that variance is real, but the
  team owns it; only a fee stated in the request changes the figure.
- **CD-4.4** The request email may say no preliminary agreement is required. One
  was still produced on the observed job (26045 — email said "no need for
  Prelim agreement", the folder holds an executed one). Ask — do not resolve it
  either way.
- **CD-4.5** Fill conventions *(rebuilt 28 Aug 2026 from the team's review —
  `AI.Manual.comparison (2).xlsx`, Preliminary Agreement sheet — and its three
  corrected Sydney references, jobs 26019/26032/26052; `regress_prelim.py`
  reproduces 26032 and 26052 space-for-space. Supersedes the Tamworth-pair
  conventions of 16 Aug 2026: the review rejects exactly those cosmetics —
  names on tab stops, the 62-space label pad, cloned signature fonts)*:
  - Client row, as the team wrote it out *(confirmed 28 Aug 2026)*:

    ```
    Single buyer:  And <First name> <Middle name> <LAST NAME>  (“Client”)
    Two buyers:    And <buyer 1 name> & <buyer 2 name>  (“Clients”)
    ```

    The name(s) flow straight after `And`, with one tab kept before
    `(“Client”)`, which becomes `(“Clients”)` when there are two. Each name
    follows CD-3.1 — First name + Middle name + LAST NAME, surname in CAPS.
    The corrected 26052 predates the plural and keeps `(“Client”)`; the team
    confirmed the plural, so the filler writes it and `regress_prelim.py`
    normalises before comparing against 26052.
  - `(Current Residential Address)` starts its own paragraph directly under
    the client name (same paragraph properties as the client row), value one
    space after the label. `(For Construction Address)`: value five spaces
    after the label, prefixed `Lot `.
  - Signature block: owner 1 two paragraphs above the first `Client Name`
    label, owner 2 two above the second, builders representative three above
    `Name who is authorised…` — typed **Calibri 12** *(confirmed by the team
    28 Aug 2026, chosen over both the blank's 8–9pt rendering and the
    corrected documents' own 10–11pt)*.
- **CD-4.6** **The master template was corrected at source on 28 Aug 2026**, so
  these faults no longer ship in the blank a person opens:
  - the third paragraph of `3. ENDING AGREEMENT` (the sunset-clause insertion)
    was indented `left 720` where its neighbours are `left 820 / right 105`
    justified BodyText, and the empty spacer above it was a condensed 9.5pt
    paragraph — both now carry the neighbours' properties;
  - the client row's `&` run held a tab that pushed a typed name onto a tab
    stop — removed. The single tab before `(“Client”)` is deliberate and stays.

  The outgoing blank is filed as
  `SS\NSW PRELIMINARY AGREEMENT 2024 - superseded 28.08.2026.docx`. The swap was
  proved output-neutral first: identical wording, byte-identical filled XML from
  either blank, unchanged 3-page pagination, and `regress_prelim.py` still
  reproducing 26019/26032/26052.

  **The filler keeps normalising both on every fill** — now a no-op on both
  templates, retained as a guard for older copies, restored files, and any
  future revision that reintroduces them. The sibling
  `NSW PRELIMINARY AGREEMENT 2024 - STAGE F2 - LOTS 12XX AND 18XX.docx` was
  corrected the same way later that day (its spacer was already right, so only
  the client-row tab and the sunset indent changed; outgoing blank filed as
  `SS\... - superseded 28.08.2026.docx`), verified by the same checks:
  wording byte-identical, fill output-neutral, 3-page pagination unchanged,
  the deliberate tab before `(“Client”)` kept.

## CD-5 Build contract — filled when a Word template exists, data sheet always

- **CD-5.1** The live NSW and SEQ build-contract **PDFs are flat, with no form
  fields** — a PDF can never be filled programmatically here. The fill happens
  only on a Word template (CD-5.2b resolves which one, if any); the data sheet
  of person-keyed values is produced every run, and in PRODUCTION with no
  MCR-approved Word blank it is the whole deliverable — never present the
  contract as generated then. *(observed)*
- **CD-5.2** The manual describes editing a Word HIA contract
  (`QLD HIA Contract 1.docx`). Every Word contract of that name is now in `SS\`,
  dated 2016–2017. The manual is behind the drive here — flag it for review.
- **CD-5.2a** **HIA licence held** *(stated by the user 17 Aug 2026; reaffirmed
  18 Aug 2026)*: generating HIA-branded PDFs is permitted, and the target for
  the HIA build contract is a filled `.docx` **plus** its `.pdf` export, like
  the other documents. **Blocked until a current fillable HIA Word template
  exists on the drive**: the `SS\` Word versions stay forbidden (CD-1.3), the
  live blanks are flat PDFs with no form fields (CD-5.1), the server cannot
  fill a flat PDF, and `HIA BUILD CONTRACT 30.07.2026 - DONT USE UNTIL MCR
  APPROVES.pdf` stays off-limits until MCR approves regardless of licensing.
  Until unblocked, produce the CD-5 data sheet.
- **CD-5.2b** **Detection is automated** *(18 Aug 2026)*: `hia_probe.py`
  classifies every build-contract blank in the region's contract-template
  folder, and `draft_contract.py --job-dir` runs it on every routed save —
  the verdict prints in the run summary and ships as `hia_status.txt` with the
  evidence. The **fill is driver-integrated** *(18 Aug 2026, by explicit
  instruction to streamline the build contract)*: on every `--job-dir` fill
  run, `draft_contract.py` resolves a template in this order and fills it via
  `fill_hia.py` (region-aware NSW/QLD anchor sets, `regress_hia.py` is its
  regression) —
  1. an approved CANDIDATE `.docx` in the region's `CONTRACT\` folder (a
     person + MCR filed it) → filled under the **real deliverable name**, in
     TEST or PRODUCTION; the anchor `--check` is the automated regression
     gate, and the first fill after a template lands is eye-verified;
  2. no candidate, **TEST mode only** → the staged template in
     `runtime\contract-admin\outputs\_hia-word-templates\`, filled under a
     `- TEST UNAPPROVED TEMPLATE` name (never issuable);
  3. otherwise (PRODUCTION, no approved blank) → **data sheet only**, and the
     run says BLOCKED.
  Both staged templates are **the team's own Word builds**: NSW
  (`NSW.BUILD.CONTRACT.Final.docx`, built 21 Aug 2026; staged 23 Aug 2026 in
  response to the end users' review of the 10 test contracts, whose
  build-contract findings — text artifacts, misalignment, pagination spill,
  blank pages — all traced to the earlier PDF conversion) and QLD v2
  (`QLD_HIA_BUILD_CONTRACT_v2.docx`, uploaded by the owner 1 Sep 2026 on
  issue #8; staged 3 Sep 2026, superseding the 28 Aug v1.1 ANCHORS interim
  and the 25 Aug team build before it). v2 resolved the 25 Aug build review
  at source: the wrap-crushed label areas (cover fields, Schedule 1 items
  3/7, the deed's BUILDER IS / OWNER IS) are real label-cell + value-cell
  tables — `fill_hia.py` types those values into the empty value cell
  (mode "cell", 3 Sep 2026; `regress_hia.py` asserts the placement
  row-by-row and that the six e-sign anchor codes survive a fill) — and
  the licensed PDF's anchor codes are in the master itself. Two items ride
  with MCR's read-through (staging README): Schedule 1 item 11's `STREET
  ADDRESS:` line still wraps any typed value (filled exports run 38 pages
  vs the licensed 37, down from the 25 Aug build's 40), and v2 moved
  `/i1/\signer1_sig` from the licensed "Owner(s) to initial here" spot to
  the owner SIGNATURE line. What remains before rule 1 takes over is that
  read-through of a filled test output against the licensed PDF and filing
  the blank in `CONTRACT\` — no repair work. Once a blank is filed, rule 1
  applies with no further engineering.
- **CD-5.3** Cover page: owners' name (per client type, CD-1.4), job number, lot,
  site. *(manual)* On the team builds the fill also types (NSW 23 Aug 2026
  per the end users' review; QLD 25 Aug 2026): Schedule 1 owners incl.
  mobile/email, the land (NSW: DP, street, suburb, postcode; QLD: SP/RP,
  street, suburb, state, postcode), the owner signature name, and — only
  when a signed source names them — the guarantor details and the deed's
  BUILDER IS / OWNER IS lines (`guarantor_*` job keys). Region specifics:
  NSW types the builder's rep on the Builder NAME line (executed
  26044/26040/26036 all key `Michael CRONK`) and the Attachment A checklist
  owner names; QLD types the Consumer Building Guide acknowledgement
  NAME(S) on both copies (executed 25163 keys the owner at each) and leaves
  the builder line alone — the QLD build ships it prefilled (Michael CRONK).
  Signatures, initials and dates stay human (CD-3.7).
- **CD-5.4** Price excluding GST, GST, total, and the fixed-price component all
  come **from DataBuild**. Never calculated or inferred. *(manual)* Both
  team builds ship `$000,000.00`-style placeholders for these; `fill_hia.py`
  replaces them **only** when a person has keyed the DataBuild figures into
  the job JSON (`price_excl_gst`, `gst_amount`, `price_incl_gst`, and on NSW
  `deposit` — QC2 has no schedule deposit item; its deposit is a Schedule 2
  progress row, never filled) — it never derives one figure from another,
  and the contract order's price is not a substitute for DataBuild. Progress
  stage amounts are never filled (CD-5.6).
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
- **CD-7.6** Existing contract documents in the job folder (`SS\` included)
  mean the job **already exists in production**, so the run is a **test run**
  (17 Aug 2026, superseding the earlier report-and-ask amendment stop): output
  goes only to the test destination in CD-7.7, and the job folder is not
  touched. A genuine amendment is produced the same way; a person promotes it
  into the job folder with the CD-7.5 `SS\` move.
- **CD-7.7** **Destination routing, automatic (17 Aug 2026 — the preview/
  approval gate of 12/16 Aug was removed by explicit instruction).** The fill
  run saves in the same pass, to exactly one of two places: **TEST** (job
  already has contract documents) →
  `Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\`,
  finals at the root, working files in `temp\`, refreshable in place;
  **PRODUCTION** (genuine first draft) → the job's own `CONTRACT
  DOCUMENTATION`, final `.docx`+`.pdf` pair per document only, never
  overwriting. Enforced by `draft_contract.py --job-dir`. Data gates stay:
  anchor miss aborts, unsourced mandatory values refuse, failed stages block
  the save, price conflicts stop the run.

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
| Contract documents already in the job folder | Test mode: save only to the template-testing folder (CD-7.6/7.7) |
| Preliminary agreement requirement unclear | Ask (CD-4.4) |
| Preliminary fee not stated in the request | Proceed; the standard $30,000 stands (CD-4.3) |
| Client ID missing from the request | Note it; do not guess the name spelling |

## Open questions for business review

1. Is the manual's `J# L# Street, Estate Stage - Inclusions` naming retired, or
   is current practice drift that should be corrected? (CD-7.3)
2. The HIA licence (CD-5.2a) makes the HIA build contract's docx+PDF output a
   requirement. The whole pipeline is now built and driver-integrated
   (CD-5.2b: both regions staged on the team's own Word builds — NSW 23 Aug
   2026, QLD v2 3 Sep 2026 — `fill_hia.py` NSW+QLD commissioned on
   26045/25163, cell mode verified on 26015, `regress_hia.py` passing); the
   ONLY remaining step is human — a read-through of a filled test output
   against the licensed PDF (for QLD, settling the two flagged v2 items in
   the staging README with it: the land line's residual one-page spill, and
   the moved `/i1/\signer1_sig` placement), MCR approval, file the blank in
   the region's `CONTRACT\` folder. Until then production runs stay
   data-sheet-only. (CD-5.1/5.2)
3. ~~What sets the preliminary work fee, and should the template default be
   removed to stop it being carried over?~~ **Answered 28 Aug 2026** by the
   team's review sheet: $30,000 is the standard fee and stands unless the
   request names another — the filler no longer refuses a missing fee. Rule
   reversed. (CD-4.3)
3a. ~~The blank `NSW PRELIMINARY AGREEMENT 2024.docx` itself carries the
   misaligned sunset-clause paragraph and spacer, and its client row renders
   the AI-rejected tab-stop layout — should the master template be corrected
   instead of normalised per fill?~~ **Answered 28 Aug 2026:** yes. The master
   was corrected at source, the outgoing blank filed in `SS\`, and the per-fill
   normalisation kept as a guard. The Stage F2 sibling got the same correction
   later that day. (CD-4.6)
4. ~~`ESTATE` is blank on every recent NSW job — is the field retired?~~
   **Answered 13 Aug 2026:** not retired. Sydney job 26004 uses it for the
   pre-registration parent address + estate name. Rule updated. (CD-2.4)
5. Who approves aux/dual-key inclusions, and is there an approved template for
   them outside Sydney? (CD-6.3/6.4)
