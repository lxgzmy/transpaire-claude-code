r"""Fill an HIA build contract Word template from a job JSON. Stdlib only.

    python fill_hia.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_hia.py --template <blank.docx> --job <job.json> --check
    --region NSW (default) | QLD    picks the anchor set for that edition

STATUS (3 Sep 2026):
  NSW - anchored to the v1.1 TABLES interim (staged as "NSW BUILD CONTRACT
        v1.1 TABLES 03.09.2026 - INTERIM PENDING MCR.docx", sanctioned
        repair 3 Sep 2026, built by make_nsw_v11.py in the staging folder):
        the team's own Word build of the April 2021 contract (21 Aug 2026)
        plus the fixes the team's build-contract review sheet ordered
        (NSW.BUILD.CONTRACT.updated.8.28.xlsx) - the same label-cell +
        value-cell treatment QLD's v2/v2.1 got, in the areas the review
        marked. The cover fields, Schedule 1 item 3 owners (whose SUBURB
        row split into SUBURB|STATE|POSTCODE label+value cells) and item 5
        The Land (the LOT / CERTIFICATE OF TITLE / STREET ADDRESS: column,
        QLD v2.1's twin) are real value-cell tables now; the signature
        NAME lines carry a tab stop at the SIGNATURE lines' own x; and
        Special Conditions clause 1 cites Item 2 (contract price), not
        Item 3 - the sheet's one wording order. Blank renders identical
        to the team build outside those bands (45pp both). Since 8 Sep 2026
        the driver fills real contracts from it under the real name (CD-5.2b
        rule 2); MCR filing a blank in the region's CONTRACT folder swaps
        the template (rule 1).
  QLD - anchored to the v2.1 LAND TABLES interim (staged as "QLD BUILD
        CONTRACT v2.1 LAND TABLES 03.09.2026 - INTERIM PENDING MCR.docx",
        sanctioned repair 3 Sep 2026): the team's v2 Word build of the QC2
        contract (QLD_HIA_BUILD_CONTRACT_v2.docx, uploaded 1 Sep 2026 on
        issue #8) plus the same table fix applied to the one wrap-prone
        area v2 missed. v2 rebuilt the cover fields, Schedule 1 item 3
        (owners), item 7 (guarantors) and the deed's BUILDER IS / OWNER IS
        lines as real label-cell + value-cell tables; v2.1 (make_v21.py in
        the staging folder) does the same for item 11 The land, whose
        STREET ADDRESS: line had no room for any typed value and cascaded
        a near-empty spill page. A typed value now always lands in a wide
        empty cell - filled exports hold the licensed 37 pages (v1.1
        filled at 40, v2 at 38, v2.1 at 37). The e-sign anchor set rides
        at source (/bs1/\builder_sig, four witness /na/; /i1/\signer1_sig
        moved by the team's v2 to the owner SIGNATURE line, where the
        licensed PDF and the old v1.1 interim had it at Special Conditions
        "Owner(s) to initial here" - flagged for MCR's read-through, no
        fill impact). Supersedes the 28 Aug v1.1 ANCHORS interim and the
        25 Aug team build. Same standing as NSW: real fills since 8 Sep
        2026; MCR filing the blank in REGION - SEQ\CONTRACT swaps the
        template (CD-5.2b rule 1).

What it fills (label-anchored - the same technique as fill_inclusions.py /
fill_prelim.py. Mode "after" types the value inline after the printed label,
as its own regular-weight run - bold/italic/underline are stripped, since
the completed contracts key values regular beside bold printed labels
(review items 2/7/10/14); mode "tab" does the same but leads with a tab, for
lines whose value column is a tab stop; mode "cell" - the QLD v2 / NSW v1.1
table layout - lands it in the empty table cell beside the label's cell, the
way a person typing in the value column would):

  NSW (April 2021 edition, team Word build + v1.1 TABLES interim):
    cover         OWNERS: / JOB: / LOT: / SITE: - value cells since v1.1
    Schedule 1    item 3 Owners: NAME, ADDRESS, SUBURB, STATE, POSTCODE and
                  EMAIL in value cells; MOBILE inline after its label
                  (ABN/ACN, WORK, HOME left blank). A second owner's
                  contact keys (owner_2_mobile / owner_2_email) join the
                  first with "; " - every purchaser's mobile and email
                  rides on the contract, DocuSign needs them (review
                  item 8; the executed multi-owner contracts key both)
    The Land      LOT, DP NO and STREET ADDRESS: in value cells; SUBURB,
                  POSTCODE inline (STATE is prefilled NSW in the template)
    item 11       liquidated damages, replaces the $25.00 "per working day" prefill
    item 2(a)/(b) PRICE EXCLUDING GST / GST / CONTRACT PRICE / DEPOSIT, and
    Part B        the Progress Payments Schedule's six stage amounts and TOTAL -
                  worked from the request's GST-inclusive `price` by the
                  executed contracts' convention (CD-5.4 / CD-5.6, issue #62,
                  15 Oct 2026; contract_figures shows the arithmetic in the
                  report). A DataBuild figure a person keys into the JSON
                  (price_excl_gst, gst_amount, price_incl_gst, deposit,
                  progress_1..6, progress_total) always wins; a difference is
                  flagged. No usable price: everything stays blank, flagged.
    item 14 +     guarantor_name / guarantor_address / guarantor_suburb /
    deed          guarantor_state / guarantor_postcode - only when sourced
                  (a signed land contract or the contract order names them).
                  When a guarantor is present the deed's BUILDER IS / OWNER IS
                  lines are completed too; the deed date is never filled.
    signatures    owner name(s) on the Owner NAME line, builders_rep on the
                  Builder NAME line (executed 26044/26040/26036 all key
                  Michael CRONK there), both typed at the lines' 2233 tab
                  stop - the x the SIGNATURE rules start at, where the
                  manual contracts key the names (review item 13).
                  Signatures themselves stay human.
    Attachment A  checklist acknowledgement: owner_1 / owner_2 in the value
                  cell beside the first / second "Name (print):" box - the
                  boxes were already label|value tables; typing in the
                  label cell stretched it and hid the Date row (review
                  items 15-16). Capacity stays blank - it matters only
                  for company or agent signings.

  QLD (QC2, October 2020 edition, team v2 Word build):
    cover        OWNERS: / JOB: / LOT: / SITE:
    guide        Consumer Building Guide owner-acknowledgement NAME(S), both
                 copies (the executed 25163 contract keys the owner at each)
    Schedule 1   item 3 Owner(s): NAME, ADDRESS, SUBURB, STATE, POSTCODE,
                 MOBILE, EMAIL (company/trust buyer: the whole entity string
                 goes in NAME, as the executed 25163 contract does)
    item 2       PRICE EXCLUDING GST / GST / CONTRACT PRICE - worked from the
                 request's GST-inclusive `price` the way the HIA form the team
                 fills works them out (27 Oct 2026 review, reversing issue #73's
                 "never worked out"); figures a person gives from DataBuild,
                 typed or read off a screenshot, at any time, still win
    Schedule 2   Part B amounts: DEPOSIT, BASE, FRAME, ENCLOSED, FIXING,
                 PRACTICAL COMPLETION and TOTAL, worked from the same price
                 (QC2 has no item 2 deposit: the deposit is Part B's first
                 row); the printed percentages are checked first (CD-5.6).
                 The checks on the figures are warnings only
    item 7       guarantors - only when sourced; a guarantor also completes
                 the deed's BUILDER IS / OWNER IS lines (deed date never)
    item 11      The land: LOT, SP/RP, STREET ADDRESS:, SUBURB, STATE, POSTCODE;
                 a job's `estate` goes after the street as "Street, (Estate)",
                 and the cover SITE shows that street with SUBURB STATE
                 POSTCODE below it, as the team's HIA form does (27-28 Oct
                 2026 review). NSW item 5 takes the same "Street, (Estate)"
                 and its cover SITE reads "Street, (Estate), SUBURB NSW
                 postcode" on one line (job 26061 feedback, 9 Nov 2026)
    item 15      late completion damages, replaces the $25.00 "per day." prefill
    signatures   owner name on the Owner NAME line only, at the x and size of
                 the builder's name below it (27 Oct 2026 review) - the builder
                 line ships prefilled (Michael CRONK, signed for TRANSPIRE
                 CONSTRUCTIONS PTY LTD), so builders_rep is not typed here

What it NEVER fills (CD-5.4): date, interest %, builder's margin %, and any
figure that is neither keyed in the job JSON nor worked from its contract
price as above. Every amount types as "$nnn,nnn.nn", padded after the "$" so
the amounts of one column line up on their digits (feedback sheet 5 Nov 2026
row 5).
The building and initial periods carry the template's own prefills (NSW build:
52 weeks / 90 + 180 days; QLD build: 90 days start / 10 days inclement
weather) - except QLD item 13's 210 days, which becomes the team's figure for
the job's storeys and house size: single 210, double under 300 m2 240, over
260; unknown keeps 210, flagged (CD-5.5, feedback sheet row 11).

Feedback sheet of 5 Nov 2026, also: a company owner (owner_names.py) names its
ACN with the company everywhere, sized to its line (font_fit.py), with
"<company_signatory> on behalf of <company> ACN: ..." under the owner's
signature NAME and the QLD guide NAME(S); the deed reads "Transpire
Constructions Pty Ltd"; a guarantor with no address takes the owner's,
flagged (rows 8-13, CD-3.9). NSW Special Conditions clause 1 takes the
request's price-validity date when the job JSON carries the request's line
and that line is in the saved request text (row 6, CD-10.7). NSW site streets
bracket their house number (street_format.py, row 7).

Anchor discipline as everywhere else: --check first; a missing anchor is a
revised template and stops the fill. The fill engine tolerates Word's habit
of splitting a printed label across runs (this is why the team's Word build
needs it: "BUILDER IS", "THE DEPOSIT IS:" etc. arrive split), and matching
is whitespace-normalised. Mode "cell" validates structure as well as text:
the label paragraph must close its table cell and the next cell in the row
must be empty - anything else reads as a revised template and stops the
fill, even on --check with no value to type.
"""
import argparse
import html
import json
import re
import sys
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import amendments
import owner_names
import street_format
from owner_names import company_name   # one definition of a company owner for every document

