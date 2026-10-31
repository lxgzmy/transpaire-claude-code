"""Fill a blank Transpire INCLUSIONS template from a job JSON. Stdlib only.

    python fill_inclusions.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_inclusions.py --template <blank.docx> --job <job.json> --check

Copies the blank template and writes the client/lot values into it the same way a
person editing in Word does: a new run inserted after the label's whitespace,
inheriting that run's formatting. The template's own wording, styles, numbering
and inclusion text are never touched, so the output is the existing template with
values in it - not a regenerated document.

Every anchor is filled at ALL of its occurrences, because the signature pages are
duplicated for the builder's copy and the owner's copy (manual: "Repeat this on
the Builders and Owners copy").

Field anchors were verified against the blank Gunnedah INTEGRITY template and
three completed jobs in Z:\\PROJECTS\\TAMWORTH (lots 141, 143, 144). Rules: see
job-roles/contract-admin/rules/contract-docs.md (CD-*).

--check reports which anchors were found without writing anything, so a template
that has moved on can be caught before it produces a half-filled contract.
"""
import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

T_RE = re.compile(r"<w:t(?: [^>]*)?>.*?</w:t>", re.S)
RUN_RE = re.compile(r"<w:r(?: [^>]*)?>(?:(?!<w:r[ >]).)*?</w:r>", re.S)
# A gap run holds no value - only whitespace, and sometimes the label's colon,
# because Word splits "SUBURB:" into a 'SUBURB' run and a ':  ' run.
GAP_ONLY = re.compile(r"^[:\s\u00a0]*$")
# A floating text box - the owner-name box under ACKNOWLEDGEMENTS & SIGNATURE, the
# site-address box under the "located at;" sentence. Word stores each twice
# (mc:Choice + mc:Fallback), so filling both is what a person editing in Word
# produces. An empty box's paragraph may be written <w:p/> (SEQ blank 1's site box).
TXBX_RE = re.compile(r"<w:txbxContent>.*?</w:txbxContent>", re.S)
BOX_PARA = re.compile(r"<w:p\b[^>]*/>|<w:p\b[^>]*>.*?</w:p>", re.S)

# (anchor, json key, mode, exact)
#
# mode:
#   gap         - insert the value as a new run after the label's trailing gap runs
#   suffix      - label and value share one run, e.g. "PRICE : $"
#   dotted      - type the value into the anchor run's own dotted line
#   dotted_next - type the value into the dotted line in the FOLLOWING run
#   prefix      - append the value to following runs that already read "Lot "
#   textbox     - fill the empty floating text box that follows the anchor
#   after_lot   - type "Lot <value>" into the text box under the anchor sentence
#
# exact=True matches the whole run text, which matters because "SUBURB" is a
# substring of page 1's "SUBURB :" and would otherwise be filled twice.
#
# Anchors shared by every template family. Region-specific ones live in FAMILIES.
COMMON_FIELDS = [
    # --- page 1 header table (CD-2) ---
    ("Lot No. :",           "lot_no",      "gap",    True),
    ("STREET :",            "street",      "gap",    True),
    ("SUBURB :",            "suburb",      "gap",    True),
    ("ESTATE :",            "estate",      "gap",    True),
    ("HOUSE TYPE :",        "house_type",  "gap",    True),
    ("HOUSE SIZE :",        "house_size",  "gap",    True),
    ("HOUSE FA\u00c7ADE :", "facade",      "gap",    True),
    ("GARAGE SIDE :",       "garage_side", "gap",    True),
    # --- pages 10-13 signature / acknowledgement blocks (CD-3) ---
    ("Name of Owner 1:",    "owner_1",     "gap",         True),
    ("Name of Owner 2:",    "owner_2",     "dotted_next", True),
    ("LOT No:",             "lot_no",      "gap",         True),
    ("STREET:",             "street",      "gap",         True),
    ("SUBURB",              "suburb",      "gap",         True),
    ("Builders Representative:", "builders_rep", "dotted", False),
    # Every completed job puts ALL the owners in this box joined by " & ", not
    # just the first - verified on lot 113 Box Hill (two owners) and lot 141
    # Westdale (three). Kept as its own key rather than composed from
    # owner_1/owner_2 so a job with three owners can still say so, and so
    # jobs that do not set it behave exactly as before (see fill()).
    ("ACKNOWLEDGEMENTS & SIGNATURE", "owners", "textbox", True),
]

SITE_ANCHOR = "Being the owners of the proposed new home to be located at;"

