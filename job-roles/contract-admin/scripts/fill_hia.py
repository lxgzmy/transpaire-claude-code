r"""Fill an HIA build contract Word template from a job JSON. Stdlib only.

    python fill_hia.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_hia.py --template <blank.docx> --job <job.json> --check
    --region NSW (default) | QLD    picks the anchor set for that edition

STATUS (25 Aug 2026):
  NSW - anchored to the team's own Word build of the NSW contract
        (NSW.BUILD.CONTRACT.Final.docx, built 21 Aug 2026, staged as
        "NSW BUILD CONTRACT Final 21.08.2026 - TEAM BUILD PENDING MCR.docx").
        A real Word-native document, not a PDF conversion - native pagination,
        no reflow artifacts. Still fills to template-testing only until MCR
        files the blank in the region's CONTRACT folder (CD-5.2b rule 1).
  QLD - anchored to the team's own Word build of the QC2 contract
        (QLD.BUILD.CONTRACT.Final.docx, provided 25 Aug 2026), which replaced
        the repaired PDF conversion and its layout risks the same way the NSW
        build did. Since 28 Aug 2026 the staged copy is the sanctioned interim
        "QLD BUILD CONTRACT v1.1 ANCHORS 28.08.2026 - INTERIM PENDING MCR.docx"
        - the team build plus the licensed PDF's e-sign anchor codes
        (/bs1/\builder_sig, /i1/\signer1_sig, four witness /na/), nothing
        else changed; blank still exports at 37 pages. Same gate:
        template-testing only until MCR files the blank in
        REGION - SEQ\CONTRACT (CD-5.2b rule 1).

What it fills (label-anchored, value typed after the printed label - the same
technique as fill_inclusions.py / fill_prelim.py):

  NSW (April 2021 edition, team Word build):
    cover         OWNERS: / JOB: / LOT: / SITE:
    Schedule 1    item 3 Owners: NAME, ADDRESS, SUBURB, STATE, POSTCODE,
                  MOBILE, EMAIL  (ABN/ACN, WORK, HOME left blank)
    The Land      LOT, DP NO, STREET ADDRESS:, SUBURB, POSTCODE (STATE is
                  prefilled NSW in the template)
    item 11       liquidated damages, replaces the $25.00 "per working day" prefill
    item 2(a)/(b) PRICE EXCLUDING GST / GST / CONTRACT PRICE / DEPOSIT -
                  ONLY when the job JSON carries the figures explicitly
                  (price_excl_gst, gst_amount, price_incl_gst, deposit, all
                  formatted "$nnn,nnn.00"). CD-5.4 stands: these come FROM
                  DATABUILD, keyed by a person into the JSON - this script
                  never computes, splits or infers an amount.
    item 14 +     guarantor_name / guarantor_address / guarantor_suburb /
    deed          guarantor_state / guarantor_postcode - only when sourced
                  (a signed land contract or the contract order names them).
                  When a guarantor is present the deed's BUILDER IS / OWNER IS
                  lines are completed too; the deed date is never filled.
    signatures    owner name(s) on the Owner NAME line, builders_rep on the
                  Builder NAME line (executed 26044/26040/26036 all key
                  Michael CRONK there). Signatures themselves stay human.
    Attachment A  checklist acknowledgement: owner_1 / owner_2 after the
                  first / second "Name (print):" (capacity stays blank -
                  it matters only for company or agent signings).

  QLD (QC2, October 2020 edition, team Word build):
    cover        OWNERS: / JOB: / LOT: / SITE:
    guide        Consumer Building Guide owner-acknowledgement NAME(S), both
                 copies (the executed 25163 contract keys the owner at each)
    Schedule 1   item 3 Owner(s): NAME, ADDRESS, SUBURB, STATE, POSTCODE,
                 MOBILE, EMAIL (company/trust buyer: the whole entity string
                 goes in NAME, as the executed 25163 contract does)
    item 2       PRICE EXCLUDING GST / GST / CONTRACT PRICE - ONLY when the
                 job JSON carries the figures explicitly (CD-5.4, as NSW).
                 QC2 has no schedule deposit item: the deposit is a
                 Schedule 2 progress row, never filled (CD-5.6)
    item 7       guarantors - only when sourced; a guarantor also completes
                 the deed's BUILDER IS / OWNER IS lines (deed date never)
    item 11      The land: LOT, SP/RP, STREET ADDRESS:, SUBURB, STATE, POSTCODE
    item 15      late completion damages, replaces the $25.00 "per day." prefill
    signatures   owner name on the Owner NAME line only - the builder line
                 ships prefilled (Michael CRONK, signed for TRANSPIRE
                 CONSTRUCTIONS PTY LTD), so builders_rep is not typed here

What it NEVER fills (CD-5.4): date, interest %, builder's margin %, progress
payment stage amounts, and any figure not explicitly present in the job JSON.
The building and initial periods carry the template's own prefills (NSW build:
52 weeks / 90 + 180 days; QLD build: 210 days / 90 days start / 10 days
inclement weather) and are left untouched for the reviewer - on QLD check the
210 against the job's CD-5.5 period.

Anchor discipline as everywhere else: --check first; a missing anchor is a
revised template and stops the fill. The fill engine tolerates Word's habit
of splitting a printed label across runs (this is why the team's Word build
needs it: "BUILDER IS", "THE DEPOSIT IS:" etc. arrive split), and matching
is whitespace-normalised.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

P_RE = re.compile(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", re.S)
# text nodes and the layout elements that separate them visually
SEG_RE = re.compile(r"(<w:t(?: [^>]*)?>)(.*?)(</w:t>)|(<w:tab/>|<w:br/>|<w:cr/>)", re.S)
# the QLD reflow prints its prefill as "$ 25.00" - tolerate the space
AMOUNT_RE = re.compile(r"\$ ?[\d,]+\.\d{2}")


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_segments(p_xml):
    """The paragraph's visible text as ordered segments.

    Real segments map back to a <w:t> node (span within p_xml); virtual ones
    stand in for tabs/breaks as a single space so labels separated by a tab
    still read "LABEL NEXT" the way Word shows them.
    """
    segs = []
    for m in SEG_RE.finditer(p_xml):
        if m.group(4):
            segs.append({"virtual": True, "text": " "})
        else:
            segs.append({"virtual": False, "span": (m.start(), m.end()),
                         "open": m.group(1), "text": html.unescape(m.group(2)),
                         "orig": html.unescape(m.group(2))})
    return segs


def para_text(p_xml):
    return "".join(s["text"] for s in parse_segments(p_xml))


def label_regex(label):
    """Word splits printed labels across runs and doubles spaces, so a label
    matches its words joined by any whitespace, bounded on both sides (STATE
    must not match inside STATEMENT)."""
    return re.compile(r"(?<!\S)"
                      + r"\s+".join(re.escape(w) for w in label.split())
                      + r"(?!\w)")


def _splice(segs, start, end, text):
    """Replace [start, end) of the segments' joined text with `text`.

    Deletion applies only to real segments (a tab in the middle of a match
    survives - no HIA anchor spans one). The replacement lands where the
    match starts; a pure insertion (start == end) lands at the end of the
    segment holding that offset, so a typed value inherits the label run's
    formatting the way typing in Word after the label would.
    """
    pos, ins_done = 0, False
    for s in segs:
        ln = len(s["text"])
        s_start, s_end = pos, pos + ln
        pos = s_end
        if s["virtual"]:
            continue
        del_from, del_to = max(start, s_start), min(end, s_end)
        if del_from < del_to:
            a, b = del_from - s_start, del_to - s_start
            s["text"] = s["text"][:a] + (text if not ins_done else "") + s["text"][b:]
            ins_done = True
        elif not ins_done and start == end and s_start <= start <= s_end:
            a = start - s_start
            s["text"] = s["text"][:a] + text + s["text"][a:]
            ins_done = True
    if not ins_done:
        for s in reversed(segs):
            if not s["virtual"]:
                s["text"] += text
                return


def _rebuild(p_xml, segs):
    """Write changed segment texts back into their <w:t> nodes."""
    for s in sorted((s for s in segs if not s["virtual"] and s["text"] != s["orig"]),
                    key=lambda s: -s["span"][0]):
        open_tag = s["open"]
        if s["text"] != s["text"].strip() and "xml:space" not in open_tag:
            open_tag = open_tag[:-1] + ' xml:space="preserve">'
        a, b = s["span"]
        p_xml = p_xml[:a] + open_tag + xml_escape(s["text"]) + "</w:t>" + p_xml[b:]
    return p_xml


def fill_para(p_xml, label, value, mode, occ=1):
    """Type value beside the occ-th occurrence of label in this paragraph."""
    segs = parse_segments(p_xml)
    concat = "".join(s["text"] for s in segs)
    if mode == "after":
        hits = list(label_regex(label).finditer(concat))
        if len(hits) < occ:
            return p_xml, False
        m = hits[occ - 1]
        _splice(segs, m.end(), m.end(), f"  {value}")
    elif mode == "replace_amount":
        m = AMOUNT_RE.search(concat)
        if not m:
            return p_xml, False
        _splice(segs, m.start(), m.end(), value)
    else:
        return p_xml, False
    return _rebuild(p_xml, segs), True


# Anchor sets. Field tuples are (json key, printed label, mode[, occurrence]).
# Scope None = whole document, first occurrence.
COVER = [
    ("owners",   "OWNERS:", "after"),
    ("job_no",   "JOB:",    "after"),
    ("lot_no",   "LOT:",    "after"),
    ("site_hia", "SITE:",   "after"),
]
REGIONS = {
    # The team's own Word build of the April 2021 NSW contract (21 Aug 2026).
    # Schedule 1's owner rows are a real table; the deed and checklist are
    # plain paragraphs. Scopes are picked from strings unique-first in
    # document order (the TOC repeats most headings).
    "NSW": {
        "groups": [
            (None, COVER),
            # item 3 Owners - between item 2(b)'s closing note and the
            # builder block's prefilled company name
            (("(The deposit must not exceed", "TRANSPIRE CONSTRUCTIONS"), [
                ("_sch1_owner",    "NAME",     "after"),
                ("owner_address",  "ADDRESS",  "after"),
                ("owner_suburb",   "SUBURB",   "after"),
                ("owner_state",    "STATE",    "after"),
                ("owner_postcode", "POSTCODE", "after"),
                ("owner_mobile",   "MOBILE",   "after"),
                ("owner_email",    "EMAIL",    "after"),
            ]),
            # item 5 The Land (STATE is prefilled NSW in the template)
            (("THE LAND IS:", "must reach the stage"), [
                ("lot_no",        "LOT",             "after"),
                ("dp_no",         "DP NO",           "after"),
                ("land_street",   "STREET ADDRESS:", "after"),
                ("land_suburb",   "SUBURB",          "after"),
                ("land_postcode", "POSTCODE",        "after"),
            ]),
            # item 14 Guarantors - sourced names only, else left blank
            (("(refer to Deed of Guarantee", "Progress Payments Schedule"), [
                ("guarantor_name",     "NAME",     "after"),
                ("guarantor_address",  "ADDRESS",  "after"),
                ("guarantor_suburb",   "SUBURB",   "after"),
                ("guarantor_state",    "STATE",    "after"),
                ("guarantor_postcode", "POSTCODE", "after"),
            ]),
            # Signatures page: the owner block runs to the first witness
            # "/na/" prefill; the builder block runs from there to the
            # e-signing note
            (("has read and understood this contract", "/na/"), [
                ("_sch1_owner", "NAME", "after"),
            ]),
            (("/na/", "electronically signed"), [
                ("builders_rep", "NAME", "after"),
            ]),
            # Deed of guarantee and indemnity - completed only when the job
            # has a sourced guarantor; the deed date is never filled
            (("STATEMENT SETTING OUT THE OWNER", "Background"), [
                ("_deed_builder",      "BUILDER IS",     "after"),
                ("_deed_owner",        "OWNER IS",       "after"),
                ("guarantor_name",     "Guarantors",     "after"),
                ("guarantor_address",  "ADDRESS LINE 1", "after"),
                ("guarantor_suburb",   "SUBURB",         "after"),
                ("guarantor_state",    "STATE",          "after"),
                ("guarantor_postcode", "POSTCODE",       "after"),
            ]),
            # Attachment A checklist acknowledgement (owners' printed names)
            (("Acknowledgement of owners", "Consumer"), [
                ("owner_1", "Name (print):", "after", 1),
                ("owner_2", "Name (print):", "after", 2),
            ]),
        ],
        # item 2: the template ships $000,000.00-style placeholders; each is
        # replaced ONLY when the JSON carries the DataBuild figure (CD-5.4)
        "amounts": [
            ("price_excl_gst", "PRICE EXCLUDING GST:"),
            ("gst_amount",     "GST ON THE ABOVE AMOUNT:"),
            ("price_incl_gst", "THE CONTRACT PRICE IS:"),
            ("deposit",        "THE DEPOSIT IS:"),
        ],
        "liq": ("liq_damages", "per working day"),
    },
    # The team's own Word build of the QC2 October 2020 contract (25 Aug
    # 2026). The schedule pages are multi-column: labels sit in narrow
    # indented columns (several labels share one wrapping paragraph, e.g.
    # "NAME ADDRESS SUBURB", "SUBURB<tab>STATE<tab>POSTCODE"), and a value
    # types inline after its label - the pattern the build's own prefilled
    # builder block uses ("NAME TRANSPIRE CONSTRUCTIONS PTY LTD"). Scopes are
    # picked from strings unique-first in document order (the TOC repeats
    # the schedule headings, so heading-only scopes would land there).
    "QLD": {
        "groups": [
            (None, COVER),
            # Consumer Building Guide - owner acknowledgement, both copies
            # (the executed 25163 contract keys the owner entity at each)
            (("Complete and sign the section below", "For further building information"), [
                ("owners", "NAME(S):", "after", 1),
                ("owners", "NAME(S):", "after", 2),
            ]),
            # item 3 Owner(s) - between item 2's closing note and the
            # builder block's prefilled company name
            (("However, the contract price may include amounts", "TRANSPIRE CONSTRUCTIONS"), [
                ("_sch1_owner",    "NAME",     "after"),
                ("owner_address",  "ADDRESS",  "after"),
                ("owner_suburb",   "SUBURB",   "after"),
                ("owner_state",    "STATE",    "after"),
                ("owner_postcode", "POSTCODE", "after"),
                ("owner_mobile",   "MOBILE",   "after"),
                ("owner_email",    "EMAIL",    "after"),
            ]),
            # item 7 Owner's guarantors - sourced names only, else left blank
            (("Owner's guarantors (Clause 32)", "Default interest rate"), [
                ("guarantor_name",     "NAME",     "after"),
                ("guarantor_address",  "ADDRESS",  "after"),
                ("guarantor_suburb",   "SUBURB",   "after"),
                ("guarantor_state",    "STATE",    "after"),
                ("guarantor_postcode", "POSTCODE", "after"),
            ]),
            # item 11 The land
            (("The land (Clause 6)", "Matters affecting the site"), [
                ("lot_no",        "LOT",             "after"),
                ("sp_rp",         "SP/RP",           "after"),
                ("land_street",   "STREET ADDRESS:", "after"),
                ("land_suburb",   "SUBURB",          "after"),
                ("land_state",    "STATE",           "after"),
                ("land_postcode", "POSTCODE",        "after"),
            ]),
            # Signatures: the owner NAME line only (occurrence 2 is the
            # witness, left for a person) - the builder's line ships
            # prefilled with Michael CRONK in this build
            (("has read and understood this contract", "Michael CRONK"), [
                ("_sch1_owner", "NAME", "after", 1),
            ]),
            # Deed of guarantee and indemnity - completed only when the job
            # has a sourced guarantor; the deed date is never filled
            (("BUILDER IS", "Background"), [
                ("_deed_builder",      "BUILDER IS",     "after"),
                ("_deed_owner",        "OWNER IS",       "after"),
                ("guarantor_name",     "Guarantors",     "after"),
                ("guarantor_address",  "ADDRESS LINE 1", "after"),
                ("guarantor_suburb",   "SUBURB",         "after"),
                ("guarantor_state",    "STATE",          "after"),
                ("guarantor_postcode", "POSTCODE",       "after"),
            ]),
        ],
        # item 2: the three price lines stack in the left column (the GST and
        # CONTRACT PRICE labels share one paragraph) and the three
        # $ 000,000.00 placeholders stack in the next column, in the same
        # order - the third element picks the nth placeholder after the
        # label. Filled ONLY from explicitly keyed DataBuild figures
        # (CD-5.4). No deposit item on QC2: the deposit is a Schedule 2
        # progress row, never filled (CD-5.6).
        "amounts": [
            ("price_excl_gst", "PRICE EXCLUDING GST:",     1),
            ("gst_amount",     "GST ON THE ABOVE AMOUNT:", 2),
            ("price_incl_gst", "THE CONTRACT PRICE IS:",   3),
        ],
        "liq": ("liq_damages", "per day"),
    },
}


def derive_values(values, region):
    """Convenience keys derived from sourced ones - never from thin air."""
    # Schedule 1 / signature NAME: every executed multi-owner job keys the
    # joined names; a company job keys the entity (owner_1) without the ACN
    if not values.get("_sch1_owner"):
        two = (values.get("owner_2") or "").strip()
        values["_sch1_owner"] = (values.get("owners") if two
                                 else values.get("owner_1", "")) or ""
    # NSW job JSONs written before the team build carried "SUBURB POSTCODE"
    # as one value; split it rather than forcing every JSON to be re-authored
    if region == "NSW" and not values.get("land_suburb") and values.get("land_suburb_pc"):
        parts = str(values["land_suburb_pc"]).rsplit(" ", 1)
        values["land_suburb"] = parts[0]
        if len(parts) == 2 and parts[1].isdigit() and not values.get("land_postcode"):
            values["land_postcode"] = parts[1]
    # the deed is only in play when the job actually has a guarantor
    if (values.get("guarantor_name") or "").strip():
        values.setdefault("_deed_builder", "TRANSPIRE CONSTRUCTIONS PTY LTD")
        values.setdefault("_deed_owner", values["_sch1_owner"])
    return values


def run(template, job, out_path, check_only, region):
    anchors = REGIONS[region]
    values = derive_values(json.loads(Path(job).read_text(encoding="utf-8")), region)
    xml = __import__("zipfile").ZipFile(template).read("word/document.xml").decode("utf-8")
    paras = [(m.start(), m.end(), m.group(0)) for m in P_RE.finditer(xml)]

    ptexts = [para_text(p) for _, _, p in paras]
    # whitespace-normalised, for scope and label matching
    ntexts = [re.sub(r"\s+", " ", t) for t in ptexts]

    def first_hit(needle, lo=0, hi=None):
        for i in range(lo, hi if hi is not None else len(ntexts)):
            if needle in ntexts[i]:
                return i
        return None

    def scope_bounds(scope):
        if scope is None:
            return 0, len(ptexts)
        lo = first_hit(scope[0])
        if lo is None:
            return None, None
        hi = first_hit(scope[1], lo + 1)
        return lo, (hi if hi is not None else len(ptexts))

    def find_occurrence(label, lo, hi, occ):
        """(paragraph index, occurrence within that paragraph) or (None, None)."""
        lre, seen = label_regex(label), 0
        for i in range(lo, hi):
            k = len(lre.findall(ntexts[i]))
            if seen + k >= occ:
                return i, occ - seen
            seen += k
        return None, None

    # resolve each field to (paragraph index, key, label, value, mode, occ)
    plan, missing_anchor, blank_fields = [], [], []
    for scope, fields in anchors["groups"]:
        lo, hi = scope_bounds(scope)
        if lo is None:
            missing_anchor.append(f"scope {scope[0]!r} not found")
            continue
        for field in fields:
            key, label, mode = field[:3]
            occ = field[3] if len(field) > 3 else 1
            val = str(values.get(key, "") or "").strip()
            idx, para_occ = find_occurrence(label, lo, hi, occ)
            if idx is None:
                missing_anchor.append(
                    f"{key}: label {label!r} (occurrence {occ}) not in scope "
                    f"{scope and scope[0]}")
                continue
            if not val:
                blank_fields.append((key, label))
                continue
            plan.append((idx, key, label, val, mode, para_occ))

    # item 2 amounts: the label's paragraph, then the nth $-placeholder in it
    # or the next few paragraphs (label and figure sit in separate cells or
    # columns; on the QLD build the placeholders stack, so the spec's third
    # element says which one belongs to this label - default the first)
    for spec in anchors["amounts"]:
        key, label = spec[:2]
        nth = spec[2] if len(spec) > 2 else 1
        lre = label_regex(label)
        idx = next((i for i, t in enumerate(ntexts) if lre.search(t)), None)
        if idx is None:
            missing_anchor.append(f"{key}: label {label!r} not found")
            continue
        hits = [j for j in range(idx, min(idx + 8, len(ntexts)))
                if AMOUNT_RE.search(ntexts[j])]
        if len(hits) < nth:
            missing_anchor.append(
                f"{key}: no $ placeholder (#{nth}) near label {label!r}")
            continue
        val = str(values.get(key, "") or "").strip()
        if not val:
            blank_fields.append((key, label))
            continue
        plan.append((hits[nth - 1], key, label, val, "replace_amount", 1))

    # liquidated damages: the paragraph with both halves of the item
    key, label = anchors["liq"]
    val = str(values.get(key, "") or "").strip()
    idx = next((i for i, t in enumerate(ntexts)
                if label in t and AMOUNT_RE.search(t)), None)
    if idx is None:
        missing_anchor.append(f"{key}: liquidated-damages paragraph not found")
    elif val:
        plan.append((idx, key, label, val, "replace_amount", 1))
    else:
        blank_fields.append((key, label))

    print(f"template : {Path(template).name}")
    print(f"region   : {region}")
    print(f"job      : {Path(job).name}")
    print("STATUS   : CD-5.2b - not MCR-filed; template-testing only, never issuable")
    print()
    print(f"{'field':<18} {'para':>5}  {'label':<18} value")
    print("-" * 80)
    for idx, key, label, val, mode, occ in sorted(plan):
        print(f"{key:<18} {idx:>5}  {label:<18} {val[:40]}")
    for key, label in blank_fields:
        print(f"{key:<18} {'-':>5}  {label:<18} (no value - left blank)")
    if missing_anchor:
        print()
        for msg in missing_anchor:
            print(f"ANCHOR MISSING: {msg}")
        print("The template has been revised (or is not the expected blank) - stopping.")
        return 1
    if check_only:
        print("\n(--check: nothing written)")
        return 0

    # apply, back-to-front so offsets stay valid; all fills for one
    # paragraph compose on the same XML before it is spliced back once
    by_para = {}
    for idx, key, label, val, mode, occ in plan:
        by_para.setdefault(idx, []).append((key, label, val, mode, occ))
    for idx in sorted(by_para, reverse=True):
        start, end, p_xml = paras[idx]
        for key, label, val, mode, occ in by_para[idx]:
            p_xml, ok = fill_para(p_xml, label, val, mode, occ)
            if not ok:
                print(f"FILL FAILED at paragraph {idx} for {key} - stopping, nothing written")
                return 1
        xml = xml[:start] + p_xml + xml[end:]

    import shutil
    import zipfile
    shutil.copy2(template, out_path)
    tmp = Path(str(out_path) + ".tmp")
    with zipfile.ZipFile(out_path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = (xml.encode("utf-8") if item.filename == "word/document.xml"
                    else zin.read(item.filename))
            zout.writestr(item, data)
    tmp.replace(out_path)
    print(f"\nwritten  : {out_path}")
    print("Not MCR-filed - a person must review it against the licensed PDF; "
          "it is not issuable.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--region", default="NSW", choices=sorted(REGIONS))
    args = ap.parse_args()
    if not args.check and not args.out:
        sys.exit("ERROR: give --out or --check")
    return run(args.template, args.job, args.out, args.check, args.region)


# This console is cp1252; contract text carries curly quotes and dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