P_RE = re.compile(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", re.S)
# text nodes and the layout elements that separate them visually
SEG_RE = re.compile(r"(<w:t(?: [^>]*)?>)(.*?)(</w:t>)|(<w:tab/>|<w:br/>|<w:cr/>)", re.S)
# the QLD reflow prints its prefill as "$ 25.00" - tolerate the space
AMOUNT_RE = re.compile(r"\$ ?[\d,]+\.\d{2}")
# a plain amount as the job JSON keys it: "514,700.00", "$514,700", "77"
MONEY_RE = re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d{1,2})?")
# every money key the contract types; each is typed as "$nnn,nnn.nn"
MONEY_KEYS = ("price_excl_gst", "gst_amount", "price_incl_gst", "deposit", "liq_damages",
              "progress_1", "progress_2", "progress_3", "progress_4", "progress_5",
              "progress_6", "progress_total")


def parse_money(s):
    """Decimal from a plain amount, None for anything else (never a guess)."""
    m = MONEY_RE.fullmatch(str(s or "").strip())
    return Decimal(m.group(1).replace(",", "") + (m.group(2) or "")) if m else None


def cents(d, rounding=ROUND_HALF_UP):
    return d.quantize(Decimal("0.01"), rounding=rounding)


def fmt_money(d):
    return f"${cents(d):,.2f}"


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
    """Replace the non-empty span [start, end) of the segments' joined text
    with `text` (the replace_amount path - a $-placeholder swaps in place
    and keeps its own regular face). Deletion applies only to real segments;
    a tab in the middle of a match survives - no HIA anchor spans one."""
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


def _rebuild(p_xml, segs):
    """Write changed segment texts back into their <w:t> nodes."""
    for s in sorted((s for s in segs if not s["virtual"] and s["text"] != s["orig"]),
                    key=lambda s: -s["span"][0]):
        open_tag = s["open"]
        # an aligned amount carries spaces inside it ("$  49,990.91")
        if (s["text"] != s["text"].strip() or "  " in s["text"]) and "xml:space" not in open_tag:
            open_tag = open_tag[:-1] + ' xml:space="preserve">'
        a, b = s["span"]
        p_xml = p_xml[:a] + open_tag + xml_escape(s["text"]) + "</w:t>" + p_xml[b:]
    return p_xml


def insert_value_run(p_xml, segs, offset, value, tab=False, rpr=None):
    """Insert the typed value as its OWN run right after the label text at
    `offset`, in the label's face minus bold/italic/underline (STRIP_RE) -
    the way the completed contracts key regular-weight values beside bold
    printed labels - or in `rpr` when given. Mode "tab" leads with a tab
    (the line's value column) instead of the two-space gap."""
    pos, seg, off_in = 0, None, 0
    for s in segs:
        ln = len(s["text"])
        if not s["virtual"] and pos < offset <= pos + ln:
            seg, off_in = s, offset - pos
            break
        pos += ln
    if seg is None:
        return p_xml, False
    t_start, t_end = seg["span"]
    run = next((m for m in RUN_RE.finditer(p_xml)
                if m.start() < t_start and m.end() > t_end), None)
    if run is None:
        return p_xml, False
    rpr_m = RPR_RE.search(run.group(0))
    if rpr is None:
        rpr = STRIP_RE.sub("", rpr_m.group(0)) if rpr_m else ""
    lead = "<w:tab/>" if tab else ""
    text = value if tab else f"  {value}"
    new_run = f'<w:r>{rpr}{lead}<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>'
    if off_in == len(seg["text"]) and not T_RE.search(
            run.group(0), t_end - run.start()):
        # the label ends this run: the value run goes right after it
        return p_xml[:run.end()] + new_run + p_xml[run.end():], True
    # otherwise split the label's text node and re-open its run around the
    # inserted value, keeping the original face on the tail
    head = xml_escape(seg["text"][:off_in])
    tail = xml_escape(seg["text"][off_in:])
    orig_rpr = rpr_m.group(0) if rpr_m else ""
    repl = (f'<w:t xml:space="preserve">{head}</w:t></w:r>{new_run}'
            f'<w:r>{orig_rpr}<w:t xml:space="preserve">{tail}</w:t>')
    return p_xml[:t_start] + repl + p_xml[t_end:], True


def fill_para(p_xml, label, value, mode, occ=1):
    """Type value beside the occ-th occurrence of label in this paragraph."""
    segs = parse_segments(p_xml)
    concat = "".join(s["text"] for s in segs)
    if mode in ("after", "tab"):
        hits = list(label_regex(label).finditer(concat))
        if len(hits) < occ:
            return p_xml, False
        return insert_value_run(p_xml, segs, hits[occ - 1].end(), value,
                                tab=(mode == "tab"))
    if isinstance(mode, tuple) and mode[0] == "tab_at":
        # a value that must line up with a name typeset elsewhere on the
        # page: its own tab stop at that name's x (twips from the margin) and
        # that name's size (half-points) in the paragraph's own font. A
        # paragraph that already sets tab stops is a revised template
        _, pos, size = mode
        hits = list(label_regex(label).finditer(concat))
        ppr = re.search(r"<w:pPr>(.*?)</w:pPr>", p_xml, re.S)
        # w:tabs goes first in the pPr, so nothing the schema orders ahead
        # of it may be there already (the paragraph mark's own rPr aside)
        if len(hits) < occ or not ppr or re.search(
                r"<w:(?:pStyle|keepNext|keepLines|pageBreakBefore|framePr|widowControl|numPr"
                r"|suppressLineNumbers|pBdr|shd|tabs)\b", ppr.group(1).split("<w:rPr>")[0]):
            return p_xml, False
        p_xml, ok = insert_value_run(p_xml, segs, hits[occ - 1].end(), value, tab=True,
                                     rpr=f'<w:rPr><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>')
        return p_xml.replace("<w:pPr>", f'<w:pPr><w:tabs><w:tab w:val="left" w:pos="{pos}"/></w:tabs>',
                             1), ok
    if isinstance(mode, tuple) and mode[0] == "tab_rpr":
        # mode "tab" in a given face - a company's name sized to its line
        hits = list(label_regex(label).finditer(concat))
        if len(hits) < occ:
            return p_xml, False
        return insert_value_run(p_xml, segs, hits[occ - 1].end(), value, tab=True, rpr=mode[1])
    if isinstance(mode, tuple) and mode[0] == "replace_days":
        # QLD item 13: the printed number of days, which must still be the template's
        m = QLD_PERIOD_RE.search(concat)
        if not m or m.group(1) != mode[1]:
            return p_xml, False
        _splice(segs, m.start(1), m.end(1), value)
        return _rebuild(p_xml, segs), True
    if isinstance(mode, tuple) and mode[0] == "replace_tail":
        # NSW Special Conditions clause 1: the printed validity wording, which
        # must still read as the template prints it, swapped for the request's
        hits = list(re.finditer(r"\s+".join(re.escape(w) for w in mode[1].split()), concat))
        if len(hits) != 1:
            return p_xml, False
        _splice(segs, hits[0].start(), hits[0].end(), value)
        return _rebuild(p_xml, segs), True
    if mode == "replace_amount":
        m = AMOUNT_RE.search(concat)
        if not m:
            return p_xml, False
        _splice(segs, m.start(), m.end(), value)
        return _rebuild(p_xml, segs), True
    if isinstance(mode, tuple) and mode[0] == "replace_value":
        # an approved schedule change (CD-10): the rate right after its label,
        # which must still read the old value
        hits = list(label_regex(label).finditer(concat))
        m = RATE_RE.search(concat, hits[0].end()) if hits else None
        if not m or plain_rate(m.group(0)) != mode[1]:
            return p_xml, False
        _splice(segs, m.start(), m.end(), value)
        return _rebuild(p_xml, segs), True
    if mode == "dollar_cell":
        # a progress schedule AMOUNT cell holds a lone "$" run, condensed by
        # 0.5 pt (w:spacing -10); the figure replaces it at normal spacing
        if concat.strip() != "$":
            return p_xml, False
        i = concat.index("$")
        _splice(segs, i, i + 1, value)
        return re.sub(r'<w:spacing w:val="-?\d+"/>', "", _rebuild(p_xml, segs)), True
    return p_xml, False


T_RE = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
TC_OPEN_RE = re.compile(r"<w:tc\b")
P_ANY_RE = re.compile(r"<w:p\b[^>]*/>|<w:p\b[^>]*>")  # self-closed first
LABEL_RPR_RE = re.compile(r"<w:r\b[^>]*>\s*(<w:rPr>.*?</w:rPr>)", re.S)
RUN_RE = re.compile(r"<w:r\b[^>]*>.*?</w:r>", re.S)
RPR_RE = re.compile(r"<w:rPr>.*?</w:rPr>", re.S)
# typed values render regular: no bold, italic or underline off the label
# (review sheet items 2/7/10/14 - the completed contracts key values in
# regular weight beside their bold printed labels)
STRIP_RE = re.compile(r"<w:(?:b|bCs|i|iCs|u)(?: [^>]*)?/>")


def cell_value_run(label_p_xml, value):
    """A run for the empty value cell: the label run's own face minus
    bold/italic/underline, the way a typed entry renders beside a printed
    label. A newline in the value is a line break (the QLD cover SITE)."""
    m = LABEL_RPR_RE.search(label_p_xml)
    rpr = STRIP_RE.sub("", m.group(1)) if m else ""
    text = '</w:t><w:br/><w:t xml:space="preserve">'.join(xml_escape(v) for v in value.split("\n"))
    return f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'