# The NSW and QLD inclusions are DIFFERENT DOCUMENTS, not versions of one, and
# three things differ:
#
#   1. PRICE - Gunnedah's run reads "PRICE : $", SEQ's standard blank reads
#      "PRICE : " - but the SEQ Auxiliary blank (template 2) carries the $ like
#      Gunnedah, so both shapes exist WITHIN one family. Suffix matching
#      therefore treats a trailing $ as optional (fill() normalises both sides
#      with rstrip("$ "), the same normalisation the write path always used).
#   2. The site address - both families type it into the box under the
#      sentence. Gunnedah's box carries "Lot " runs to append to; of the SEQ
#      blanks, 2 and 3 carry a "Lot " run there and blank 1 (Transpire) an
#      empty box, so SEQ types the whole "Lot <address>" (after_lot).
#   3. pad - extra spaces between the template's own gap run and the value, so
#      the value lands where it lands on the real contracts. Both families indent
#      further than the blank, but by different amounts.
#
# Every pad below was read off completed jobs, not guessed: lots 141/142/143/144
# (Pioneer Close, Tamworth) for gunnedah, lots 13/21/58/59 (Zhang Street,
# Holmview) for seq. regress_page1.py re-checks them against those jobs.
#
# sydney rests on ONE job - lot 113, The Water Lane, Box Hill (26004) - and that
# is worth knowing before trusting its pads. The only other completed Sydney
# inclusions is lot 109 in the same estate, and it was drafted over several
# editing passes: it disagrees with lot 113 on six of the nine fields, and its
# job was later cancelled. Taking both would produce a tie on every one of those
# six, which the regression harness reads as "no convention" - a check that
# passes whatever the filler does. So lot 113 alone is the reference. Re-measure
# when a second clean Sydney job lands.
FAMILIES = {
    "gunnedah": {
        "match": "REGION - GUNNEDAH",
        "label": "Gunnedah / NSW INTEGRITY  (also used by Tamworth jobs)",
        "fields": [
            ("PRICE : $", "price", "suffix", True),
            (SITE_ANCHOR, "site_address", "prefix", True),
        ],
        "pads": {
            "Lot No. :": 0, "STREET :": 1, "SUBURB :": 0, "ESTATE :": 0,
            "HOUSE TYPE :": 4, "HOUSE SIZE :": 5, "HOUSE FA\u00c7ADE :": 0,
            "GARAGE SIDE :": 3, "PRICE : $": 5,
        },
    },
    "sydney": {
        "match": "REGION - SYDNEY",
        "label": "Sydney INTEGRITY  (Box Hill, Gables, Leppington, Menangle Park)",
        "fields": [
            # Same shape as gunnedah: the label run carries the $, and the
            # template has two "Lot " runs after the site sentence to append to.
            ("PRICE : $", "price", "suffix", True),
            (SITE_ANCHOR, "site_address", "prefix", True),
        ],
        "pads": {
            "Lot No. :": 1, "STREET :": 2, "SUBURB :": 0, "ESTATE :": 2,
            "HOUSE TYPE :": 4, "HOUSE SIZE :": 6, "HOUSE FAÇADE :": 0,
            "GARAGE SIDE :": 3, "PRICE : $": 6,
            # Sydney only: both completed Sydney jobs (lot 113, live, and lot
            # 109, cancelled) leave 4 spaces between the owner's name and the
            # following "Signature of Owner 1:" label on the two signature-page
            # occurrences. Gunnedah (lot 141) and SEQ (lots 13, 59) all glue the
            # two directly with no gap - so this is a genuine Sydney convention,
            # not one person's typing, and belongs on this family only.
            # Negative = trailing (see the "gap" branch in fill()).
            "Name of Owner 1:": -4,
        },
        # Tab stops instead of typed spaces (NSW inclusions feedback sheet 9.9,
        # rows 1, 14, 15 - 10 Sep 2026). Typed spaces put every value at a
        # slightly different x because the labels differ in width; a tab stop
        # puts each column's values at ONE x. Positions are twips from the
        # paragraph's left edge, measured in Word (11 Sep 2026):
        #   page1  - the completed Menangle Park jobs 26019/26021/26028 start
        #            left-column values ~85.5 pt and right-column values
        #            ~404.5 pt from the page edge; the cells start at 35.25 /
        #            318.75 pt, so 50.25 pt = 1005 twips and 85.75 pt = 1715.
        #   sig_name - the width of "Builders Representative: " in the signature
        #            line's font (Segoe UI Light 11 bold) is 111.75 pt = 2235
        #            twips, so the owner's name starts exactly under the
        #            builder's (sheet row 14).
        #   sig_date - 378 pt: past the longest dotted line on those lines
        #            (label + 32 ellipses = 348.75 pt) and inside the text box
        #            (568 pt wide) with the 105.75 pt "Date: .." run to spare,
        #            so every Date: sits at one x (sheet row 15).
        # gate_inclusions.py checks the page-1 x in Word and the page-13 tab
        # stops in the XML on every run (Word cannot measure inside text boxes).
        "tabs": {
            "page1": {"Lot No. :": 1005, "STREET :": 1005, "SUBURB :": 1005, "ESTATE :": 1005,
                      "PRICE : $": 1005, "HOUSE TYPE :": 1715, "HOUSE SIZE :": 1715,
                      "HOUSE FA\u00c7ADE :": 1715, "GARAGE SIDE :": 1715},
            "sig_name": 2235,
            "sig_date": 7560,
        },
    },
    "seq": {
        "match": "REGION - SEQ",
        "label": "SEQ / QLD ESSENTIALS",
        "fields": [
            ("PRICE :", "price", "suffix", True),
            (SITE_ANCHOR, "site_address", "after_lot", True),
        ],
        "pads": {
            "Lot No. :": 2, "STREET :": 2, "SUBURB :": 0, "ESTATE :": 2,
            "HOUSE TYPE :": 4, "HOUSE SIZE :": 5, "HOUSE FA\u00c7ADE :": 0,
            "GARAGE SIDE :": 3, "PRICE :": 6,
        },
        # The signature-page lines on Sydney's two tab stops (job 26059 review,
        # issue #94, INCLUSIONS row 12: the witness Date: and the owners' names
        # were out of line). The SEQ blanks type those lines exactly as
        # Sydney's do: Segoe UI Light bold at the 11 pt default, in the same
        # 568 pt text box, so Sydney's measured stops hold here unchanged.
        "tabs": {"sig_name": 2235, "sig_date": 7560},
    },
}


