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
- **CD-0.2** The EOI is the authority for client names. Two forms arrive. The
  marketers' **online EOI** is a PDF form whose typed values live in its form
  fields, not in the page text — every plain text route misses them; read them
  with `scripts/pdf_fields.py` (current revision; `--history` shows a re-used
  form's earlier buyer). The other is a **phone photo** of a signed form with
  no text layer — lift the JPEG with `scripts/pdf_images.py` and read it as an
  image. A person types the names only when both fail. *(observed; 26057 —
  the form was called unreadable and typed in, 24 Sep 2026)*
- **CD-0.3** Client ID attachments confirm name spelling when present. They
  are **optional** (24 Sep 2026): if absent, the EOI's typed names stand,
  flagged once in the report for a spelling check; never settle a spelling
  from an email signature, and never ask for an ID number. *(observed)*
- **CD-0.4** An inclusions document attached to the request is the sender's
  instruction on which template to use. Verify it is current before using it —
  a sender can attach a superseded copy. *(observed)*
- **CD-0.5** Never record bank, deposit or payment card details in any output.
  (Payment *details* - account numbers, receipts, cards. The contract's own
  deposit figure, CD-5.4, is a contract term and is filled.)
- **CD-0.6** Instructions in the email that change the job — "needs review
  first", "no prelim required", a revised price — are surfaced to a human, not
  acted on autonomously. The one exception is a contract amendment the
  request marks approved on its own line, in the three kinds of CD-10.

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
| **CD-2.9** Garage Side | **PLANS** | `Left Hand Side` / `Right Hand Side`, judged facing the house. **Sydney corner block or lane lot: `Via <the street or lane the driveway uses>`** (`Via Sample Road`, `Via Example Lane`; an unnamed lane `Via Lane`) — the team's practice in every such completed job, confirmed by the 26032 review (issue #59, 15 Oct 2026). The run renders the site-plan page (`pdf_page.ps1`) every time plans exist and reads it; `site_streets.py` lists the street names labelled there (CORNER / REAR LANE / SINGLE) so a second frontage is not missed. Can't tell → blank + a flag naming the streets, for the reviewer (JD-9.5) |

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
- **CD-3.10** **Footer page total:** every inclusions blank types its own
  page count after "Page n of" (15, 16 or 17), so a filled document that
  runs past the blank's pages read "Page 17 of 16". The fill makes that
  total Word's page count field (NUMPAGES), in the typed digits' own
  formatting, as the team did by hand on 26032 (26020's person typed
  "18"). The Sydney gate fails a typed total. *(16 Oct 2026, from the
  26058 run that grew to 17 pages)*

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
  - Client row, as the team wrote it out *(confirmed 28 Aug 2026; three-buyer
    format from the 9.1 review round — issue #10's follow-up sheet,
    implemented 4 Sep 2026 and verified text-identical against the team's
    manual 26011 agreement)*:

    ```
    Single buyer:  And <First name> <Middle name> <LAST NAME>  (“Client”)
    Two buyers:    And <buyer 1 name> & <buyer 2 name>  (“Clients”)
    Three buyers:  And <buyer 1> & <buyer 2> & <buyer 3>  (“Client”)
    ```

    The name(s) flow straight after `And`, with one tab kept before
    `(“Client”)`, which becomes `(“Clients”)` when there are **exactly two**.
    Each name follows CD-3.1 — First name + Middle name + LAST NAME, surname
    in CAPS. The corrected 26052 predates the plural and keeps `(“Client”)`;
    the team confirmed the plural for two, so the filler writes it and
    `regress_prelim.py` normalises before comparing against 26052. **Three
    buyers keep the template's `(“Client”)`** — the 9.1 sheet's written
    format and the manual 26011 both do — which sits oddly beside the
    two-buyer plural; flagged for the team in case one rule should cover
    both (a one-word change in `fill_prelim.py`).
  - `(Current Residential Address)` starts its own paragraph directly under
    the client name (same paragraph properties as the client row), value one
    space after the label — **the split happens even when the job has no
    residential address yet** (9.1 items 3–5: an empty value used to skip
    the split too, gluing the label to the client row and overlapping the
    rules below). `(For Construction Address)`: value five spaces after the
    label, prefixed `Lot `.
  - Signature block: owner 1 two paragraphs above the first `Client Name`
    label, owner 2 two above the second, builders representative three above
    `Name who is authorised…` — typed **Calibri 12** *(confirmed by the team
    28 Aug 2026, chosen over both the blank's 8–9pt rendering and the
    corrected documents' own 10–11pt)*, every name with the same two-space
    lead so the client's and the builder's names start at one edge *(14 Oct
    2026 review, issue #60; the corrected 26032/26052 had a third space
    before Michael CRONK)*. **A third buyer** (`owner_3`, 9.1
    item 6) gets the second client's whole signing row cloned below itself —
    spacers, name line, rule and `Client Name` label — with the Transpire
    authorised-signatory block flowing down, as the manual 26011 lays it out.
  - **Company/trust client** (9.1 item 1): page 1 carries the entity
    (CD-3.9) as usual. When the job JSON names a `company_signatory` —
    sourced from the signed land contract, never derived — the page-3
    signing line takes two lines above the horizontal rule
    (`<signatory>` ⏎ `on behalf of <entity as `owners` carries it, incl.
    ABN/ACN>`) and that row's printed label becomes `Client Name / Company`,
    per the review's reference image.
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
  only on a Word template (CD-5.2b resolves which one); the data sheet of
  person-keyed values is produced every run alongside the filled contract.
  Only a region with neither an approved blank nor a staged interim template
  gets the data sheet alone — never present the contract as generated then.
  *(observed)*
- **CD-5.2** The manual describes editing a Word HIA contract
  (`QLD HIA Contract 1.docx`). Every Word contract of that name is now in `SS\`,
  dated 2016–2017. The manual is behind the drive here — flag it for review.
- **CD-5.2a** **HIA licence held** *(stated by the user 17 Aug 2026; reaffirmed
  18 Aug 2026)*: generating HIA-branded PDFs is permitted, and the target for
  the HIA build contract is a filled `.docx` **plus** its `.pdf` export, like
  the other documents. **Blocked until a current fillable HIA Word template
  exists on the drive**: the `SS\` Word versions stay forbidden (CD-1.3), the
  live blanks are PDFs - NSW's flat with no form fields (CD-5.1), SEQ's a
  fillable form (26 text fields in object streams, seen correctly only from
  27 Oct 2026) - the pipeline fills Word templates, not PDFs, and `HIA BUILD CONTRACT 30.07.2026 - DONT USE UNTIL MCR
  APPROVES.pdf` stays off-limits until MCR approves regardless of licensing.
  **Unblocked 8 Sep 2026 by business instruction**: the staged interim Word
  templates (CD-5.2b) fill real contracts until an approved blank replaces
  them. The data sheet still ships with every run.
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
  2. no candidate → the region's **staged interim template** in
     `runtime\contract-admin\outputs\_hia-word-templates\`, filled under the
     **real deliverable name** in PRODUCTION and TEST alike *(business rule,
     8 Sep 2026: a job with no build contract in `Z:\PROJECTS` gets a real
     contract document, not a blocked data sheet — this replaced the
     18 Aug–7 Sep rule that confined the staged template to TEST runs under
     a `- TEST UNAPPROVED TEMPLATE` name)*. The run report names the interim
     template so the reviewer reads the draft against the licensed PDF before
     issue; issuing stays human regardless (CD-8);
  3. otherwise (no staged template for the region) → **data sheet only**.
  Both staged templates are **the team's own Word builds plus a sanctioned
  interim repair each** (each interim carries fixes the team's own review
  ordered, until the team folds them into its master):
  - **NSW — the v1.1 TABLES interim** (sanctioned repair 3 Sep 2026,
    `make_nsw_v11.py` in the staging folder), on the team's Word build
    (`NSW.BUILD.CONTRACT.Final.docx`, 21 Aug 2026; staged 23 Aug 2026 after
    the end users' review of the 10 test contracts traced every
    build-contract finding to the earlier PDF conversion). The team's
    review of the filled NSW build contract
    (`NSW.BUILD.CONTRACT.updated.8.28.xlsx`, 28 Aug, updated 3 Sep 2026)
    found the same construction QLD's v2 fixed: typed values wrap-crushed
    vertically under narrow labels (cover fields ~950tw usable, item 3
    owners, item 5 land), values rendering in the labels' bold, checklist
    acknowledgement names typed into the `Name (print):` label cell (which
    stretched the box and hid its Date row), and the overflow cascading
    two spill pages (filled 47pp vs the blank's 45). v1.1 rebuilds the
    cover, the item 3 SUBURB|STATE|POSTCODE row and the land block (QLD
    v2.1's twin construction) as label-cell + value-cell tables, puts a
    tab stop at 2233 on the signature NAME lines (the SIGNATURE rules'
    own x, where the manual contracts key the names), and makes the
    sheet's one wording order verbatim — Special Conditions clause 1
    cites **Item 2** (contract price), not Item 3 (owners). The blank
    renders identical to the team build outside those bands (45pp both,
    y-diff to the licensed count); **filled exports hold the licensed 45
    pages**.
  - **QLD — the v2.1 LAND TABLES interim** (sanctioned repair, 3 Sep 2026,
    `make_v21.py`), on the team's v2 (`QLD_HIA_BUILD_CONTRACT_v2.docx`,
    uploaded by the owner 1 Sep 2026 on issue #8; staged 3 Sep 2026,
    superseding the 28 Aug v1.1 ANCHORS interim and the 25 Aug team build
    before it). v2 resolved the 25 Aug build review at source: the
    wrap-crushed label areas (cover fields, Schedule 1 items 3/7, the
    deed's BUILDER IS / OWNER IS) are real label-cell + value-cell tables,
    with the licensed PDF's e-sign anchor codes in the master itself. v2
    missed one wrap area — Schedule 1 item 11's `STREET ADDRESS:` line,
    which cascaded a near-empty spill page (38 vs the licensed 37) — and
    v2.1 applies the same table fix there, band geometry held to the v2
    render within 0.1pt, wording word-identical. Filled exports hold the
    licensed **37 pages** (v1.1: 40 → v2: 38 → v2.1: 37). One item rides
    with MCR's read-through (staging README): v2 moved `/i1/\signer1_sig`
    from the licensed "Owner(s) to initial here" spot to the owner
    SIGNATURE line — confirm it is deliberate.
  `fill_hia.py` types every such value into the empty value cell (mode
  "cell"; `regress_hia.py` asserts the placement row-by-row in both
  regions and that the e-sign anchor codes survive a fill — QLD's six,
  NSW's two witness `/na/`), and every inline/tab-typed value renders
  regular weight (the labels' bold/italic is stripped — review items
  2/7/10/14). What remains before rule 1 takes over is the read-through
  of a filled test output against the licensed PDF and filing the blank
  in `CONTRACT\` (for each master, fold the interim's fix in at source as
  v2 folded in the v1.1 anchors). Once a blank is filed, rule 1 applies
  with no further engineering.
- **CD-5.3** Cover page: owners' name (per client type, CD-1.4), job number, lot,
  site. *(manual)* On the team builds the fill also types (NSW 23 Aug 2026
  per the end users' review; QLD 25 Aug 2026): Schedule 1 owners incl.
  mobile/email, the land (NSW: DP, street, suburb, postcode; QLD: SP/RP,
  street, suburb, state, postcode), the owner signature name, and — only
  when a signed source names them — the guarantor details and the deed's
  BUILDER IS / OWNER IS lines (`guarantor_*` job keys). **Every purchaser's
  mobile and email rides on the contract**, joined `"; "` — the job JSON
  carries the second owner's under `owner_2_mobile` / `owner_2_email` and
  the filler joins them (team review item 8, 3 Sep 2026: all purchaser
  emails are required for DocuSign; the executed multi-owner contracts key
  both). Region specifics: NSW types the builder's rep on the Builder NAME
  line (executed 26044/26040/26036 all key `Michael CRONK`) and the owner
  names — both at the signature NAME lines' 2233 tab stop (v1.1) — plus
  the Attachment A checklist owner names in the value cell beside
  `Name (print):` (box N belongs to owner N; boxes 3/4 stay blank on a
  two-owner job); QLD types the Consumer Building Guide acknowledgement
  NAME(S) on both copies (executed 25163 keys the owner at each) and leaves
  the builder line alone — the QLD build ships it prefilled (Michael CRONK).
  Since the 27 Oct 2026 review (job 26059), QLD types the owner signature
  name at that prefilled name's x and size (a 2219 tw tab stop, 12 pt), so
  the two line up, and item 11's STREET ADDRESS carries the job's estate
  after the street as `Sample Street, (Sample Estate)` - the team's own copy
  of 26059 and the latest SEQ estate contracts. The cover SITE shows that
  same street with `SUBURB STATE POSTCODE` on the line below, its label level
  with the first line: on the team's HIA form one field feeds both places,
  so every executed SEQ contract reads that way (28 Oct 2026).
  Signatures, initials and dates stay human (CD-3.7).
- **CD-5.4** ~~Price excluding GST, GST, total, and the fixed-price component
  all come from DataBuild. Never calculated or inferred.~~ *(manual)*
  **Reversed for NSW, 15 Oct 2026** (issue #62, owner sign-off; the team's
  review sheets of 3 Sep and 14 Oct 2026 asked for it): `fill_hia.py` works
  item 2 and the Part B progress schedule from the request's GST-inclusive
  `price` (the price the inclusions carry, checked against the EOI, CD-2.5),
  by the convention the executed NSW contracts 26045 and 26040 follow:
  - GST = price ÷ 11, to the cent (half up); price excluding GST = price −
    GST, so the two add up exactly;
  - deposit = 10% of the price, rounded **down** to the cent so it never
    passes the statutory 10% cap; a lower deposit the request states
    (`deposit_request`, an amount or `n%`) goes into item 2(b) with a flag
    that the schedule's stage 1 still reads 10%; a higher one is refused;
  - each stage = its printed % × price to the cent (stage 1, the deposit
    stage, rounded down), the last stage taking the rounding balance so the
    schedule always totals the price; the TOTAL row carries the price.
  A DataBuild figure a person keys into the job JSON (`price_incl_gst`,
  `gst_amount`, `price_excl_gst`, `deposit`, `progress_1`..`progress_6`,
  `progress_total`) always wins; the run flags any difference from the
  calculation, and a keyed contract price that differs from the request's.
  The fill report and the run summary show the arithmetic. No usable price:
  item 2 and the schedule stay blank, flagged. Every amount types as
  `$nnn,nnn.nn` (a figure keyed without its `$` used to print bare).
  ~~**QLD is never worked out** (15 Oct 2026, issue #73).~~ **QLD is worked
  out too since 27 Oct 2026** (contract admin review of job 26059: "the
  QLD contract price still can't be filled automatically"). The executed
  SEQ contracts take one figure, the contract price, and the HIA form the
  team fills works out the rest from it; the run does the same from the
  request's `price`:
  - GST = price ÷ 11, to the cent (half up); price excluding GST = price −
    GST (the same cents as the form's price ÷ 1.1 for any price in cents);
  - each Schedule 2 Part B row (CD-5.6) = its printed % × price to the
    cent: DEPOSIT 5% rounded **down** so it never passes the 5% cap,
    PRACTICAL COMPLETION the rounding balance, TOTAL the price.
  DataBuild figures the person gives (typed, or read off a screenshot that
  is read back to them first) still win, at any time: with the request,
  later in the chat, or after the documents are saved (a
  build-contract-only run, which refreshes to template-testing under
  CD-7.7). They are typed as given and the figures not given are worked
  from the contract price given. The run never asks for them or waits. The
  checks only warn: item 2 adds up, the GST is 1/11 of the price, the price
  matches the request, Part B totals the price with each row at its printed
  %, and the deposit is within the 5% the contract prints for a price of
  $20,000 or more. No usable price and no figures: item 2 and Part B stay
  blank, flagged. QC2 has no item 2 deposit; the deposit is Part B's first
  row.
- **CD-5.5** Building period, in contract days: single storey 180; single storey
  duplex 210; double storey 210; double storey duplex 240. *(manual)*
- **CD-5.6** ~~Part B progress payment schedule is copied from DataBuild.~~
  NSW: worked from the contract price since 15 Oct 2026 (CD-5.4, issue #62);
  the template's printed percentages (10 / 10 / 25 / 25 / 20 / 10) are
  checked before anything is typed, and a changed schedule stops the fill
  like any other moved anchor.
  QLD: Part B (the part the team completes, with Transpire's stage
  wording) takes the DEPOSIT, BASE, FRAME, ENCLOSED, FIXING, PRACTICAL
  COMPLETION and TOTAL amounts worked from the contract price, or the
  ones the person gives (CD-5.4, 27 Oct 2026); its printed percentages
  (5 / 15 / 20 / 25 / 20 / 15) are checked the same way. Part A is left as
  printed.
  Consumer building guide and contract index pages are left as they are. *(manual)*
- **CD-5.7** The completed pack is the contract, general conditions, inclusions
  and concept plan assembled together — roughly double the blank's page count.
  *(observed)*

## CD-6 Auxiliary and dual-key dwellings

- **CD-6.1** An EOI marked dual key, or a request mentioning an auxiliary
  dwelling, means the standard range inclusions **do not cover the second
  dwelling**. *(observed — the sales manager's email said so explicitly)*
- **CD-6.2** House type reads `<design> + Auxiliary Unit`. *(observed)*
- **CD-6.3** ~~The aux inclusions text itself is a pricing and specification
  decision. Claude does not write it.~~ **Reversed, signed off 15 Oct 2026**
  (issue #63, option B; built 8 Oct 2026 for job 26032): on the Sydney AUXILIARY blanks the run writes the
  aux dwelling's upgrade lines too, under the same CD-9 rules as the main
  dwelling — each `upgrades` item names its `dwelling`, the row choice and any
  custom wording stay a person's call, and every item is reported with its
  confidence for confirmation before issue (CD-9.11). On the observed job a
  whole `UPGRADED INCLUSIONS – AUX DWELLING` section was added and the existing
  upgrades relabelled `– Main Dwelling`; the 19.08.2026 AUXILIARY blanks now
  carry both headings.
- **CD-6.4** A Sydney-region auxiliary job has its own template variant — use it
  rather than amending the standard one. *(observed)*
- **CD-6.5** The Sydney AUXILIARY blanks go through the full CD-9 edit,
  layout pass and gate like the STANDARD ones (CD-9.11). (Replaces the
  interim fields-only skip proposed on 8 Oct 2026, never merged.) A hand-added section that
  is in neither blank — 26032's `SPECIAL CONDITIONS` — stays a person's edit:
  decided 8 Oct 2026 (option C declined).

## CD-7 Output naming and location

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
- **CD-7.6** Routing is decided **per document, not per job** *(business rule,
  8 Sep 2026, replacing the 17 Aug whole-run switch)*. A document type
  (`INCLUSIONS`, `PRELIMINARY AGREEMENT`, `BUILD CONTRACT`) already in the
  job's `CONTRACT DOCUMENTATION` (`SS\` included) **already exists in
  production**, so a new copy of *that document* is a **test/refresh** and goes
  only to the test destination in CD-7.7; a person promotes it with the CD-7.5
  `SS\` move. A document type **not yet in the folder is a real first draft**
  and is saved into the job folder — whatever else the folder holds. A job that
  already has its inclusions but no build contract therefore gets the build
  contract saved into `Z:\PROJECTS` while the inclusions refresh lands in
  template-testing.
- **CD-7.7** **Destination routing, automatic (17 Aug 2026 — the preview/
  approval gate of 12/16 Aug was removed by explicit instruction; per-document
  since 8 Sep 2026).** The fill run saves in the same pass, each document to
  exactly one of two places: **TEST** (that document already in the job
  folder) →
  `Z:\CLAUDE CODE\cowork-projects\3.new_contract\template-testing\<job>\`,
  finals at the root, working files in `temp\`, refreshable in place;
  **PRODUCTION** (that document not yet in the job folder) → the job's own
  `CONTRACT DOCUMENTATION`, final `.docx`+`.pdf` pair only, never
  overwriting. Enforced by `draft_contract.py --job-dir`, which prints the
  route per document before anything runs. Data gates stay: anchor miss
  aborts, unsourced mandatory values refuse, failed stages block the save,
  price conflicts stop the run.

## CD-9 Sydney inclusions content (instruction, 10 Sep 2026)

Source: the NSW inclusions feedback sheet `NSW.INCLUSIONS.updated.9.9.xlsx`
(issue #35, 15 rows, reviewed 10 Sep 2026) and the instruction of the same
day to build it. It **reverses** the earlier rule that spec content ordered
by the request is a person's edit (the skill's spec-content table, issue
#28's "permanent" carve-out). Sydney INTEGRITY family, and since 28 Oct
2026 the SEQ ESSENTIALS family (CD-9.12); Gunnedah upgrades stay a person's
edit until its template is measured.

- **CD-9.1** The job JSON carries an `upgrades` block: `area`, `storeys`,
  `bathroom2_ground`, `aircon`, `items[]` (each: `category`, `request`,
  `variation_row`, `wording`, `confidence`, optional `replaces` / `mode` /
  `note`). `edit_inclusions.py` applies it after the field fill;
  `word_layout.ps1` re-levels the columns; `gate_inclusions.py` must PASS
  before the document saves.
- **CD-9.2** Section 18 REGIONAL REGULATIONS keeps ONE label/wording pair:
  Box Hill or Gables → `Box Hill` + Recycled Water connection (observed
  26004); North Kellyville → `North Kellyville ONLY` + rain garden (by
  elimination — confirm on the first North Kellyville job); every other
  suburb → `All areas Excl. Box Hill` + Water tank (observed 26019). The
  other two pairs and the red `DELETE NOT APPLICABLE ONE` line are deleted
  in both columns. *(sheet row 2)*
- **CD-9.3** Bathroom 2: no ground-floor Bathroom 2 → the three red notes
  are deleted and the wording stays; ground-floor Bathroom 2 → `Bathroom &
  Ensuite` becomes `Bathroom, Bathroom 2 & Ensuite` on the vanity,
  basin-location and exhaust-fan lines (the pattern of completed 26019) and
  the notes go. *(sheet row 6)*
- **CD-9.4** Air conditioning: not in the request → the promotion item
  **stays** and only the red `(remove if not included)` note goes; a type is
  specified → the item's description is rewritten to it. *(sheet row 11 —
  the 7 Sep 2026 run deleted the whole item, which was wrong)*
- **CD-9.5** Storeys: 2 when the request mentions an upper/first floor or
  gives "ground floor" as a location, else from the design/plans; unknown is
  recorded as unknown. It selects the variation row (single/ground floor vs
  first floor) and is checked against the wording; nothing in the document
  changes with it. *(sheet row 5)*
- **CD-9.6** Wording comes from `Standard Variation Costs 2025 (up to
  220m2).xlsm` (NSW or QLD sheet by region, read live, version date
  reported): drop the leading "Provide", drop "in lieu of …", drop any
  price note; one blank line between items, none inside an item. An
  existing label's wording is replaced (or one line of it, or added to);
  a new label is inserted at the Standard Variation category order with
  its wording level on the right. *(sheet rows 9, 10)*
- **CD-9.7** Only section 18, the three notes and `UPGRADED INCLUSIONS` may
  change. The editor compares every other paragraph of both columns and
  every text outside the body table with the blank and refuses to write on
  any difference. *(sheet row 8)*
- **CD-9.8** Every run black except the package headings (INTERNAL /
  EXTERNAL TURNKEY PACKAGE, UPGRADED INCLUSIONS and its MAIN / AUX DWELLING
  variants), which keep the template's blue (`00B0F0`); no highlight, no run
  shading. *(sheet rows 3, 13; the headings exception from the 14 Oct 2026
  review of job 26032, issue #58, which answered open question 8 and reversed
  the earlier "no exception" reading)*
- **CD-9.9** Layout: the body is one table row with two independent
  columns. After any content change the Word pass measures each label
  against its wording and pads/trims blank left-column paragraphs (a
  fraction of a line as paragraph spacing) until level within 0.5 pt (the
  gate allows 1.5 pt; the margin absorbs the small shifts a later edit
  causes), and puts INTERNAL / EXTERNAL TURNKEY PACKAGE and UPGRADED
  INCLUSIONS at the top of their pages. A re-measure follows, with up to
  four correction rounds. Page-1 values and the page-13 signature lines sit on
  tab stops (one x per column; the owner's name under the builder's; every
  `Date:` on one x, the Owners Witness Name line included — issue #56).
  Section 18 sits one blank line below the NBN wording, on the same page as
  its label: the editor leaves three blank paragraphs above the kept wording
  (one blank line plus the heading's two) whatever the blank had (2 in the
  STANDARD blanks, 11 in the AUXILIARY one — issue #57), and two below it
  (one blank line plus section 19's one-line heading; the blank leaves 1 to
  4 depending on which area pair was kept). When the kept wording starts a
  page (the NBN wording then ends at the foot of the page before), the
  label is levelled onto that page and the heading's two lines would be
  left behind. The pass then puts the heading at the top of the label's
  page, by blank lines above it, and levels the pair from the wording side
  only: whole blank lines and spacing above the wording, or a fraction of
  a line above the label under its heading. Nothing above the heading is
  touched again, in that pass or any correction round, so it is never
  pulled back to the page before. The foot of the table keeps
  one blank paragraph per column: the blanks pad it with 38, which landed
  on a page of their own once the upgrades ran past one page (the section
  after the table starts its own page either way). The gate fails the
  document on any miss, on an empty page (pages inside the body table read
  column by column), on a colour left outside the
  package headings, on a label line whose `Date:` is not on the tab stops,
  or on a section 18 gap or stranded heading. A heading on the page after
  the NBN wording passes only when the kept area wording could not fit
  there: it starts that page beside its label, the heading starts it
  too, and no more than the editor's 3 blank lines follow the NBN
  wording on its page (Word's own placement, no free-line count: the
  wording needs those 3 lines plus 2 of its own). *(sheet rows 1, 4, 12, 14,
  15; the 14 Oct 2026 review of job 26032)*
- **CD-9.10** What stays human: mapping a request line to a Standard
  Variation row, and approving custom wording where no row exists. The run
  reports request → row → wording → confidence per item and a TO CONFIRM
  list; medium/low confidence and custom items are confirmed before issue.
  *(instruction, 10 Sep 2026)*
- **CD-9.11** AUXILIARY blanks *(signed off 15 Oct 2026, issue #63 option B)*: the
  upgrades are two sections, `UPGRADED INCLUSIONS – MAIN DWELLING` then
  `– AUX DWELLING`, each with its own labels and wording. Every `upgrades`
  item carries `dwelling: "main"` or `"aux"`; an item with none on an
  AUXILIARY blank goes under MAIN and is flagged, and an `aux` item on a
  STANDARD blank is refused. Labels are matched, and new ones placed in
  Standard Variation order, within the item's own section; a new label at
  both body columns always end on a blank line (the AUXILIARY blank ends
  them on text, and Word cannot measure a cell's last paragraph for the
  layout pass). Two item keys added
  the same day for any Sydney blank: `mode: "remove"` drops a label with its
  wording (26032 has no alfresco), and `before: "<label>"` puts a new label
  in front of an existing one when the agreed document's order differs from
  the Standard Variation order (labels like Architrave or Trim have no
  category to rank by). Section 18 (whose
  red instruction reads `(DELETE AS REQUIRED)` on these blanks), the Bathroom
  2 notes and lines (the AUXILIARY exhaust fan names its rooms on a
  `Location:` line) and the main dwelling's air conditioning follow CD-9.2–
  9.4. A granny-flat air conditioner is an `aux` item, never a change to the
  main dwelling's ducted system. Both headings stay where the blank puts them
  (each starts a page) and the gate checks them. CD-9.7's scope check covers
  both sections and refuses any change to the headings themselves.

- **CD-9.12** SEQ ESSENTIALS blanks *(contract admin review of job 26059,
  28 Oct 2026)*: the run left `PROMOTIONAL UPGRADES` untouched on the reading
  that contract wording is a person's job and Sydney the only exception; the
  review called that the defect. SEQ follows CD-9.1, 9.5–9.10 on its
  `PROMOTIONAL UPGRADES` section (heading kept in the template's colour,
  last standard label `Letterbox`), with the QLD Variation List sheet.
  CD-9.2–9.4 do not apply (no section 18, no Bathroom 2 notes, no air-con
  note: air conditioning is an ordinary item). The edit, the layout pass and
  the gate run on **every** SEQ job, with or without an `upgrades` block
  (issue #94): NCC Livable Housing is kept on every Queensland job, so the
  blank's yellow-highlighted `19.` is cleared every time, and the layout pass
  keeps `Livable Housing` level with its first line of wording. Rules from
  the review:
  1. A promotion the request names is copied whole from its document
     (`SALES INCLUSIONS - SEPTEMBER PROMOTION 2023.docx`, `promotion.py`):
     Benchtops replace the blank's (`Benchtops – MWC ONLY` on an MWC job);
     Hinges & Drawer Runners, Handles, Shower Screens and Mirrors before
     Plumbing; Plumbing and Electrical lines under the existing labels;
     Oven, Cooktop and Rangehood after Plumbing. A request that changes a
     promotion line replaces it.
  2. Awning windows are not written: the plans carry them.
  3. "Both bathrooms" / "2 bathrooms" is written as the plans name the
     rooms ("to Bathroom and Ensuite").
  4. A credit is a standard item: its wording comes from the inclusions'
     own pages (Carpet, page 10), narrowed to the request, under a new label.
  5. A Standard Variation note that contradicts another request line is
     amended to fit ("… standard range excluding tapware" when black
     tapware is ordered).
  The signature-page lines (Owner 1, Owner 2, Owners Witness, Builders
  Representative, each with its `Date:`) take Sydney's two tab stops
  (CD-9.9, #56). The SEQ blanks type those lines in the same font and text
  box, so the owners' names start under the builder's and every `Date:` sits
  at one x (issue #94, INCLUSIONS row 12). The gate checks them there as it
  does on Sydney; only the page-1 tab-stop check stays Sydney's.
  `variation_list.py` matches sheet names trimmed: the workbook
  names the QLD sheet `QLD Variation List ` (trailing space), so no QLD run
  had read it before.

## CD-10 Approved per-job amendments (sign-off 15 Oct 2026, issue #61)

A request sometimes asks for a per-job change to the contract and marks it
approved on the same line (26032, 12 Oct 2026: "Delete Clause 14. Hidden
Site Conditions – Approved by <director>", "Change late payment interest
rate from 15% to 12% - Approved", and new words for the prelim's clause 4).
Until 15 Oct 2026 a person retyped each of these; the team's review of
26032 called that the defect. The run now applies three kinds itself
(`amendments.py`, `fill_hia.py`, `fill_prelim.py`):

- **CD-10.1** `schedule` (build contract): a schedule value with a stated old
  and new value. Only the late-payment interest rate so far (`field:
  interest_rate`): NSW Schedule 1 item 12, QLD's rate on overdue payments.
  The contract must still read the old value, or the change is refused.
- **CD-10.2** `strike_clause` (build contract, NSW): a whole general-
  conditions clause named by number, struck through from its heading to the
  next clause heading — heading, sub-clauses, their numbers and the margin
  notes, as the team struck clause 14 by hand. Never deleted (the clause
  numbers would move), never part of a clause; the contents line and any
  cross-reference stay as printed and the report counts them for the
  reviewer. A `title`, when given, must match the heading.
- **CD-10.3** `prelim_words` (preliminary agreement): words added to or
  removed from one paragraph of a numbered clause. The request quotes the
  new paragraph (`expect`); the run finds the one paragraph of that clause
  that becomes it by adding or removing words, and refuses rewording.
- **CD-10.4** Every amendment carries its request line verbatim
  (`request_line`). The line must close with its own approval marker
  ("Approved", "Approved by <name>"), must not ask for approval ("to be
  approved", "pending approval"), and must be found word for word in the
  request text saved beside the job JSON (`email*.txt`); a `prelim_words`
  paragraph must be found there too. An approval given anywhere else — a
  separate reply, a chat — does not count.
- **CD-10.5** A refused amendment is reported with its reason and the
  document saves with the template wording; a refusal never blocks the
  save. The report and the run summary list each amendment APPLIED or
  REFUSED with its request line and approval.
- **CD-10.6** Everything else stays with a person and goes, verbatim, under
  `amendments_for_person` in the job JSON and the report: a new clause or
  special condition, rewording an HIA clause, part of a clause, any other
  schedule item, a line without its own marker. The Special Conditions
  validity clause (open question 7) is one of these.

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
| Request asks for a contract change without its own approval marker, or of a kind CD-10 does not cover | List it under `amendments_for_person`; a person makes it (CD-10.6) |
| An approved amendment is REFUSED (old value, title or quoted paragraph does not match) | The document saves with the template wording; a person checks the request and makes the change (CD-10.5) |
| Keyed DataBuild figure ≠ the figure worked from the price | The keyed figure is used; FLAG in the report and the run summary (CD-5.4) |
| Request asks for a deposit over 10% | Refused, 10% used, FLAG (CD-5.4) |
| QLD figures not given | Nothing is asked or waited for; item 2 and Part B are worked from the request price; the person can give DataBuild figures any time, typed or as a screenshot, and those win (CD-5.4, 27 Oct 2026) |
| QLD figures that disagree (item 2 sum, GST, request price, Part B total or %, deposit over 5%) | Typed as given; each disagreement is a FLAG for the person (CD-5.4) |
| Garage side not clear from the rendered site plan | Leave it blank; flag the streets the site plan names for the reviewer, who confirms or asks Michael (JD-9.5) |
| Plans not yet received | Produce the rest; state which fields are unfilled |
| Auxiliary / dual key | Fill fields, route for review before issue (CD-6.3) |
| Template anchor not found by `--check` | Stop; template revised, needs a person |
| A document type already in the job folder | That document refreshes to the template-testing folder; documents not yet there still save into the job folder (CD-7.6/7.7, per document) |
| Preliminary agreement requirement unclear | Ask (CD-4.4) |
| Preliminary fee not stated in the request | Proceed; the standard $30,000 stands (CD-4.3) |
| Client ID missing from the request | Note it; do not guess the name spelling |
| Upgrade request matches no Standard Variation row | Write it as a custom item, `confidence: low`, `variation_row: null`; a person approves the wording (CD-9.10) |
| `gate_inclusions.py` FAILs | The document does not save; fix the cause (template changed, content overflow) and re-run — never hand-fix the output (CD-9.9) |

## Open questions for business review

1. Is the manual's `J# L# Street, Estate Stage - Inclusions` naming retired, or
   is current practice drift that should be corrected? (CD-7.3)
2. The HIA licence (CD-5.2a) makes the HIA build contract's docx+PDF output a
   requirement. The whole pipeline is now built and driver-integrated
   (CD-5.2b: NSW staged on the v1.1 TABLES interim, 3 Sep 2026 — the team's
   21 Aug build plus the team review sheet's layout fixes, filled exports
   at the licensed 45 pages; QLD on the v2.1 LAND TABLES interim,
   3 Sep 2026 — the team's v2 plus the land table fix, filled exports at
   the licensed 37 pages — `fill_hia.py` NSW+QLD commissioned on
   26045/25163, cell mode verified on 26015 and the hamilton-crescent
   dummy, `regress_hia.py` passing); the ONLY remaining step is human — a
   read-through of a filled test output against the licensed PDF (for QLD,
   settling the one flagged item in the staging README with it: the moved
   `/i1/\signer1_sig` placement), MCR approval, file the blank in the
   region's `CONTRACT\` folder. **Since 8 Sep 2026 production runs no
   longer wait for it**: the interim template fills real build contracts
   under the real name, and the run report flags the interim provenance for
   the reviewer. Filing the approved blank swaps the template, nothing else.
   (CD-5.1/5.2)
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
6. ~~The team's build-contract review sheet (item 4, 3 Sep 2026) asks for the
   contract price sections to be completed from the order email's
   GST-inclusive price before any DataBuild/OSC integration exists: item
   2(a) price excl GST + GST + price incl GST, item 2(b) deposit as 10% of
   the inclusive price, and the Part B progress claims per the schedule's
   own percentages. That is a **CD-5.4 reversal** — the rule the sheet
   itself calls "not wrong, but not practical" makes those figures
   DataBuild-only and never computed, because a plausible-but-wrong GST
   split or claim amount in a signed contract is a liability. Deriving
   them is mechanically trivial; the decision (and the rounding rules —
   cents vs dollars, last-claim-as-balance vs rounded percentage, whether
   the derived figures must later reconcile to DataBuild) belongs to the
   business. Held pending that decision.~~ **Answered 15 Oct 2026** (issue
   #62): reversed for NSW with the executed contracts' rounding - cents,
   GST half up, deposit and stage 1 rounded down, the last stage as the
   balance, keyed DataBuild figures win with a flag. QLD followed on
   27 Oct 2026 (the job 26059 review): worked from the request price the way
   the team's HIA form works it, deposit rounded down, practical completion
   the balance; the person's DataBuild figures win (this reverses issue #73's
   "never worked out"). (CD-5.4)
7. Review sheet item 12 asks whether the Special Conditions validity clause
   can be amended per job when the fixed period differs from six months or
   a specific end date is requested ("otherwise, this section may be a
   human spec clause"). Amending clause wording is exactly what the skill
   never does (contract wording is a person's edit), so it stays a human
   spec clause — flagged per run when the request names a validity date.
   Raised here in case the business wants a sanctioned template variant
   instead. (CD-5.2b)
8. The Sydney inclusions blank itself carries the things the 9.9 feedback
   objected to: red instruction notes, blue headings, and a layout that
   keeps labels level with their wording only through blank-paragraph
   padding typed by eye (the blank is up to ~7 pt off in places). The run
   now corrects all of it per document (CD-9.8/9.9), but the durable fix is
   the template owner's: a one-row-per-item table in the NMA master would
   make the alignment structural, and the notes could become Word comments.
   Three CD-9 readings also want a one-line confirmation on the first job
   they meet: North Kellyville pairs with the rain-garden wording (by
   elimination); ~~the blue package headings go black too ("no exception")~~
   answered 14 Oct 2026: they stay blue (CD-9.8, issue #58);
   Bathroom 2 on the ground floor writes "Bathroom 2" into the descriptions
   as 26019 did rather than leaving the note text in the contract. (CD-9)