def cell_slot(xml, para_end):
    """((start, end, before, after), None) locating the value slot in the
    table cell after the label's cell, or (None, reason).

    The slot replaces xml[start:end] with before + value run + after. The
    label's paragraph must close its cell, the next cell must start in the
    same row, and it must hold no visible text - anything else reads as a
    revised template and stops the fill like any other missing anchor."""
    if not xml[para_end:para_end + 40].lstrip().startswith("</w:tc>"):
        return None, "label paragraph does not close a table cell"
    tc = TC_OPEN_RE.search(xml, para_end)
    row_end = xml.find("</w:tr>", para_end)
    if not tc or (0 <= row_end < tc.start()):
        return None, "no value cell follows in the same table row"
    cell_start = tc.start()
    cell = xml[cell_start:xml.find("</w:tc>", cell_start)]
    if "".join(m.group(1) for m in T_RE.finditer(cell)).strip():
        return None, "the value cell beside the label is not empty"
    pm = P_ANY_RE.search(cell)
    if not pm:
        return None, "the value cell has no paragraph"
    if pm.group(0).endswith("/>"):   # <w:p .../> -> open it around the run
        a = cell_start + pm.start()
        return (a, a + len(pm.group(0)), pm.group(0)[:-2] + ">", "</w:p>"), None
    close = cell.find("</w:p>", pm.end())
    if close < 0:
        return None, "the value cell's paragraph does not close"
    a = cell_start + close
    return (a, a, "", ""), None


CENTRED_RE = re.compile(r'<w:vAlign w:val="center"/>')


def top_aligned(xml, para_start, slot_start):
    """Edits that turn the label cell and the value cell from vertically
    centred to top: a value on two lines (the QLD cover SITE) otherwise leaves
    the label floating between them, where the team's form has it level with
    the first line. A cell that is not centred is left as it is."""
    label_cell = max(m.start() for m in re.finditer(r"<w:tc[ >]", xml[:para_start]))
    value_cell = TC_OPEN_RE.search(xml, para_start).start()
    edits = []
    for lo, hi in ((label_cell, para_start), (value_cell, slot_start)):
        m = CENTRED_RE.search(xml, lo, hi)
        if m:
            edits.append((m.start(), m.end(), '<w:vAlign w:val="top"/>'))
    return edits