# Instructions the template addresses to whoever is editing it - not contract
# text. The SEQ template carries a conditional block that must be deleted for
# narrow lots, and the completed jobs do delete it. Filling a template does not
# remove these, so a draft issued unread would send them to a client.
#
# The last four are Sydney's wording, which none of the earlier patterns caught:
# a rain-garden/water-tank pair where one must go, an air-conditioning line to
# strike out, and two bathroom-2 notes. The completed lot 109 and lot 113 jobs
# resolve every one of them by hand. They are deliberately narrow: "if Applicable"
# on its own would fire on the "(if applicable)" that Gunnedah and SEQ use as
# ordinary contract text, three times between them. These four hit Sydney only.
EDITOR_NOTES = [
    "DELETE IF",
    "UPDATE THE NUMBERS",
    "DONT USE",
    "TO BE AMENDED",
    "DELETE NOT APPLICABLE",
    "DELETE AS REQUIRED",   # the AUXILIARY blanks' section-18 instruction
    "remove if not included",
    "Vanity Added",
    "Note: Add Bathroom",
]


# Placeholder text a blank template prints INSIDE a field, where a person types
# over it rather than beside it. The two Sydney AUXILIARY templates (3 and 4)
# carry "AUXILIARY" as their HOUSE TYPE value; leaving it turns a filled field
# into "Custom + Auxiliary UnitAUXILIARY". All four completed auxiliary jobs
# (25137, 25149, 25192, 26032) replaced it with the design name, so removing it
# is part of filling the field. Matched on the whole stripped run, per anchor,
# and only in the runs that belong to that field - it cannot reach contract text.
FIELD_PLACEHOLDERS = {
    "HOUSE TYPE :": {"AUXILIARY"},
}


def editor_notes_left(xml):
    """Editor instructions still present in the filled document."""
    text = " ".join(run_text(m.group(0)) for m in RUN_RE.finditer(xml))
    return [n for n in EDITOR_NOTES if n.lower() in text.lower()]


# Editor-instruction paragraphs the filler deletes outright, per family. Only a
# line every completed job of that family removes belongs here - deleting text
# is otherwise a person's call. The one entry so far: SEQ's narrow-lot note.
# All five completed SEQ jobs checked (lots 1, 2, 13, 58, 70 - 16 Aug 2026)
# removed the LINE and kept the accessible-entrance block it governs, so the
# line is part of producing the deliverable. Whether the BLOCK must also go
# (lot 12.5m wide or less) only the site plan can say - main() prints that
# decision as a warning every time the line is removed.
DELETE_PARAS = {
    "seq": ["DELETE IF BLOCK WIDTH IS 12.5M OR LESS"],
}

P_RE = re.compile(r"<w:p(?: [^>]*)?>.*?</w:p>", re.S)


def drop_instruction_paras(xml, fam_name):
    """Delete whole paragraphs that are purely template-editor instructions.

    A paragraph that is the only block of its table cell is blanked instead of
    deleted (a cell must keep at least one block element to stay valid docx).
    Returns (xml, [notes removed]).
    """
    removed = []
    for needle in DELETE_PARAS.get(fam_name or "", []):
        while True:
            hit = next(
                (m for m in P_RE.finditer(xml)
                 if needle.lower() in " ".join(
                     run_text(r.group(0))
                     for r in RUN_RE.finditer(m.group(0))).lower()),
                None)
            if hit is None:
                break
            cell_open = xml.rfind("<w:tc>", 0, hit.start())
            in_cell = (cell_open != -1
                       and xml.find("</w:tc>", cell_open) > hit.start())
            if in_cell:
                cell_close = xml.find("</w:tc>", hit.end())
                sole = len(P_RE.findall(xml[cell_open:cell_close])) == 1
            else:
                sole = False
            if sole:
                xml = xml[:hit.start()] + "<w:p/>" + xml[hit.end():]
            else:
                xml = xml[:hit.start()] + xml[hit.end():]
            removed.append(needle)
    return xml, removed


def pick_family(template_path):
    """Which family this template belongs to, from its path on Z:."""
    p = str(Path(template_path)).lower()
    for name, fam in FAMILIES.items():
        if fam["match"].lower() in p:
            return name, fam
    return None, None


def read_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run_text(run):
    """Visible text of a single <w:r>, with XML entities decoded."""
    return html.unescape("".join(
        re.sub(r"<[^>]+>", "", m.group(0))
        for m in T_RE.finditer(run)
    ))


def set_run_text(run, new):
    """Replace the text of a run's first <w:t>, dropping any others."""
    esc = xml_escape(new)
    seen = [False]

    def sub(m):
        if seen[0]:
            return ""
        seen[0] = True
        space = ' xml:space="preserve"' if esc != esc.strip() else ""
        return f"<w:t{space}>{esc}</w:t>"

    return T_RE.sub(sub, run)


def clone_run(run, text):
    """A new run carrying `text` with this run's formatting."""
    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S)
    return (
        "<w:r>"
        + (rpr.group(0) if rpr else "")
        + f'<w:t xml:space="preserve">{xml_escape(text)}</w:t>'
        + "</w:r>"
    )


TAB_RUN = "<w:r><w:tab/></w:r>"
# pPr children that come AFTER <w:tabs> in the schema - the tab stop goes before the first of them
PPR_AFTER_TABS = ("suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct",
                  "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
                  "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
                  "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
                  "pPrChange")


def tab_stop_xml(*positions):
    return "<w:tabs>" + "".join(f'<w:tab w:val="left" w:pos="{int(p)}"/>' for p in positions) + "</w:tabs>"


def paragraph_at(xml, pos):
    """(start, end) of the <w:p> element that contains offset pos."""
    start = xml.rfind("<w:p ", 0, pos)
    start2 = xml.rfind("<w:p>", 0, pos)
    start = max(start, start2)
    end = xml.find("</w:p>", pos) + len("</w:p>")
    return start, end


def box_after(xml, pos):
    """(start, end) of every copy of the first floating text box after offset pos.

    A DrawingML box sits in one mc:AlternateContent with its VML fallback, so a
    person typing into it fills both copies; a VML-only box is the one copy."""
    m = TXBX_RE.search(xml, pos)
    if not m:
        return []
    ac = xml.rfind("<mc:AlternateContent", 0, m.start())
    ac_end = xml.find("</mc:AlternateContent>", m.start())
    if ac != -1 and xml.find("</mc:AlternateContent>", ac) == ac_end:
        return [(b.start(), b.end()) for b in TXBX_RE.finditer(xml, ac, ac_end)]
    return [(m.start(), m.end())]


def site_box(xml, s, e):
    """Copies of the address box that belongs to the "located at;" run at s..e.

    Either the box floats in the sentence's own paragraph, ahead of the words
    (the Owner Occupier colour-selections page), or it is the next box after
    the paragraph with no text between (every page-15 sentence). [] otherwise."""
    ac_end = xml.rfind("</mc:AlternateContent>", 0, s)
    if ac_end != -1 and "</w:p>" not in xml[ac_end:s] and not run_text(xml[ac_end:s]).strip():
        return box_after(xml, xml.rfind("<mc:AlternateContent", 0, ac_end))
    pend = xml.find("</w:p>", e)
    copies = box_after(xml, pend)
    if copies and run_text(xml[pend:copies[0][0]]).strip():
        return []
    return copies


def box_text_edits(xml, span, text, placeholders=("Lot", "Lot:")):
    """Edits typing `text` into one copy of a text box.

    Over the box's placeholder run(s) when that is all it holds ("Lot "), else
    at the end of its first paragraph when it is empty. None when the box holds
    other words - a value never lands on top of contract text."""
    seg = xml[span[0]:span[1]]
    words = [(m.start(), m.end(), m.group(0)) for m in RUN_RE.finditer(seg) if run_text(m.group(0)).strip()]
    if words:
        if not all(run_text(r).strip() in placeholders for _, _, r in words):
            return None
        return [(span[0] + s, span[0] + e, set_run_text(r, text if n == 0 else ""))
                for n, (s, e, r) in enumerate(words)]
    p = BOX_PARA.search(seg)
    if not p:
        return None
    run = f'<w:r><w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>'
    if p.group(0).endswith("/>"):
        return [(span[0] + p.start(), span[0] + p.end(), p.group(0)[:-2].rstrip() + ">" + run + "</w:p>")]
    at = span[0] + p.end() - len("</w:p>")
    return [(at, at, run)]


def ppr_tab_edit(xml, pos, *positions):
    """An (start, end, replacement) edit adding tab stops to the pPr of the paragraph containing pos."""
    ps, pe = paragraph_at(xml, pos)
    open_end = xml.find(">", ps) + 1
    ppr = re.compile(r"<w:pPr>.*?</w:pPr>", re.S).match(xml, open_end)
    stops = tab_stop_xml(*positions)
    if not ppr:
        return (open_end, open_end, f"<w:pPr>{stops}</w:pPr>")
    body = ppr.group(0)
    if "<w:tabs>" in body:
        at = ppr.start() + body.index("</w:tabs>")
        return (at, at, stops[len("<w:tabs>"):-len("</w:tabs>")])
    for tag in PPR_AFTER_TABS:
        k = body.find(f"<w:{tag}")
        if k != -1:
            return (ppr.start() + k, ppr.start() + k, stops)
    at = ppr.end() - len("</w:pPr>")
    return (at, at, stops)


def dot_line(prefix, value, dots, lead=3):
    """Type `value` into a dotted line, keeping the line roughly its original length."""
    keep = dots[:lead]
    tail = dots[lead + len(value):]
    return f"{prefix}{keep}{value}{tail}"