# Anchor sets. Field tuples are (json key, printed label, mode[, occurrence]).
# Scope None = whole document, first occurrence.
# Both builds box each cover label into a narrow table cell with a wide
# empty value cell beside it - QLD since the team's v2, NSW since the v1.1
# TABLES interim (the review's item 1: values wrapped vertically in the old
# 950tw-wide label paragraphs and pushed the cover's HIA notice off-page).
COVER = [
    ("owners",   "OWNERS:", "cell"),
    ("job_no",   "JOB:",    "cell"),
    ("lot_no",   "LOT:",    "cell"),
    ("site_hia", "SITE:",   "cell"),
]
REGIONS = {
    # The team's Word build of the April 2021 NSW contract plus the v1.1
    # TABLES interim (3 Sep 2026, review sheet fixes): the cover, item 3
    # owner rows (SUBURB|STATE|POSTCODE split into label+value cells) and
    # the land's LOT/DP NO/STREET ADDRESS: block are label-cell +
    # value-cell tables; MOBILE and the land's SUBURB/POSTCODE stay inline
    # (their lines absorb a value without wrapping); the deed and
    # guarantors are plain paragraphs. Scopes are picked from strings
    # unique-first in document order (the TOC repeats most headings).
    "NSW": {
        "groups": [
            (None, COVER),
            # item 3 Owners - between item 2(b)'s closing note and the
            # builder block's prefilled company name
            (("(The deposit must not exceed", "TRANSPIRE CONSTRUCTIONS"), [
                ("_sch1_owner",    "NAME",     "cell"),
                ("owner_address",  "ADDRESS",  "cell"),
                ("owner_suburb",   "SUBURB",   "cell"),
                ("owner_state",    "STATE",    "cell"),
                ("owner_postcode", "POSTCODE", "cell"),
                ("owner_mobile",   "MOBILE",   "after"),
                ("owner_email",    "EMAIL",    "cell"),
            ]),
            # item 5 The Land (STATE is prefilled NSW in the template)
            (("THE LAND IS:", "must reach the stage"), [
                ("lot_no",        "LOT",             "cell"),
                ("dp_no",         "DP NO",           "cell"),
                ("land_street",   "STREET ADDRESS:", "cell"),
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
            # e-signing note. Names type at the NAME lines' 2233 tab stop
            # (v1.1) - the x the SIGNATURE rules start at, where the
            # manual contracts key them (review item 13)
            (("has read and understood this contract", "/na/"), [
                ("_sch1_owner", "NAME", "tab"),
            ]),
            (("/na/", "electronically signed"), [
                ("builders_rep", "NAME", "tab"),
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
            # Attachment A checklist acknowledgement (owners' printed
            # names). The boxes are label|value tables: the name lands in
            # the value cell beside "Name (print):" - typed into the label
            # cell it stretched the box and hid the Date row (review items
            # 15-16). Boxes 3 and 4 stay blank: box N belongs to owner N.
            (("Acknowledgement of owners", "Consumer"), [
                ("owner_1", "Name (print):", "cell", 1),
                ("owner_2", "Name (print):", "cell", 2),
            ]),
        ],
        # item 2: the template ships $000,000.00-style placeholders, filled
        # from the contract price (CD-5.4, issue #62) or keyed DataBuild figures
        "amounts": [
            ("price_excl_gst", "PRICE EXCLUDING GST:"),
            ("gst_amount",     "GST ON THE ABOVE AMOUNT:"),
            ("price_incl_gst", "THE CONTRACT PRICE IS:"),
            ("deposit",        "THE DEPOSIT IS:"),
        ],
        "liq": ("liq_damages", "per working day"),
        # Progress Payments Schedule (CD-5.6): six stage rows and a TOTAL row,
        # each with a lone "$" AMOUNT cell. The percentages are the template's
        # own and are checked against these before anything is typed.
        "progress": {
            "scope": ("Progress Payments Schedule",
                      "The total amount must be the same as the contract price"),
            "stages": [10, 10, 25, 25, 20, 10],
        },
        # approved amendments (CD-10, issue #61): the schedule values one may
        # change, by the label they follow, and the style of the general
        # conditions' "Clause N. Title" headings (the TOC repeats each title
        # in another style, so the style is what picks the heading)
        "schedule": {"interest_rate": "Interest on late payments is"},
        "clause_style": "Heading1",
    },
    # The team's v2 Word build of the QC2 October 2020 contract (1 Sep 2026,
    # issue #8). v2 rebuilt the wrap-prone label areas as real tables: the
    # cover fields, item 3 owners, item 7 guarantors and the deed's BUILDER
    # IS / OWNER IS lines are a narrow label cell + wide empty value cell,
    # filled with mode "cell" - the value lands in the empty cell, the way
    # the build's own ABN/ACN prefills sit beside their labels. Everything
    # else keeps the v1 inline layout (the land, the Consumer Building
    # Guide, the deed's guarantor lines and the signature names still share
    # label paragraphs, e.g. "SUBURB<tab>STATE<tab>POSTCODE") and a value
    # types inline after its label. Scopes are picked from strings
    # unique-first in document order (the TOC repeats the schedule
    # headings, so heading-only scopes would land there).
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
                ("_sch1_owner",    "NAME",     "cell"),
                ("owner_address",  "ADDRESS",  "cell"),
                ("owner_suburb",   "SUBURB",   "cell"),
                ("owner_state",    "STATE",    "cell"),
                ("owner_postcode", "POSTCODE", "cell"),
                ("owner_mobile",   "MOBILE",   "cell"),
                ("owner_email",    "EMAIL",    "cell"),
            ]),
            # item 7 Owner's guarantors - sourced names only, else left blank
            (("Owner's guarantors (Clause 32)", "Default interest rate"), [
                ("guarantor_name",     "NAME",     "cell"),
                ("guarantor_address",  "ADDRESS",  "cell"),
                ("guarantor_suburb",   "SUBURB",   "cell"),
                ("guarantor_state",    "STATE",    "cell"),
                ("guarantor_postcode", "POSTCODE", "cell"),
            ]),
            # item 11 The land - LOT/SP-RP/STREET are value cells since the
            # v2.1 LAND TABLES interim (3 Sep 2026: v2 left this block in the
            # old narrow label column, the one residual page-spill area);
            # the SUBURB row below it stays inline - it absorbs its three
            # values on the line without wrapping
            (("The land (Clause 6)", "Matters affecting the site"), [
                ("lot_no",        "LOT",             "cell"),
                ("sp_rp",         "SP/RP",           "cell"),
                ("land_street",   "STREET ADDRESS:", "cell"),
                ("land_suburb",   "SUBURB",          "after"),
                ("land_state",    "STATE",           "after"),
                ("land_postcode", "POSTCODE",        "after"),
            ]),
            # Signatures: the owner NAME line only (occurrence 2 is the
            # witness, left for a person) - the builder's line ships
            # prefilled with Michael CRONK in this build, in a two-column
            # section: a 1206 tw first column + 497 tw gap, then Heading 5's
            # 516 tw indent puts the name 2219 tw in from the margin, at 12 pt.
            # The owner's name types at a tab stop there, at that size, so the
            # two names line up (27 Oct 2026 review; typed two spaces after
            # the label at 10 pt it sat well left of the builder's)
            (("has read and understood this contract", "Michael CRONK"), [
                ("_sch1_owner", "NAME", ("tab_at", 2219, 24), 1),
            ]),
            # Deed of guarantee and indemnity - completed only when the job
            # has a sourced guarantor; the deed date is never filled
            (("BUILDER IS", "Background"), [
                ("_deed_builder",      "BUILDER IS",     "cell"),
                ("_deed_owner",        "OWNER IS",       "cell"),
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
        # label. Worked from the contract price, figures a person gives
        # winning (CD-5.4, 27 Oct 2026 review). No deposit item on QC2: the
        # deposit is Part B's first row.
        "amounts": [
            ("price_excl_gst", "PRICE EXCLUDING GST:",     1),
            ("gst_amount",     "GST ON THE ABOVE AMOUNT:", 2),
            ("price_incl_gst", "THE CONTRACT PRICE IS:",   3),
        ],
        # Schedule 2 Part B (CD-5.6, issue #73), the part the team completes:
        # six rows and a TOTAL row, each a printed "n.00%" cell then a
        # "$ 0.00" amount cell. Same source as item 2; the printed
        # percentages are checked before anything is typed, and the amounts
        # are worked from these same percentages.
        "part_b": {
            "scope": ("Part B can be used where the parties agree",
                      "The total must equal the contract price"),
            "rows": [("deposit", "DEPOSIT", 5), ("progress_1", "BASE", 15),
                     ("progress_2", "FRAME", 20), ("progress_3", "ENCLOSED", 25),
                     ("progress_4", "FIXING", 20),
                     ("progress_5", "PRACTICAL COMPLETION", 15)],
        },
        "liq": ("liq_damages", "per day"),
        # approved amendments (CD-10): the interest rate only; striking a QC2
        # clause is not set up (its clause headings are not verified yet)
        "schedule": {"interest_rate": "Rate on overdue payments"},   # prints "payments:15%"
    },
}

# an interest rate as the schedule prints it: "15%", "12.5 %"
RATE_RE = re.compile(r"\d+(?:\.\d+)?\s?%")


def plain_rate(s):
    return re.sub(r"\s+", "", str(s or ""))


def _strike_rpr(inner):
    """<w:strike/> into an rPr's content at its schema place: after rStyle,
    rFonts, b, bCs, i, iCs, caps, smallCaps; before everything else."""
    if re.search(r'<w:strike(?: w:val="(?:1|true|on)")?/>', inner):
        return inner
    inner = re.sub(r'<w:strike w:val="[^"]*"/>', "", inner)
    head = list(re.finditer(r"<w:(?:rStyle|rFonts|b|bCs|i|iCs|caps|smallCaps)\b[^>]*/>", inner))
    at = head[-1].end() if head else 0
    return inner[:at] + "<w:strike/>" + inner[at:]


def strike_range(seg):
    """Strike through every run that prints text in an XML range, and every
    paragraph mark (the automatic 14.1 / (a) numbers render in the mark's
    format). Text, numbering and section breaks are untouched. (new xml, runs)"""
    runs = 0

    def run(m):
        nonlocal runs
        r = m.group(0)
        if not re.search(r"<w:t[ >]", r):
            return r
        runs += 1
        rp = re.search(r"<w:rPr>(.*?)</w:rPr>", r, re.S)
        if rp:
            return r[:rp.start(1)] + _strike_rpr(rp.group(1)) + r[rp.end(1):]
        op = re.match(r"<w:r\b[^>]*>", r)
        return r[:op.end()] + "<w:rPr><w:strike/></w:rPr>" + r[op.end():]

    def mark(m):
        inner = m.group(1)
        rp = re.search(r"<w:rPr>(.*?)</w:rPr>", inner, re.S)
        if rp:
            inner = inner[:rp.start(1)] + _strike_rpr(rp.group(1)) + inner[rp.end(1):]
        else:
            cut = min([i for i in (inner.find("<w:sectPr"), inner.find("<w:pPrChange")) if i >= 0],
                      default=len(inner))
            inner = inner[:cut] + "<w:rPr><w:strike/></w:rPr>" + inner[cut:]
        return f"<w:pPr>{inner}</w:pPr>"

    seg = re.sub(r"<w:r\b[^>]*>.*?</w:r>", run, seg, flags=re.S)
    seg = re.sub(r"(<w:p\b[^>]*?(?<!/)>)(?!<w:pPr>)", r"\1<w:pPr></w:pPr>", seg)
    seg = re.sub(r"<w:pPr>(.*?)</w:pPr>", mark, seg, flags=re.S)
    return seg, runs


def strike_read_back(old, new):
    """The struck range reads the same, keeps its section breaks, and every
    run that prints text is struck."""
    def text(s):
        return "".join(m.group(1) for m in re.finditer(r"<w:t(?: [^>]*)?>(.*?)</w:t>", s, re.S))
    printing = [r for r in re.findall(r"<w:r\b[^>]*>.*?</w:r>", new, re.S) if re.search(r"<w:t[ >]", r)]
    return (text(old) == text(new) and old.count("<w:sectPr") == new.count("<w:sectPr") and printing
            and all(re.search(r'<w:strike(?: w:val="(?:1|true|on)")?/>', r) for r in printing))


def derive_values(values, region):
    """Convenience keys derived from sourced ones - never from thin air."""
    # Every purchaser's mobile and email rides on the contract - DocuSign
    # needs them all (review item 8; the executed multi-owner contracts key
    # both, ";"-separated). A second owner's contact keys join the first.
    for key in ("owner_mobile", "owner_email"):
        extra = str(values.get(key.replace("owner_", "owner_2_", 1)) or "").strip()
        if extra:
            main = str(values.get(key) or "").strip()
            values[key] = f"{main}; {extra}" if main else extra
    # Schedule 1 / signature NAME: every executed multi-owner job keys the
    # joined names. A company or trust owner keys its full name WITH the ACN
    # (feedback sheet 5 Nov 2026 rows 9, 12, 13: "ACN must be included with
    # company name"; until then the entity went in without it)
    company = company_name(values)
    if not values.get("_sch1_owner"):
        two = (values.get("owner_2") or "").strip()
        values["_sch1_owner"] = (values.get("owners") if two or company
                                 else values.get("owner_1", "")) or ""
    if company:
        values["_company"] = company
        # "<guarantor> on behalf of <company> ACN: ..." under the company's
        # name where the owner signs (rows 8, 12, 16)
        signer = owner_names.signer_line(values, company)
        if signer:
            values["_signer_line"] = signer
    # NSW job JSONs written before the team build carried "SUBURB POSTCODE"
    # as one value; split it rather than forcing every JSON to be re-authored
    if region == "NSW" and not values.get("land_suburb") and values.get("land_suburb_pc"):
        parts = str(values["land_suburb_pc"]).rsplit(" ", 1)
        values["land_suburb"] = parts[0]
        if len(parts) == 2 and parts[1].isdigit() and not values.get("land_postcode"):
            values["land_postcode"] = parts[1]
    # The land's STREET ADDRESS and the cover SITE with the job's estate after
    # the street, "Street, (Estate)" (street_format.with_estate): QLD item 11
    # since the 27-28 Oct 2026 review of job 26059 (the team's own copy of
    # 26059 and the latest SEQ estate contracts); NSW item 5 since the job
    # 26061 feedback sheet (9 Nov 2026 rows 9-10) - 26042 and 26057, the latest
    # NSW estate contracts, read "(60) Sample Road, (Sample Estate)". The
    # Oct fix pinned NSW as untouched, which is how 26061 lost its estate.
    street = bare_street = str(values.get("land_street") or "").strip()
    estate = street_format.estate_name(values.get("estate"))
    if street and estate:
        street = street_format.with_estate(street, estate)
        values["land_street"] = street
    if region == "QLD":
        # the cover: that street with SUBURB STATE POSTCODE on the line below,
        # as every executed SEQ contract shows (one form field feeds both)
        place = " ".join(" ".join(str(values.get(k) or "") for k in ("land_suburb", "land_state",
                                                                     "land_postcode")).split())
        if street and place:
            values["site_hia"] = f"{street}\n{place}"
    elif region == "NSW":
        # the cover SITE on one line, "<street>, SUBURB NSW <postcode>", the
        # estate after the street - every NSW cover the team typed (26042,
        # 26056, 26057, the team's 26061). The run had written "26 Sample
        # Street, Sampleville": no estate, no postcode, suburb not in capitals.
        suburb = " ".join(str(values.get("land_suburb") or "").split()).upper()
        postcode = str(values.get("land_postcode") or "").strip()
        if street and suburb and postcode:
            values["site_hia"] = f"{street}, {suburb} NSW {postcode}"
        elif values.get("site_hia") and estate:
            given = bare_street or str(values.get("street") or "").strip()
            values["site_hia"] = street_format.site_with_estate(values["site_hia"], given, estate)
    # the deed is only in play when the job actually has a guarantor. The
    # builder reads as the team types it ("Transpire Constructions Pty Ltd",
    # CD-1.4; row 13) and the owner as item 3 does, ACN included
    if (values.get("guarantor_name") or "").strip():
        values.setdefault("_deed_builder", "Transpire Constructions Pty Ltd")
        values.setdefault("_deed_owner", values["_sch1_owner"])
        # The land contract's guarantee page names the guarantor and often
        # leaves the address line blank; the team then types the buyer's own
        # address (26039: the director's, the company's registered one).
        # Used only with a flag for the person to confirm.
        if company and not any(str(values.get(f"guarantor_{k}") or "").strip()
                               for k in ("address", "suburb", "postcode")):
            for k in ("address", "suburb", "state", "postcode"):
                values[f"guarantor_{k}"] = str(values.get(f"owner_{k}") or "").strip()
            values["_guarantor_address_from_owner"] = True
    return values


# ---------------------------------------------------------------------------
# Feedback sheet of 5 Nov 2026 (jobs 26060 and 26011 NSW, 26039 QLD): a company owner's name with its ACN, sized to its slot and
# signed "on behalf of"; amounts in one column lined up on their digits; the
# QLD building period from storeys and house size; the NSW price-validity
# clause from the request.

# Amounts that print in one column, each group lined up on its digits: the
# printed placeholder is left-aligned, so "$49,990.91" under "$499,909.09"
# started one digit to the left (row 5). The team pads after the "$"
# ("$  49,990.91"). In Arial - every amount here prints in Arial - a digit is
# exactly two spaces wide and a comma one, so the pad lines the digits up.
ALIGN_GROUPS = {
    "NSW": [("price_excl_gst", "gst_amount", "price_incl_gst"),
            ("progress_1", "progress_2", "progress_3", "progress_4", "progress_5", "progress_6",
             "progress_total")],
    "QLD": [("price_excl_gst", "gst_amount", "price_incl_gst"),
            ("deposit", "progress_1", "progress_2", "progress_3", "progress_4", "progress_5",
             "progress_total")],
}
TYPED_AMOUNT_RE = re.compile(r"\$[\d,]+\.\d{2}")


def aligned_amounts(values, region):
    """{key: "$  49,990.91"} for every amount that needs a pad to line up with
    the widest amount of its column."""
    out = {}
    for group in ALIGN_GROUPS.get(region, []):
        vals = {k: str(values.get(k) or "").strip() for k in group}
        vals = {k: v for k, v in vals.items() if TYPED_AMOUNT_RE.fullmatch(v)}
        if len(vals) < 2:
            continue
        digits = {k: sum(c.isdigit() for c in v) for k, v in vals.items()}
        commas = {k: v.count(",") for k, v in vals.items()}
        dmax, cmax = max(digits.values()), max(commas.values())
        for k, v in vals.items():
            pad = 2 * (dmax - digits[k]) + (cmax - commas[k])
            if pad:
                out[k] = "$" + " " * pad + v[1:]
    return out


def run_face(rpr, default_font="Arial", default_size=20):
    """(font family, size in half-points, bold) of a run's rPr."""
    f = re.search(r'<w:rFonts\b[^>]*w:ascii="([^"]+)"', rpr or "")
    s = re.search(r'<w:sz w:val="(\d+)"', rpr or "")
    bold = bool(re.search(r'<w:b(?: w:val="(?:1|true|on)")?/>', rpr or ""))
    return (f.group(1) if f else default_font), (int(s.group(1)) if s else default_size), bold


def with_size(rpr, half_points):
    """The rPr with its size (and complex-script size) set to half_points."""
    rpr = rpr or "<w:rPr></w:rPr>"
    rpr = re.sub(r'<w:sz(?:Cs)? w:val="\d+"/>', "", rpr)
    return rpr.replace("</w:rPr>", f'<w:sz w:val="{half_points}"/><w:szCs w:val="{half_points}"/></w:rPr>')


def text_width_at(xml, pos):
    """Twips of text width governing pos: page width less margins, from the
    first section break at or after it."""
    m = re.search(r"<w:sectPr\b.*?</w:sectPr>", xml[pos:], re.S)
    if not m:
        return None
    s = m.group(0)
    w = re.search(r'<w:pgSz w:w="(\d+)"', s)
    left = re.search(r'<w:pgMar\b[^>]*w:left="(\d+)"', s)
    right = re.search(r'<w:pgMar\b[^>]*w:right="(\d+)"', s)
    if not (w and left and right):
        return None
    return int(w.group(1)) - int(left.group(1)) - int(right.group(1))


CELL_MARGINS = 230   # twips: Word's default 0.08" left + right cell padding


def cell_width_at(xml, pos):
    """Twips of the table cell holding pos, less its padding, or None."""
    tc = max((m.start() for m in re.finditer(r"<w:tc[ >]", xml[:pos])), default=None)
    if tc is None:
        return None
    m = re.search(r'<w:tcW w:w="(\d+)" w:type="dxa"', xml[tc:tc + 600])
    return int(m.group(1)) - CELL_MARGINS if m else None


def fitted(rpr, text, width, notes, where, floor=14, cap=None):
    """rPr sized so text prints on one line within width twips (font_fit)."""
    import font_fit
    font, size, bold = run_face(rpr)
    size = min(size, cap) if cap else size
    hp, fits, exact = font_fit.fit_size(text, font, size, width, bold, floor)
    notes.append(f"{where}: {hp / 2:g} pt {font}{' bold' if bold else ''} in {width / 20:.0f} pt"
                 + ("" if fits else " - still wraps at the smallest size; check the line")
                 + ("" if exact else " (width estimated - font file not found)"))
    return with_size(rpr, hp)


# NSW Special Conditions clause 1 (feedback sheet 5 Nov 2026 row 6): the
# printed "valid for six (6) months after title registration" becomes the date
# the request fixes the price until, "up to and including 30th March 2027"
VALIDITY_TAIL = "for six (6) months after title registration of the subject land."
VALIDITY_CLAUSE = "will be fixed and valid"
VALIDITY_MENTION_RE = re.compile(r"\b(?:price\s+validity|fixed\s+until|valid(?:ity)?\s+until|"
                                 r"locked\s+in\s+until|fixed\s+price\s+until)\b", re.I)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def validity_until(values, job_path):
    """(clause words, how, refusal) for the NSW validity clause, from the job's
    `price_valid_until` (an ISO date a person or the run settled) and
    `price_validity_line` (the request's line, verbatim). The line must be in the
    saved request text, and the date must fall in the month the line names (a
    quarter's last month for "Q1 2027"). Nothing given: (None, None, None)."""
    import datetime
    until = str(values.get("price_valid_until") or "").strip()
    line = amendments.norm(values.get("price_validity_line"))
    if not until and not line:
        return None, None, None
    if not until or not line:
        return None, None, "needs both price_valid_until (a date) and price_validity_line (the request's line)"
    try:
        d = datetime.date.fromisoformat(until)
    except ValueError:
        return None, None, f"price_valid_until {until!r} is not a date like 2027-03-31"
    text = amendments.request_text(job_path)
    if text is None or line.lower() not in text.lower():
        return None, None, f"the line {line!r} is not in the request text saved beside the job JSON"
    q = re.search(r"\bQ([1-4])\s*'?\s*(\d{4}|\d{2})\b", line, re.I)
    m = re.search(r"\b(" + "|".join(MONTHS) + r"|" + "|".join(x[:3] for x in MONTHS) + r")\w*\.?\s+(\d{4})\b",
                  line, re.I)
    if q:
        year = int(q.group(2)) + (2000 if len(q.group(2)) == 2 else 0)
        want = (year, int(q.group(1)) * 3)
    elif m:
        want = (int(m.group(2)), [x[:3].lower() for x in MONTHS].index(m.group(1)[:3].lower()) + 1)
    else:
        return None, None, f"the line {line!r} names no month or quarter to check {until} against"
    if (d.year, d.month) != want:
        return None, None, (f"{until} is not in {MONTHS[want[1] - 1]} {want[0]}, which the line "
                            f"{line!r} names")
    words = f"up to and including {ordinal(d.day)} {MONTHS[d.month - 1]} {d.year}."
    return words, f"{line!r} -> {words}", None


# QLD Schedule 1 item 13, from the team (feedback sheet 5 Nov 2026 row 11):
# single storey 210 days; double storey under 300 m2 240 days, over 300 m2 260
QLD_PERIOD_RE = re.compile(r"practical completion within\s+(\d+)\s+days after commencement")


def building_period(values):
    """(days, how) for QLD item 13, or (None, why) when the job does not say."""
    up = values.get("upgrades") or {}
    storeys = values.get("storeys", up.get("storeys"))
    storeys = int(storeys) if str(storeys).strip() in ("1", "2") else storeys
    size = re.search(r"\d+(?:\.\d+)?", str(values.get("house_size") or "").replace(",", ""))
    size = float(size.group(0)) if size else None
    if storeys == 1:
        return 210, "single storey"
    if storeys != 2:
        return None, "storeys not stated in the job JSON (upgrades.storeys)"
    if size is None:
        return None, "double storey but no house size yet (the plans give it) - 240 under 300 m2, 260 over"
    if size == 300:
        return None, "double storey of exactly 300 m2 - the rule says under / over 300; a person picks"
    return (240, f"double storey, {size:g} m2 (under 300)") if size < 300 else \
           (260, f"double storey, {size:g} m2 (over 300)")


def contract_figures(values, region):
    """Item 2 and the progress schedule from the contract price (CD-5.4 / CD-5.6,
    issue #62, NSW; QLD's item 2 and Part B go to part_b_figures). Returns
    (report lines, flags) and sets the money keys a person has not keyed.

    The executed NSW contracts (26045, 26040) follow one convention, applied
    here to the request's GST-inclusive price (the price the inclusions carry):
    GST = price / 11 to the cent, price excluding GST = price - GST, deposit
    10%, each stage = its % x price to the cent. The deposit and stage 1 round
    DOWN so they never pass the 10% cap; the last stage takes the rounding
    balance so the schedule always totals the price. A DataBuild figure a
    person keys into the job JSON always wins, and any difference from the
    calculation is flagged. A deposit_request (an amount or "n%") lower than
    10% goes into item 2(b) with a flag; a higher one is refused. Every keyed
    amount, in every region, types as "$nnn,nnn.nn" (a figure keyed without
    its $ used to print bare)."""
    lines, flags = [], []
    for key in MONEY_KEYS:
        raw = str(values.get(key) or "").strip()
        if raw:
            d = parse_money(raw)
            if d is None:
                flags.append(f"{key} {raw!r} is not a plain amount - typed as keyed; check it")
            else:
                values[key] = fmt_money(d)
    if REGIONS[region].get("part_b"):
        return part_b_figures(values, region, lines, flags)
    prog = REGIONS[region].get("progress")
    if not prog:
        return lines, flags

    raw_price = str(values.get("price") or "").strip()
    req = parse_money(raw_price)
    keyed_price = parse_money(values.get("price_incl_gst"))
    base = keyed_price if keyed_price is not None else req
    if base is None or base <= 0:
        flags.append(f"contract price {raw_price!r} is not a plain amount" if raw_price
                     else "no contract price in the job JSON")
        flags[-1] += " - item 2 and the progress schedule are left blank for a person"
        return lines, flags
    if keyed_price is not None and req is not None and keyed_price != req:
        flags.append(f"the keyed DataBuild contract price {fmt_money(keyed_price)} differs from "
                     f"the request price {fmt_money(req)} - the DataBuild figure is used")

    gst = cents(base / 11)
    cap = cents(base / 10, ROUND_DOWN)
    deposit = cap
    asked = str(values.get("deposit_request") or "").strip()
    if asked:
        try:
            d = (cents(base * Decimal(asked[:-1].strip()) / 100, ROUND_DOWN)
                 if asked.endswith("%") else parse_money(asked))
        except InvalidOperation:
            d = None
        if d is None:
            flags.append(f"deposit_request {asked!r} not understood - 10% used")
        elif d > cap:
            flags.append(f"the requested deposit {fmt_money(d)} is over the 10% cap "
                         f"({fmt_money(cap)}) - 10% used")
        elif d != cap:
            deposit = d
            flags.append(f"the requested deposit {fmt_money(d)} is below 10%: item 2(b) carries it, "
                         f"but the schedule's stage 1 still reads DEPOSIT 10% ({fmt_money(cap)}) - "
                         "a person adjusts the schedule")
    stages = [cents(base * pct / 100, ROUND_DOWN if n == 0 else ROUND_HALF_UP)
              for n, pct in enumerate(prog["stages"][:-1])]
    stages.append(base - sum(stages))
    calc = {"price_incl_gst": base, "gst_amount": gst, "price_excl_gst": base - gst,
            "deposit": deposit, "progress_total": base}
    calc.update({f"progress_{n}": amt for n, amt in enumerate(stages, 1)})

    src = "the keyed DataBuild price" if keyed_price is not None else "the request price"
    lines += [f"contract figures (CD-5.4, issue #62): from {src} {fmt_money(base)}",
              f"  GST              {fmt_money(base)} / 11 = {base / 11:.4f} -> {fmt_money(gst)} "
              "(to the cent, half up)",
              f"  excl. GST        {fmt_money(base)} - {fmt_money(gst)} = {fmt_money(base - gst)}",
              f"  deposit          10% = {fmt_money(cap)} (rounded down, never over the 10% cap)"
              + (f"; requested {fmt_money(deposit)}" if deposit != cap else "")]
    for n, (pct, amt) in enumerate(zip(prog["stages"], stages), 1):
        how = ("balance: the price less stages 1-5" if n == len(stages)
               else "the deposit stage, rounded down" if n == 1 else "to the cent, half up")
        lines.append(f"  stage {n} {pct:>3}%     {fmt_money(amt):>14}  ({how})")
    lines.append(f"  TOTAL     100%     {fmt_money(sum(stages)):>14}  (= the contract price)")

    for key, amt in calc.items():
        raw = str(values.get(key) or "").strip()
        keyed = parse_money(raw) if raw else None
        if not raw:
            values[key] = fmt_money(amt)
        elif keyed is not None and keyed != amt:
            flags.append(f"{key}: the keyed DataBuild figure {fmt_money(keyed)} is used; the "
                         f"calculation gives {fmt_money(amt)} (difference {fmt_money(abs(keyed - amt))})")
    # the typed figures must still agree with each other
    final = {k: parse_money(values.get(k)) for k in calc}
    if None not in (final["price_excl_gst"], final["gst_amount"], final["price_incl_gst"]) \
            and final["price_excl_gst"] + final["gst_amount"] != final["price_incl_gst"]:
        flags.append("item 2 does not add up: price excluding GST + GST is not the contract price")
    parts = [final[f"progress_{n}"] for n in range(1, len(stages) + 1)]
    if None not in parts and final["price_incl_gst"] is not None and sum(parts) != final["price_incl_gst"]:
        flags.append("the progress stages do not total the contract price")
    return lines, flags


def part_b_figures(values, region, lines, flags):
    """QLD item 2 and Schedule 2 Part B from the contract price (27 Oct 2026
    review of job 26059, reversing issue #73's "nothing is worked out").

    The executed SEQ contracts take one figure, the GST-inclusive contract
    price, and the HIA form the team fills works out the rest from it: price
    excluding GST = price / 1.1, GST the remainder, each Part B row its printed
    % of the price, TOTAL the price. The run does the same from the request's
    `price`, to the cent: GST = price / 11 half up (the same cents as the
    form's, for any price in cents), the deposit rounded down so it never
    passes the 5% the contract allows, practical completion the rounding
    balance so Part B always totals the price. Figures a person gives from
    DataBuild - typed, or a screenshot read back to them first, at any time -
    are typed as given and the rest are worked from their contract price when
    they give one. The checks are warnings: they never stop the fill and never
    change a figure. No usable price and no figures: the cells stay blank,
    flagged."""
    rows = REGIONS[region]["part_b"]["rows"]
    item2 = [("price_excl_gst", "excl. GST"), ("gst_amount", "GST"),
             ("price_incl_gst", "contract price")]
    keys = [k for k, _ in item2] + [k for k, _, _ in rows] + ["progress_total"]
    given = [k for k in keys if str(values.get(k) or "").strip()]
    raw_price = str(values.get("price") or "").strip()
    keyed_price = parse_money(values.get("price_incl_gst"))
    base = keyed_price if keyed_price is not None else parse_money(raw_price)
    if base is not None and base > 0:
        gst = cents(base / 11)
        amts = [cents(base * pct / 100, ROUND_DOWN if key == "deposit" else ROUND_HALF_UP)
                for key, _, pct in rows[:-1]]
        amts.append(base - sum(amts))
        calc = {"price_incl_gst": base, "gst_amount": gst, "price_excl_gst": base - gst,
                "progress_total": base}
        calc.update({key: amt for (key, _, _), amt in zip(rows, amts)})
        src = "the contract price given" if keyed_price is not None else "the request price"
        lines += [f"contract figures (QLD, CD-5.4): from {src} {fmt_money(base)}",
                  f"  GST              {fmt_money(base)} / 11 = {base / 11:.4f} -> {fmt_money(gst)} "
                  "(to the cent, half up)",
                  f"  excl. GST        {fmt_money(base)} - {fmt_money(gst)} = {fmt_money(base - gst)}"]
        for n, ((key, name, pct), amt) in enumerate(zip(rows, amts)):
            how = ("balance: the price less the rows above" if n == len(rows) - 1
                   else "rounded down, never over the 5% cap" if key == "deposit"
                   else "to the cent, half up")
            lines.append(f"  {name[:20]:<20} {pct:>3}% {fmt_money(amt):>14}  ({how})")
        lines.append(f"  {'TOTAL':<20} 100% {fmt_money(base):>14}  (= the contract price)")
        for key, amt in calc.items():
            if key not in given:
                values[key] = fmt_money(amt)
    elif not given:
        flags.append((f"contract price {raw_price!r} is not a plain amount" if raw_price
                      else "no contract price in the job JSON")
                     + " - item 2 and Part B are left blank for a person")
        return lines, flags
    got = {k: parse_money(values.get(k)) for k in keys}   # None: blank, or not an amount
    price = got["price_incl_gst"]
    if any(got[k] is not None for k, _, _ in rows) and not str(values.get("progress_total") or "").strip() \
            and price is not None:
        # the contract's own rule: "The total must equal the contract price stated in item 2"
        values["progress_total"] = fmt_money(price)
        got["progress_total"] = price
    show = lambda k: fmt_money(got[k]) if got[k] is not None else "(blank)"
    if given:
        src = str(values.get("figures_source") or "").strip()
        names = dict(item2 + [(k, n) for k, n, _ in rows] + [("progress_total", "TOTAL")])
        lines += [f"contract figures (QLD): given" + (f" ({src})" if src else "")
                  + ", typed as given: " + ", ".join(names[k] for k in given),
                  "  item 2   " + " | ".join(f"{name} {show(k)}" for k, name in item2),
                  "  Part B   " + " | ".join(f"{name} {pct}% {show(k)}" for k, name, pct in rows)
                  + f" | TOTAL {show('progress_total')}"]

    blank2 = [name for k, name in item2 if got[k] is None]
    if len(blank2) < len(item2) and blank2:
        flags.append(f"item 2 is part-filled: {', '.join(blank2)} left blank")
    if None not in (got["price_excl_gst"], got["gst_amount"], price) \
            and got["price_excl_gst"] + got["gst_amount"] != price:
        flags.append("item 2 does not add up: price excluding GST + GST is not the contract price")
    if got["gst_amount"] is not None and price is not None \
            and abs(got["gst_amount"] - cents(price / 11)) > Decimal("0.01"):
        flags.append(f"the GST {fmt_money(got['gst_amount'])} is not 1/11 of the contract price "
                     f"({fmt_money(cents(price / 11))})")
    req = parse_money(values.get("price"))
    if price is not None and req is not None and price != req:
        flags.append(f"the contract price given, {fmt_money(price)}, differs from the request "
                     f"price {fmt_money(req)}")

    parts = [got[k] for k, _, _ in rows]
    if any(p is not None for p in parts):
        blankb = [name for (k, name, _) in rows if got[k] is None]
        if blankb:
            flags.append(f"Part B is part-filled: {', '.join(blankb)} left blank")
        base = price if price is not None else got["progress_total"]
        if None not in parts:
            for what, amt in (("the TOTAL", got["progress_total"]), ("the contract price", price)):
                if amt is not None and sum(parts) != amt:
                    flags.append(f"Part B's rows add up to {fmt_money(sum(parts))}, not {what} "
                                 f"{fmt_money(amt)}")
        if base is not None:
            cap = cents(base * 5 / 100, ROUND_DOWN)
            over = base >= 20000 and got["deposit"] is not None and got["deposit"] > cap
            if over:
                flags.append(f"the deposit {fmt_money(got['deposit'])} is over 5% of the contract price "
                             f"({fmt_money(cap)}), the most the contract allows for a price of $20,000 "
                             "or more unless the off-site work is over half the price")
            for (k, name, pct), amt in zip(rows, parts):
                near = base * pct / 100
                if amt is not None and abs(amt - near) > 1 and not (k == "deposit" and over):
                    flags.append(f"Part B {name} {fmt_money(amt)} is not {pct}% of the contract price "
                                 f"(about {fmt_money(cents(near))}); the printed {pct}% stays as it is")
    return lines, flags


def signer_line(p_xml, mode, signer, xml, start, notes):
    """The paragraph with "<guarantor> on behalf of <company> ACN: ..." on a line
    of its own under the typed name (feedback sheet 5 Nov 2026 rows 8 and 12,
    as the team writes it on job 26039): a line break inside the paragraph, so
    the owner's name, its signing line and the paragraph's tab stops all hold.
    On a signature NAME line it starts at the name's tab stop; on the Consumer
    Building Guide acknowledgement under NAME(S), in that line's own face."""
    tabbed = mode != "after"
    runs = [m.group(0) for m in RUN_RE.finditer(p_xml)]
    face = RPR_RE.search(runs[-1]) if runs else None
    rpr = face.group(0) if face else ""
    if tabbed:
        stop = mode[1] if isinstance(mode, tuple) and mode[0] == "tab_at" else 2233
        room = (text_width_at(xml, start) or 11000) - stop
        label_face = LABEL_RPR_RE.search(p_xml)
        rpr = fitted(with_size(STRIP_RE.sub("", label_face.group(1)) if label_face else "", 20),
                     signer, room, notes, "signer line (signature NAME)")
        lead = "<w:tab/>"
    else:
        ind = re.search(r'<w:ind w:left="(\d+)"', p_xml)
        room = (text_width_at(xml, start) or 11000) - (int(ind.group(1)) if ind else 0)
        rpr = fitted(rpr, "  " + signer, room, notes, "signer line (guide NAME(S))")
        lead = ""
    run = (f'<w:r>{rpr}<w:br/>{lead}<w:t xml:space="preserve">'
           f'{"" if tabbed else "  "}{xml_escape(signer)}</w:t></w:r>')
    k = p_xml.rfind("</w:p>")
    return p_xml[:k] + run + p_xml[k:]


EMU_PER_PT = 12700


def grow_text_box(xml, para_start, points, flags):
    """Edits that make the text box holding the paragraph at para_start taller
    by `points`, in both of Word's copies of a box (the DrawingML shape and the
    VML fallback). The QLD Consumer Building Guide's owner acknowledgement is a
    group of fixed-size boxes: the NAME(S) box holds exactly its four lines, so
    a signer line under the name was clipped. The box only grows into empty
    space: never past the group, never into a box below it - otherwise nothing
    changes and the line is flagged for a person."""
    emu = int(points * EMU_PER_PT)
    wsp = xml.rfind("<wps:wsp>", 0, para_start)
    if wsp >= 0 and xml.rfind("</wps:wsp>", 0, para_start) < wsp:
        sp = xml[wsp:xml.find("<w:txbxContent", wsp)]
        off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', sp)
        ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', sp)
        grp = xml.rfind("<wpg:wgp>", 0, wsp)
        if not (off and ext and grp >= 0):
            flags.append("signer line: the box holding it could not be measured - check it is not cut off")
            return []
        x0, y0, cx, cy = int(off.group(1)), int(off.group(2)), int(ext.group(1)), int(ext.group(2))
        group = xml[grp:xml.find("</wpg:wgp>", grp)]
        ch = re.search(r'<a:chExt cx="\d+" cy="(\d+)"/>', group)
        limit = int(ch.group(1)) if ch else y0 + cy
        for s in re.finditer(r'<a:off x="(-?\d+)" y="(-?\d+)"/>\s*<a:ext cx="(\d+)" cy="\d+"/>', group):
            sx, sy, scx = int(s.group(1)), int(s.group(2)), int(s.group(3))
            if sy >= y0 + cy and sx < x0 + cx and sx + scx > x0:
                limit = min(limit, sy)
        if y0 + cy + emu > limit:
            flags.append(f"signer line: only {(limit - y0 - cy) / EMU_PER_PT:.1f} pt free under the name's box - "
                         f"it may be cut off; check the page")
            return []
        a = wsp + ext.start()
        edits = [(a, a + len(ext.group(0)), f'<a:ext cx="{cx}" cy="{cy + emu}"/>')]
        return edits
    shape = max(xml.rfind("<v:shape ", 0, para_start), xml.rfind("<v:rect ", 0, para_start))
    if shape >= 0:
        tag_end = xml.find(">", shape)
        m = re.search(r'height:([\d.]+)pt', xml[shape:tag_end])
        if m:
            a = shape + m.start(1)
            return [(a, a + len(m.group(1)), f"{float(m.group(1)) + points:g}")]
    return []


def run(template, job, out_path, check_only, region):
    anchors = REGIONS[region]
    values = json.loads(Path(job).read_text(encoding="utf-8"))
    street_notes = []
    if street_format.applies(region):
        # the site's house number in brackets, as in the inclusions and the
        # preliminary agreement (feedback sheet 5 Nov 2026 row 7)
        values, street_notes = street_format.bracket_job(values)
    values = derive_values(values, region)
    fig_lines, fig_flags = contract_figures(values, region)
    fig_flags += street_notes
    aligned = aligned_amounts(values, region)
    company = values.get("_company")
    fit_notes, extra_lines = [], []   # sizes chosen for a company name; period / validity lines
    if company and not values.get("_signer_line"):
        fig_flags.append("company owner with no company_signatory in the job JSON - the '<name> on behalf "
                         "of <company>' line under the owner's name is left for a person")
    if company and region == "NSW":
        fig_flags.append("Attachment A checklist: a company acknowledges through the person who signs for "
                         "it - that person's Name (print) and Capacity are left for a person to complete")
    if values.get("_guarantor_address_from_owner"):
        fig_flags.append("guarantor address = the owner's address (the land contract's guarantee page names "
                         "the guarantor without one; the team typed the buyer's address on 26039) - confirm")
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

    # resolve each field to (paragraph index, key, label, value, mode, occ);
    # cell-mode fields resolve straight to an xml edit (their value lands in
    # the next table cell, outside the label's paragraph)
    plan, cell_edits, cell_shown, missing_anchor, blank_fields = [], [], [], [], []
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
            if mode == "cell":
                # validate the slot even with no value to type, so --check
                # catches template drift on every anchor
                slot, why = cell_slot(xml, paras[idx][1])
                if why:
                    missing_anchor.append(f"{key}: label {label!r} - {why}")
                    continue
                if not val:
                    blank_fields.append((key, label))
                    continue
                s, e, before, after = slot
                run_xml = cell_value_run(paras[idx][2], val)
                width = cell_width_at(xml, s)
                if company and key in ("_sch1_owner", "_deed_owner", "owners") and width:
                    # a company's name with its ACN, sized to stay on one line
                    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run_xml, re.S)
                    new = fitted(rpr.group(0) if rpr else "", val, width, fit_notes, f"{key} ({label})")
                    run_xml = (run_xml[:rpr.start()] + new + run_xml[rpr.end():] if rpr
                               else run_xml.replace("<w:r>", f"<w:r>{new}", 1))
                cell_edits.append((s, e, before + run_xml + after))
                if "\n" in val:
                    cell_edits += top_aligned(xml, paras[idx][0], s)
                cell_shown.append((idx, key, label, val))
                continue
            if not val:
                blank_fields.append((key, label))
                continue
            if company and key == "_sch1_owner" and mode != "cell":
                # the owner's signature NAME line: the company's name with its
                # ACN at the size that keeps it on the line from the name's tab
                # stop to the margin (row 12)
                start = mode[1] if isinstance(mode, tuple) else 2233
                room = (text_width_at(xml, paras[idx][0]) or 11000) - start
                face = LABEL_RPR_RE.search(paras[idx][2])
                base = STRIP_RE.sub("", face.group(1)) if face else ""
                if isinstance(mode, tuple):     # QLD: the builder's name size
                    base = with_size(base, mode[2])
                rpr = fitted(base, val, room, fit_notes, f"{key} (signature NAME)")
                mode = (("tab_at", mode[1], int(re.search(r'w:sz w:val="(\d+)"', rpr).group(1)))
                        if isinstance(mode, tuple) else ("tab_rpr", rpr))
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
        plan.append((hits[nth - 1], key, label, aligned.get(key, val), "replace_amount", 1))

    # progress payments schedule: each percentage row's lone "$" AMOUNT cell;
    # the template's percentages must be the ones the figures were worked from
    prog = anchors.get("progress")
    if prog:
        lo, hi = scope_bounds(prog["scope"])
        if lo is None:
            missing_anchor.append(f"progress schedule: {prog['scope'][0]!r} not found")
        else:
            pcts = [i for i in range(lo, hi) if re.fullmatch(r"\d+%", ntexts[i].strip())]
            cells = [i for i in range(lo, hi) if ntexts[i].strip() == "$"]
            want = [f"{p}%" for p in prog["stages"]] + ["100%"]
            got = [ntexts[i].strip() for i in pcts]
            paired = len(cells) == len(pcts) and all(
                p < c and (k + 1 == len(pcts) or c < pcts[k + 1])
                for k, (p, c) in enumerate(zip(pcts, cells)))
            if got != want or not paired:
                missing_anchor.append(f"progress schedule: expected rows {want}, each with a lone $ "
                                      f"amount cell; found {got} and {len(cells)} $ cell(s)")
            else:
                for n, i in enumerate(cells, 1):
                    key = f"progress_{n}" if n <= len(prog["stages"]) else "progress_total"
                    label = f"{'TOTAL' if n > len(prog['stages']) else 'stage ' + str(n)} {want[n - 1]}"
                    val = str(values.get(key, "") or "").strip()
                    if val:
                        plan.append((i, key, label, aligned.get(key, val), "dollar_cell", 1))
                    else:
                        blank_fields.append((key, label))

    # QLD Schedule 2 Part B (issue #73): each row's printed percentage, then
    # its "$ 0.00" amount cell; the percentages must still be the template's
    pb = anchors.get("part_b")
    if pb:
        lo, hi = scope_bounds(pb["scope"])
        if lo is None:
            missing_anchor.append(f"Part B: {pb['scope'][0]!r} not found")
        else:
            pcts = [i for i in range(lo, hi) if re.fullmatch(r"\d+\.\d{2}%", ntexts[i].strip())]
            cells = [i for i in range(lo, hi) if AMOUNT_RE.fullmatch(ntexts[i].strip())]
            rows = pb["rows"] + [("progress_total", "TOTAL", 100)]
            want = [f"{pct}.00%" for _, _, pct in rows]
            got = [ntexts[i].strip() for i in pcts]
            paired = len(cells) == len(pcts) and all(
                p < c and (k + 1 == len(pcts) or c < pcts[k + 1])
                for k, (p, c) in enumerate(zip(pcts, cells)))
            if got != want or not paired:
                missing_anchor.append(f"Part B: expected rows {want}, each with a $ amount cell; "
                                      f"found {got} and {len(cells)} amount cell(s)")
            else:
                for (key, name, pct), i in zip(rows, cells):
                    label = f"Part B {name[:10]} {pct}%"
                    val = str(values.get(key, "") or "").strip()
                    if val:
                        plan.append((i, key, label, aligned.get(key, val), "replace_amount", 1))
                    else:
                        blank_fields.append((key, label))

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

    # NSW Special Conditions clause 1, price validity (feedback sheet 5 Nov 2026
    # row 6): the request's own validity line, checked word for word against the
    # saved request text, replaces the printed six-months wording; a request
    # that names a validity the job JSON does not carry is flagged
    if region == "NSW":
        words, how, why = validity_until(values, job)
        hits = [i for i, t in enumerate(ntexts) if VALIDITY_CLAUSE in t]
        if len(hits) != 1:
            missing_anchor.append(f"price validity: Special Conditions clause 1 ('{VALIDITY_CLAUSE}') found "
                                  f"{len(hits)} times")
        elif words:
            if VALIDITY_TAIL not in ntexts[hits[0]]:
                fig_flags.append(f"price validity NOT applied: clause 1 no longer ends {VALIDITY_TAIL!r} - "
                                 f"a person makes the change")
            else:
                plan.append((hits[0], "price_validity", "Special Conditions 1", words,
                             ("replace_tail", VALIDITY_TAIL), 1))
                extra_lines.append(f"price validity: APPLIED - {how}")
                if re.search(r"\bQ[1-4]\b", str(values.get("price_validity_line") or ""), re.I):
                    # the drive shows no one day for a quarter: 30th March (26060),
                    # 18th December (two Q4 jobs), the month alone on most signed ones
                    fig_flags.append(f"price validity: the request names a quarter, not a day - {words[:-1]!r} "
                                     f"written; confirm the day before issue")
        elif why:
            fig_flags.append(f"price validity NOT applied: {why}; the clause keeps its six months - a person "
                             f"makes the change")
        else:
            said = VALIDITY_MENTION_RE.search(amendments.request_text(job) or "")
            if said:
                fig_flags.append(f"the request mentions a price validity (\"{said.group(0)}\") but the job JSON "
                                 f"gives no price_valid_until - clause 1 keeps its six months")

    # QLD item 13 building period (feedback sheet 5 Nov 2026 row 11): the
    # printed 210 days becomes the team's figure for the job's storeys and size
    if region == "QLD":
        hits = [i for i, t in enumerate(ntexts) if QLD_PERIOD_RE.search(t)]
        if len(hits) != 1:
            missing_anchor.append(f"building period: 'practical completion within N days after "
                                  f"commencement' found {len(hits)} times")
        else:
            printed = QLD_PERIOD_RE.search(ntexts[hits[0]]).group(1)
            days, how = building_period(values)
            if printed != "210":
                missing_anchor.append(f"building period: the template prints {printed} days, not 210")
            elif days is None:
                extra_lines.append(f"building period: left at the printed 210 days - {how}")
                fig_flags.append(f"building period not worked out: {how}")
            elif days == 210:
                extra_lines.append(f"building period: 210 days ({how}) - as printed")
            else:
                plan.append((hits[0], "building_period", "practical completion within", str(days),
                             ("replace_days", "210"), 1))
                extra_lines.append(f"building period: {days} days ({how}; the template prints 210)")

    # approved per-job amendments (CD-10, issue #61): checked here, applied
    # with the fills; a refused one is reported and the template wording stays
    am_lines, range_edits, struck = [], [], []
    for aid, am, approval, why in amendments.for_document(values, "build_contract", job):
        kind, line = am.get("kind"), amendments.norm(am.get("request_line"))
        if approval and kind == "schedule":
            field = am.get("field")
            label = anchors.get("schedule", {}).get(field)
            hits = [i for i, t in enumerate(ntexts) if label and label_regex(label).search(t)]
            old_m = (RATE_RE.match(ntexts[hits[0]][label_regex(label).search(ntexts[hits[0]]).end():].lstrip(" :\t"))
                     if len(hits) == 1 else None)
            old, frm, to = plain_rate(old_m and old_m.group(0)), plain_rate(am.get("from")), plain_rate(am.get("to"))
            if not label:
                why = f"{field!r} is not a schedule value the run changes (only the interest rate)"
            elif len(hits) != 1 or not old_m:
                why = f"the {field} line ({label!r}) is not where the template should have it"
            elif not re.fullmatch(r"\d+(?:\.\d+)?%", to):
                why = f"the new value {am.get('to')!r} is not a rate like 12%"
            elif old != frm:
                why = f"the contract reads {old}; the request changes it from {frm or '(not stated)'}"
            else:
                plan.append((hits[0], f"amendment {aid}", label, to, ("replace_value", old), 1))
                am_lines.append((aid, f"{field}: {old} -> {to} (para {hits[0]})", approval, line))
                continue
        elif approval and kind == "strike_clause":
            style = anchors.get("clause_style")
            n = str(am.get("clause") or "").strip()
            heads = [k for k, (_, _, p) in enumerate(paras) if style and f'<w:pStyle w:val="{style}"/>' in p]
            target = [k for k in heads if n.isdigit() and re.match(rf"\s*Clause\s+{n}\.(?!\d)", ptexts[k])]
            title = re.sub(r"[^a-z0-9]+", " ", str(am.get("title") or "").lower()).strip()
            if not style:
                why = f"striking a clause is not set up for the {region} contract yet"
            elif len(target) != 1:
                why = f"Clause {n or '?'} heading found {len(target)} times in the general conditions"
            elif title and title not in re.sub(r"[^a-z0-9]+", " ", ptexts[target[0]].lower()):
                why = f"Clause {n} is {ptexts[target[0]].strip()!r}, not {am.get('title')!r}"
            elif not any(k > target[0] for k in heads):
                why = f"no clause heading after Clause {n} to end the range"
            else:
                k = target[0]
                nxt = min(h for h in heads if h > k)
                s, e = paras[k][0], paras[nxt][0]
                seg, runs = strike_range(xml[s:e])
                if not strike_read_back(xml[s:e], seg):
                    print(f"AMENDMENT {aid}: READ-BACK FAILED striking Clause {n} - nothing written")
                    return 1
                refs = sum(1 for j, t in enumerate(ntexts) if not k <= j < nxt
                           and re.search(rf"\bClause\s+{n}\b(?!\.\d)", t))
                range_edits.append((s, e, seg))
                struck.append((s, e, xml[s:e]))
                am_lines.append((aid, f"Clause {n} struck through: {ptexts[k].strip()} (paras {k}-{nxt - 1}, "
                                      f"{runs} runs; its {refs} mention(s) elsewhere - contents, cross-"
                                      f"references - left for the reviewer)", approval, line))
                continue
        am_lines.append((aid, f"REFUSED - {why}; a person makes this change", None, line))

    print(f"template : {Path(template).name}")
    print(f"region   : {region}")
    print(f"job      : {Path(job).name}")
    interim = "INTERIM PENDING MCR" in Path(template).name.upper()
    print("STATUS   : " + ("CD-5.2b rule 2 - staged INTERIM template, not yet MCR-filed; "
                           "review the draft against the licensed PDF before issue"
                           if interim else
                           "CD-5.2b rule 1 - approved blank from the region's CONTRACT folder"))
    print()
    print(f"{'field':<18} {'para':>5}  {'label':<18} value")
    print("-" * 80)
    for idx, key, label, val in sorted(
            [(i, k, l, v) for i, k, l, v, _, _ in plan] + cell_shown):
        print(f"{key:<18} {idx:>5}  {label:<18} {val.replace(chr(10), ' / ')[:40]}")
    for key, label in blank_fields:
        print(f"{key:<18} {'-':>5}  {label:<18} (no value - left blank)")
    if aligned:
        print()
        print("amounts aligned on their digits (a pad after the $, rows lined up in Arial): "
              + ", ".join(f"{k} {v!r}" for k, v in aligned.items()))
    if company:
        print()
        print(f"company owner : {company} (the ACN rides with the name; feedback sheet 5 Nov 2026)")
        if values.get("_signer_line"):
            print(f"signer line   : {values['_signer_line']}")
        for note in fit_notes:
            print(f"  size  {note}")
    for line in extra_lines:
        print(line)
    if fig_lines or fig_flags:
        print()
        for line in fig_lines:
            print(line)
        for flag in fig_flags:
            print(f"FLAG: {flag}")
    if am_lines or amendments.for_person(values):
        print()
        for aid, what, approval, line in am_lines:
            state = "REFUSED" if approval is None else ("APPLIES" if check_only else "APPLIED")
            print(f"AMENDMENT {aid} {state}: {what.replace('REFUSED - ', '')}")
            print(f"    request: {line!r}" + (f" | approval: {approval}" if approval else ""))
        for item in amendments.for_person(values):
            print(f"AMENDMENT WITH A PERSON: {item}")
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
    # paragraph compose on the same XML before it is spliced back once,
    # and cell edits land in the same descending pass
    edits = list(cell_edits) + range_edits
    by_para = {}
    for idx, key, label, val, mode, occ in plan:
        by_para.setdefault(idx, []).append((key, label, val, mode, occ))
    signer = values.get("_signer_line")
    shown_notes, shown_flags = len(fit_notes), len(fig_flags)
    for idx in sorted(by_para, reverse=True):
        start, end, p_xml = paras[idx]
        for key, label, val, mode, occ in by_para[idx]:
            p_xml, ok = fill_para(p_xml, label, val, mode, occ)
            if not ok:
                print(f"FILL FAILED at paragraph {idx} for {key} - stopping, nothing written")
                return 1
            if signer and ((key == "_sch1_owner" and mode != "cell") or (key == "owners" and label == "NAME(S):")):
                p_xml = signer_line(p_xml, mode, signer, xml, start, fit_notes)
                if xml.rfind("<w:txbxContent", 0, start) > xml.rfind("</w:txbxContent>", 0, start):
                    # the line sits in a fixed-size text box: one line taller
                    size = int(re.findall(r'<w:sz w:val="(\d+)"', p_xml)[-1]) / 2
                    edits += grow_text_box(xml, start, round(size * 1.25, 1), fig_flags)
        edits.append((start, end, p_xml))
    edits.sort(key=lambda e: e[0], reverse=True)
    applied_to = len(xml) + 1
    for start, end, new in edits:
        if end > applied_to:
            print("FILL FAILED: overlapping edits - stopping, nothing written")
            return 1
        xml = xml[:start] + new + xml[end:]
        applied_to = start

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
    for note in fit_notes[shown_notes:]:
        print(f"  size  {note}")
    for flag in fig_flags[shown_flags:]:
        print(f"FLAG: {flag}")
    print(f"\nwritten  : {out_path}")
    if interim:
        print("Filled from the staged interim template (not yet MCR-filed) - a person "
              "reads it against the licensed PDF before it is issued; issuing stays human.")
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