def fill(xml, values, report, family):
    """Apply every field to every occurrence of its anchor, for one family."""
    runs = [(m.start(), m.end(), m.group(0)) for m in RUN_RE.finditer(xml)]
    texts = [run_text(r[2]) for r in runs]
    edits = []  # (start, end, replacement)

    # A job that names no "owners" falls back to owner_1, which is what this
    # filler did before the key existed. Single-owner jobs are unaffected either
    # way; two-owner jobs should set it.
    values = {**values, "owners": values.get("owners") or values.get("owner_1")}

    for anchor, key, mode, exact in COMMON_FIELDS + family["fields"]:
        pad = family["pads"].get(anchor, 0)
        value = values.get(key)
        entry = {"key": key, "anchor": anchor, "hits": 0}
        report.append(entry)
        if value is None or str(value).strip() == "":
            entry["skipped"] = True
            continue
        value = str(value)

        if mode == "textbox":
            # the empty floating box straight after each heading - no
            # placeholder run to find. Only that box: "every empty box after
            # the heading" also took the site-address box whenever it was empty
            # (the Owner Occupier blank's colour-selections page).
            for am in re.finditer(re.escape(xml_escape(anchor)), xml):
                copies = box_after(xml, am.end())
                if not copies or run_text(xml[am.end():copies[0][0]]).strip():
                    continue
                planned = [box_text_edits(xml, c, value, ()) for c in copies]
                if all(p is not None for p in planned):
                    for p in planned:
                        edits.extend(p)
                    entry["hits"] += len(planned)
            entry["value"] = value
            continue

        for i, t in enumerate(texts):
            if mode == "suffix":
                # the label's trailing $ is template typing, not identity: the
                # SEQ Auxiliary blank reads "PRICE : $" where the standard SEQ
                # blank reads "PRICE : ", so both sides are compared with the
                # same rstrip("$ ") the write below applies.
                tt, aa = t.strip().rstrip("$ "), anchor.rstrip("$ ")
                if (tt != aa) if exact else (aa not in tt):
                    continue
            elif (t.strip() != anchor) if exact else (anchor not in t):
                continue
            s, e, run = runs[i]

            if mode == "suffix":
                # "PRICE : $" -> "PRICE :     $606,000.00". The $ is written by
                # us, because SEQ's label does not carry one.
                base = anchor.rstrip("$ ")
                tabs = family.get("tabs", {}).get("page1", {})
                if anchor in tabs:
                    # tab-stopped value (sydney): label run, tab, value run
                    edits.append((s, e, set_run_text(run, base) + TAB_RUN + clone_run(run, f"${value}")))
                    edits.append(ppr_tab_edit(xml, s, tabs[anchor]))
                else:
                    edits.append((s, e, set_run_text(run, f"{base}{' ' * pad}${value}")))

            elif mode == "after_lot":
                # "Lot <address>" goes in the box under the sentence, once per
                # copy, with nothing typed after "located at;": all 182
                # completed SEQ inclusions on the drive hold it so, 173 of them
                # starting the box with "Lot" (31 Oct 2026). Blanks 2 and 3
                # carry a "Lot " run in the box, typed over; blank 1
                # (Transpire) leaves the box empty. The earlier reading - "typed
                # after the sentence, twice" - was the box's two copies read as
                # flat text; on blank 1 it left the box empty and the doubled
                # line pushed a sixteenth, empty page (job 26059 follow-up).
                copies = site_box(xml, s, e)
                planned = [box_text_edits(xml, c, f"Lot {value}") for c in copies]
                if planned and all(p is not None for p in planned):
                    for p in planned:
                        edits.extend(p)
                    entry["hits"] += len(planned)
                else:
                    entry["why"] = "no empty address box under the sentence"
                continue  # hits count the box copies typed into, not the sentence

            elif mode == "dotted":
                edits.append((s, e, set_run_text(
                    run, dot_line(anchor, value, t[len(anchor):]))))

            elif mode == "dotted_next":
                # the dotted line lives in the following run. lead=4 keeps the
                # leading space plus a few dots, matching every completed job
                # that has dots here at all: lot 113 and lot 109 (Sydney) both
                # keep ~3 leading dots before the name, and lot 141 (Gunnedah)
                # keeps 2. lead=1 (keeping only the space, no dots) matches
                # none of them - SEQ has no dots in this run either way, so is
                # unaffected by this value.
                if i + 1 >= len(runs):
                    continue
                sj, ej, rj = runs[i + 1]
                edits.append((sj, ej, set_run_text(
                    rj, dot_line("", value, texts[i + 1], lead=4))))

            elif mode == "prefix":
                # the sentence continues in following runs that already read "Lot "
                j = i + 1
                while j < len(runs) and texts[j].strip() in ("Lot", "Lot:", ""):
                    if texts[j].strip():
                        sj, ej, rj = runs[j]
                        edits.append((sj, ej, set_run_text(rj, f"{texts[j]}{value}")))
                        entry["hits"] += 1
                    j += 1
                continue

            else:  # gap - insert a new run after the label's trailing gap runs
                # A run with no text at all is a tab or a break, and marks the end
                # of the gap: on page 10 the name is typed straight after the label,
                # before the tab stops, not out past them.
                j = i + 1
                while j < len(runs) and texts[j] != "" and GAP_ONLY.match(texts[j]):
                    j += 1
                at = runs[j - 1] if j - 1 > i else runs[i]
                # The value replaces the template's own placeholder, it does not
                # sit after it. Only runs immediately past the gap are eligible.
                placeholders = FIELD_PLACEHOLDERS.get(anchor)
                if placeholders:
                    k = j
                    while k < len(runs) and texts[k].strip() in placeholders:
                        edits.append((runs[k][0], runs[k][1],
                                      set_run_text(runs[k][2], "")))
                        entry.setdefault("placeholders_cleared", 0)
                        entry["placeholders_cleared"] += 1
                        k += 1
                # A negative pad is trailing space, after the value - Sydney's
                # "Name of Owner 1:" convention leaves the gap between the name
                # and "Signature of Owner 1:", not between the label and the
                # name. Every other pad in FAMILIES is a leading indent (the
                # normal case), so a plain positive/zero value keeps its
                # existing meaning.
                tabs = family.get("tabs", {}).get("page1", {})
                if anchor in tabs:
                    # tab-stopped value (sydney): the typed gap spaces go (with
                    # them a wide label such as "HOUSE FAÇADE :" would reach past
                    # the stop and the tab would jump to the next default stop),
                    # a tab takes the value to the column's one x
                    for k in range(i + 1, j):
                        edits.append((runs[k][0], runs[k][1], set_run_text(runs[k][2], "")))
                    edits.append((at[1], at[1], TAB_RUN + clone_run(at[2], value)))
                    edits.append(ppr_tab_edit(xml, s, tabs[anchor]))
                else:
                    text = value + " " * -pad if pad < 0 else " " * pad + value
                    edits.append((at[1], at[1], clone_run(at[2], text)))

            entry["hits"] += 1

        entry["value"] = value

    # apply back-to-front so offsets stay valid
    for s, e, repl in sorted(edits, key=lambda x: -x[0]):
        xml = xml[:s] + repl + xml[e:]
    return xml


SIG_LABELS = ("Name of Owner 1:", "Name of Owner 2:", "Owners Witness Name:", "Builders Representative:")
ELLIPSIS = "\u2026"
# Dotted-line length of an empty line. The witness label is about three dots
# wider than "Name of Owner 2:" (the blank's typist gave it 31 dots to Owner 2's
# 34), so 29 ends it level with the others and well before the Date: stop (#56).
SIG_DOTS = {"Owners Witness Name:": 29}
SIG_DOTS_DEFAULT = 32


def signature_tabs(xml, values, family):
    """Page-13 signature lines on tab stops (sydney): name where the builder's name starts, Date: at one x.

    Only the paragraph-style lines that carry their own "Date:" are rebuilt
    (the signature-table cells on the earlier page have no Date in the cell and
    stay as filled). The blank types these with runs of spaces and default tab
    stops, so a typed name moves the Date: and the owner's name never starts
    where the builder's does (feedback sheet 9.9 rows 14 and 15).
    """
    tabs = family.get("tabs") or {}
    if not tabs.get("sig_name") or not tabs.get("sig_date"):
        return xml, 0
    rebuilt = 0
    out, pos = [], 0
    for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", xml, re.S):
        p = m.group(0)
        runs = [r.group(0) for r in RUN_RE.finditer(p)]
        text = "".join(run_text(r) for r in runs)
        label = next((l for l in SIG_LABELS if text.startswith(l)), None)
        if not label or "Date:" not in text:
            continue
        date_at = text.index("Date:")
        middle, date_text = text[len(label):date_at], text[date_at:]
        rprs = [re.search(r"<w:rPr>.*?</w:rPr>", r, re.S) for r in runs]
        rpr_label = rprs[0].group(0) if rprs and rprs[0] else ""
        rpr_value = next((x.group(0) for r, x in zip(runs[1:], rprs[1:]) if x and run_text(r).strip()), rpr_label)
        rpr_date = next((x.group(0) for r, x in zip(runs, rprs) if x and "Date:" in run_text(r)), rpr_label)
        # the blank types the builder's dotted line as ellipses ending in a
        # full stop ("……….") - both are line, not name
        name = middle.strip(" " + ELLIPSIS + ".")
        dots = middle.count(ELLIPSIS)
        stop = "." if middle.rstrip().endswith(".") else ""
        parts = [f'<w:r>{rpr_label}<w:t xml:space="preserve">{xml_escape(label)}</w:t></w:r>']
        if label == "Builders Representative:":
            # the name sits straight after the label; the dotted line fills out
            # to (about) its original length, the owner's tab stop points here
            tail = ELLIPSIS * max(0, dots - len(name)) if name else ELLIPSIS * dots
            parts.append(f'<w:r>{rpr_value}<w:t xml:space="preserve"> {xml_escape(name)}{tail}{stop}</w:t></w:r>')
        elif name:
            parts.append(TAB_RUN + f'<w:r>{rpr_value}<w:t xml:space="preserve">{xml_escape(name)}</w:t></w:r>')
        elif dots:
            cap = SIG_DOTS.get(label, SIG_DOTS_DEFAULT)
            parts.append(f'<w:r>{rpr_value}<w:t xml:space="preserve"> {ELLIPSIS * min(dots, cap)}</w:t></w:r>')
        else:
            # no name and no dotted line - SEQ blank 1 types its page-13 "Name of
            # Owner 2:" with spaces only. A tab to the name stop first, or the
            # one tab stops there and Date: sits in the name column.
            parts.append(TAB_RUN)
        parts.append(TAB_RUN + f'<w:r>{rpr_date}<w:t xml:space="preserve">{xml_escape(date_text)}</w:t></w:r>')
        open_tag = re.match(r"<w:p\b[^>]*>", p).group(0)
        ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
        ppr_xml = ppr.group(0) if ppr else "<w:pPr></w:pPr>"
        ppr_xml = re.sub(r"<w:tabs>.*?</w:tabs>", "", ppr_xml, flags=re.S)
        stops = tab_stop_xml(tabs["sig_name"], tabs["sig_date"])
        placed = False
        for tag in PPR_AFTER_TABS:
            k = ppr_xml.find(f"<w:{tag}")
            if k != -1:
                ppr_xml = ppr_xml[:k] + stops + ppr_xml[k:]
                placed = True
                break
        if not placed:
            ppr_xml = ppr_xml[:-len("</w:pPr>")] + stops + "</w:pPr>"
        out.append(xml[pos:m.start()])
        out.append(open_tag + ppr_xml + "".join(parts) + "</w:p>")
        pos = m.end()
        rebuilt += 1
    out.append(xml[pos:])
    return "".join(out), rebuilt


def write_docx(template, out, xml, parts=None):
    """Copy the template zip, swapping in the new document.xml (and any other
    part given in `parts`, name -> xml)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    parts = dict(parts or {}, **{"word/document.xml": xml})
    # Stage beside the output, NOT in the system temp dir - that is on C:, and
    # the org rules forbid writing client data there (repo CLAUDE.md).
    tmp_path = out.with_suffix(".partial")
    with zipfile.ZipFile(template) as zin, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in parts:
                data = parts[item.filename].encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp_path, out)
    return out


# The footer's "Page <PAGE field> of 16": every inclusions blank types its own page count after
# "of" (15, 16 or 17), so a document that runs past the blank's pages printed "Page 17 of 16"
# (26058, 16 Oct 2026). The team corrects it by hand (26020 reads "of 18"; 26032 carries Word's
# NUMPAGES field). The typed total becomes that field, in the typed digits' own formatting.
PAGE_INSTR_RE = re.compile(r"<w:instrText[^>]*>\s*PAGE\s*</w:instrText>")
FLD_END = 'w:fldCharType="end"'
SAFE_BETWEEN_RE = re.compile(r"\s*(?:<w:proofErr [^>]*/>\s*)*")


def footer_page_total(xml):
    """(xml, n): every typed page total after a PAGE field made a NUMPAGES field."""
    done = 0

    def fix(pm):
        nonlocal done
        p = pm.group(0)
        if not PAGE_INSTR_RE.search(p) or "NUMPAGES" in p:
            return p
        runs = list(RUN_RE.finditer(p))
        at = next((i for i, r in enumerate(runs) if PAGE_INSTR_RE.search(r.group(0))), None)
        end = next((i for i in range(at, len(runs)) if FLD_END in runs[i].group(0)), None)
        if end is None:
            return p
        tail = runs[end + 1:]
        texts = [run_text(r.group(0)) for r in tail]
        m = re.fullmatch(r"(\s*of\s*)(\d+)\s*", "".join(texts))
        if not m:
            return p
        digits, pos = [], 0
        for r, t in zip(tail, texts):
            a, b = pos, pos + len(t)
            if t and a >= m.start(2) and b <= m.end(2):
                digits.append(r)
            elif t and a < m.end(2) and b > m.start(2):
                return p   # a run that mixes the digits with other text: leave it, report it
            pos = b
        s, e = digits[0].start(), digits[-1].end()
        # only the digit runs (and proofing marks) between s and e - never a bookmark or field
        gaps = [p[digits[k].end():digits[k + 1].start()] for k in range(len(digits) - 1)]
        if any(not SAFE_BETWEEN_RE.fullmatch(g) for g in gaps):
            return p
        rpr = re.search(r"<w:rPr>.*?</w:rPr>", digits[0].group(0), re.S)
        rpr = rpr.group(0) if rpr else ""
        field = (f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
                 f'<w:r>{rpr}<w:instrText xml:space="preserve"> NUMPAGES </w:instrText></w:r>'
                 f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
                 f'<w:r>{rpr}<w:t>{m.group(2)}</w:t></w:r>'
                 f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>')
        done += 1
        return p[:s] + field + p[e:]

    return P_RE.sub(fix, xml), done


def footer_parts(template):
    """{part name: new xml} for the footers whose typed page total became NUMPAGES, the
    number of places changed, and the number of PAGE fields left with a typed total."""
    parts, changed, left = {}, 0, 0
    with zipfile.ZipFile(template) as z:
        for name in z.namelist():
            if re.fullmatch(r"word/footer\d*\.xml", name):
                old = z.read(name).decode("utf-8")
                new, n = footer_page_total(old)
                if n:
                    parts[name] = new
                    changed += n
                # a PAGE field still followed by a typed "of <number>"
                left += sum(1 for pm in P_RE.finditer(new)
                            if PAGE_INSTR_RE.search(pm.group(0)) and "NUMPAGES" not in pm.group(0)
                            and re.search(r"\bof\s*\d", "".join(run_text(r.group(0))
                                                                for r in RUN_RE.finditer(pm.group(0)))))
    return parts, changed, left


# GARAGE SIDE as the team writes it (CD-2.9 / JD-9.5, issue #59): left or right
# facing the house; "Via <the street or lane the driveway uses>" on a corner
# block or a lane lot; Rear Lane outside Sydney. Anything else is a typo or a
# placeholder ("LHS", "Via", "Via <street>") and stops the fill.
GARAGE_RE = re.compile(r"Left Hand Side|Right Hand Side|Rear Lane|Via [A-Z0-9][\w'-]*(?: [A-Z0-9][\w'-]*)*")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    values = json.loads(Path(args.job).read_text(encoding="utf-8"))
    garage = str(values.get("garage_side") or "").strip()
    if garage and not GARAGE_RE.fullmatch(garage):
        print(f"ERROR: garage_side {garage!r} is not a garage side the inclusions take - "
              "'Left Hand Side' / 'Right Hand Side' facing the house, 'Via <the street or lane the "
              "driveway uses>' on a corner block or a lane lot (CD-2.9), or blank with a flag",
              file=sys.stderr)
        return 3

    fam_name, family = pick_family(args.template)
    if not family:
        print(f"ERROR: no template family matches {args.template}", file=sys.stderr)
        print(f"       known families: {', '.join(FAMILIES)}", file=sys.stderr)
        print("       A new region needs its anchors and pads read off completed",
              file=sys.stderr)
        print("       jobs first - do not fill a template nobody has verified.",
              file=sys.stderr)
        return 2

    xml = read_xml(args.template)
    report = []
    new_xml = fill(xml, values, report, family)
    new_xml, dropped_notes = drop_instruction_paras(new_xml, fam_name)
    new_xml, sig_lines = signature_tabs(new_xml, values, family)

    print(f"template : {Path(args.template).name}")
    print(f"family   : {fam_name} - {family['label']}")
    print(f"job      : {Path(args.job).name}")
    print()
    print(f"{'field':<13} {'hits':>4}  {'anchor':<26} value")
    print("-" * 88)
    problems = []
    for info in report:
        key, anchor, hits = info["key"], info["anchor"][:26], info["hits"]
        if info.get("skipped"):
            print(f"{key:<13} {'-':>4}  {anchor:<26} (no value - left blank)")
            continue
        flag = "" if hits else f"   <-- {info['why'].upper() if info.get('why') else 'ANCHOR NOT FOUND'}"
        print(f"{key:<13} {hits:>4}  {anchor:<26} {info['value'][:30]}{flag}")
        if not hits:
            problems.append(f"{key} ({info['anchor'][:24]})")
    print()

    unknown = sorted(set(values) - {f[1] for f in COMMON_FIELDS + family["fields"]})
    if unknown:
        print(f"NOTE: job JSON has keys this template does not use: {', '.join(unknown)}")

    if problems:
        print(f"WARNING: no anchor found for: {', '.join(problems)}")
        print("The template may have changed. Do not issue this document - check it.")

    if family.get("tabs"):
        page1 = "page-1 values and " if family["tabs"].get("page1") else ""
        print(f"tabs     : {page1}{sig_lines} signature line(s) on tab stops "
              f"(sheet 9.9 rows 1, 14, 15) - gate_inclusions.py verifies the x positions")

    if dropped_notes:
        for n in dropped_notes:
            print(f"removed  : template editor instruction line {n!r}")
        print("           The conditional block it governed is STILL in the document.")
        print("           If the lot is 12.5m wide or less a person must delete that")
        print("           block too - read the frontage off the site plan.")

    notes = editor_notes_left(new_xml)
    if notes:
        print(f"WARNING: template editor instructions still in the document: "
              f"{', '.join(repr(n) for n in notes)}")
        print("These are notes to whoever edits the template, not contract text.")
        print("A person must action and remove them before this is issued.")

    footers, n_total, n_left = footer_parts(args.template)
    if n_total:
        print(f"footer   : the typed page total is Word's page count (NUMPAGES) in {n_total} place(s)")
    if n_left:
        print(f"WARNING: {n_left} footer page number(s) with a total this run does not recognise - "
              "check 'Page n of N' against the page count before issue")

    if args.check:
        print("(--check: nothing written)")
        return 1 if problems else 0

    if not args.out:
        print("ERROR: --out is required unless --check is given", file=sys.stderr)
        return 2

    out = write_docx(args.template, args.out, new_xml, footers)
    print(f"written  : {out}")
    print("DRAFT - a person must read this against the email and plans before it goes out.")
    return 1 if problems else 0


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
