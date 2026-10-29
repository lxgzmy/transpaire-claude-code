r"""Edit the content of a filled Sydney or SEQ inclusions document from the job's `upgrades` block. Stdlib only.

    python edit_inclusions.py --docx <filled.docx> --job <job.json> --blank <blank.docx>
                              --blank-measure <blank.measure.json> --out <edited.docx>
                              [--report <edit_inclusions.txt>] [--plan <layout_plan.json>]

What it changes (NSW inclusions feedback sheet 9.9, issue #35; instruction of
10 Sep 2026 that reversed the "spec content is a person's edit" rule):

  18. REGIONAL REGULATIONS  keep the ONE area pair for the job (label on the
      left, wording on the right), delete the other two and the red
      "DELETE NOT APPLICABLE ONE" line. Area from `upgrades.area`, else from the
      suburb: Box Hill / Gables -> box_hill, North Kellyville -> north_kellyville,
      anything else -> other (Water tank).
  Bathroom 2   `upgrades.bathroom2_ground` false: the three red notes go and the
      wording stays; true: "Bathroom & Ensuite" becomes "Bathroom, Bathroom 2 &
      Ensuite" on the vanity, basin-location and exhaust-fan lines (the pattern
      of completed job 26019) and the notes go.
  Air Conditioning  `upgrades.aircon` empty: the item STAYS, only the red
      "(remove if not included)" note goes (row 11 of the sheet - the 7 Sep run
      deleted the whole item, which was wrong). A description: the item's lines
      are replaced with it.
  UPGRADED INCLUSIONS items  `upgrades.items[]`, each with the category (a
      template label or Standard Variation category), the request line, the
      chosen variation row, the final wording and a confidence flag. An item
      whose label exists replaces that label's wording (or ONE line of it with
      `replaces`, or is appended with mode "add", or leaves with its label
      under mode "remove"; mode "replace" replaces the wording even of a
      label an earlier item wrote, as a request replacing a promotion
      line does); a new label is inserted at
      the Standard Variation category order, with its wording level on the
      right. Choosing the row and any custom wording is a person's judgment
      (10 Sep 2026): this script applies what the job JSON says and reports
      request -> row -> wording -> confidence for confirmation. It never picks.
  AUXILIARY blanks (CD-9.11, issue #63, 15 Oct 2026)  the upgrades are two sections,
      "UPGRADED INCLUSIONS – MAIN DWELLING" then "– AUX DWELLING"; each item's
      `dwelling` ("main"/"aux") picks the section its label is matched and
      placed in. No `dwelling` on an AUXILIARY blank -> MAIN, flagged; "aux"
      on a STANDARD blank -> refused.
  Hygiene   every run black except the package headings, which keep the
      template's blue (issue #58); no highlight, no run shading (row 3 / row 13).
  Section 18 spacing  one blank line between the NBN wording and the heading
      (issue #57): three blank paragraphs above the kept wording on the right.
  Table end   the blank pads both columns with 38 empty paragraphs after the
      last item; the section after the table starts its own page, so the
      padding only matters once the upgrades run past one page, where it
      lands on a page of its own (an empty page, sheet row 12). One is kept.
  Storeys   `upgrades.storeys` (1/2) is recorded and checked against the
      wording ("First Floor" on a single storey is flagged); nothing in the
      document changes with it.

SEQ ESSENTIALS blanks (contract admin review of job 26059, 28 Oct 2026; CD-9.12)
      the item rules above apply to their PROMOTIONAL UPGRADES section. There
      is no section 18, Bathroom 2 or air-con note there: those steps are
      Sydney's only, and air conditioning is an ordinary item. Promotion
      items come from promotion.py. Package headings stay at page top only
      where the blank puts them.

Nothing outside section 18, the three notes and the UPGRADED INCLUSIONS
section may change (row 8 of the sheet): the script compares every other
paragraph of both columns, and every text outside the body table, with the
blank / the input and refuses to write if anything differs.

The two columns are independent text flows (see word_layout.ps1), so the
script also writes `layout_plan.json`: which label must sit level with which
wording, and which headings must start a page. word_layout.ps1 -Mode align
executes it; gate_inclusions.py verifies the result.
"""
import argparse
import html
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fill_inclusions import DELETE_PARAS, EDITOR_NOTES, pick_family  # noqa: E402
import layout_pairs  # noqa: E402

P_RE = re.compile(r"<w:p\b[^>]*>.*?</w:p>", re.S)
T_RE = re.compile(r"<w:t(?: [^>]*)?>.*?</w:t>", re.S)
RUN_RE = re.compile(r"<w:r\b(?: [^>]*)?>.*?</w:r>", re.S)
RPR_RE = re.compile(r"<w:rPr>.*?</w:rPr>", re.S)
PPR_RE = re.compile(r"<w:pPr>.*?</w:pPr>", re.S)

REGIONAL_HEADING = "18. REGIONAL REGULATIONS"
AREAS = {
    "north_kellyville": ("North Kellyville ONLY", "rain garden"),
    "box_hill": ("Box Hill", "Connection of Recycled Water"),
    "other": ("All areas Excl. Box Hill", "Water tank as required"),
}
REGIONAL_LABELS = [v[0] for v in AREAS.values()]
# the red instruction line above the three area wordings: the STANDARD blanks
# say "DELETE NOT APPLICABLE ONE", the AUXILIARY blanks "(DELETE AS REQUIRED)"
REGIONAL_INSTRUCTIONS = ["DELETE NOT APPLICABLE ONE", "(DELETE AS REQUIRED)"]
REGIONAL_WORDING = REGIONAL_INSTRUCTIONS + ["rain garden", "Connection of Recycled Water",
                                            "Water tank as required"]
REGIONAL_RIGHT_BLANKS = 3   # one blank line + the two lines "18. REGIONAL REGULATIONS" wraps to
REGIONAL_AFTER_BLANKS = 2   # one blank line + the one line of "19. NCC 2022"
TABLE_END_BLANKS = 1        # blank paragraphs left at the foot of each column (the blanks carry 38)
LAST_STANDARD_LABEL = "Letterbox"          # the upgraded-section labels follow it on the left
UPGRADED_HEADING = "UPGRADED INCLUSIONS"   # the upgraded-section wording follows it on the right
# The AUXILIARY blanks split the section: "UPGRADED INCLUSIONS – MAIN DWELLING"
# then "– AUX DWELLING", each with its own labels and wording (CD-9.11).
DWELLINGS = {"MAIN DWELLING": "main", "AUX DWELLING": "aux"}
PAGE_TOP_HEADINGS = ("INTERNAL TURNKEY PACKAGE", "EXTERNAL TURNKEY PACKAGE", "UPGRADED INCLUSIONS")
AIRCON_LABEL = "Air Conditioning"
AIRCON_NOTE = "(remove if not included)"
AIRCON_FIRST = "Reverse cycle ducted air-conditioning system"
BATH2_NOTES = ["Note: If Vanity Added to Ground Floor Bathroom", "Note: Add Bathroom 2 if Applicable"]
BATH2_INLINE = "(Amend if Vanity Added to Bathroom 2)"
# the three lines a ground-floor Bathroom 2 joins, each as the STANDARD or the
# AUXILIARY blank words it (the AUXILIARY exhaust fan names its rooms on a
# "Location:" line under the fan, like the basins)
BATH2_VANITY = ["laminate cabinetry to Bathroom & Ensuite vanities", "laminate vanity to Bathroom & Ensuite"]
BATH2_LOCATION = "Location: Bathroom & Ensuite"
BATH2_FAN = "exhaust fan/light/dual heat lamp unit"
BATH2_OLD, BATH2_NEW = "Bathroom & Ensuite", "Bathroom, Bathroom 2 & Ensuite"

# Template label -> Standard Variation category, for the insertion order of new
# labels (sheet 9.9 row 9.4: "following the order of items in the STANDARD
# VARIATION"). Labels with no category are skipped when ranking.
LABEL_TO_CATEGORY = {
    "Ceiling Height": "Ceiling Height", "Alfresco": "Alfresco", "Shelving": "Shelving",
    "Cabinetry": "Cabinetry", "Benchtops": "Benchtops", "Tiles": "Tiling Walls",
    "Shower screens": "Showers screens", "Mirrors": "Mirrors", "Plumbing Hardware": "Plumbing Hardware",
    "Cooktop": "Appliances", "Oven": "Appliances", "Rangehood": "Appliances",
    "Exhaust Fan": "Electrical - Fans", "Electrical Allowances": "Electrical - Power",
    "Air Conditioning": "Air-Conditioning", "Wardrobe Doors": "Wardrobe Doors",
    "Screens": "Screens", "Window Coverings": "Window Coverings", "Driveway & Path": "Driveway & Path",
    "Carpet": "Carpet", "Floor Tiles": "Floor Tiles", "Timber Flooring": "Timber Flooring",
}
# The SEQ ESSENTIALS blanks' own labels (PROMOTIONAL UPGRADES and the labels the
# 26059 review added, 28 Oct 2026), ranked on the QLD Variation List.
SEQ_LABEL_TO_CATEGORY = {
    "Roof Covering": "Roofing", "Glazing": "Windows & Sliding Doors", "Entrance Door": "Entrance Door",
    "Wardrobes": "Wardrobe Doors", "Hinges & Drawer Runners": "Cabinetry", "Handles": "Cabinetry",
    "Shower Screens": "Showers screens", "Plumbing": "Plumbing Hardware", "Electrical": "Electrical - Lighting",
    "Air-Conditioning": "Air-Conditioning", "Window Furnishings": "Window Coverings",
}

# Per template family: the upgraded section's heading and which Sydney-only
# edits run. SEQ (contract admin review of job 26059, 28 Oct 2026): the
# PROMOTIONAL UPGRADES section takes the same item rules as Sydney's UPGRADED
# INCLUSIONS; it has no section 18, Bathroom 2 notes or air-con note, and its
# air conditioning is an ordinary item.
FAMILY_RULES = {
    "sydney": {"heading": "UPGRADED INCLUSIONS", "sydney_edits": True, "labels": {}},
    "seq": {"heading": "PROMOTIONAL UPGRADES", "sydney_edits": False, "labels": SEQ_LABEL_TO_CATEGORY},
}
OTHER_UPGRADE_HEADINGS = ("PROMOTIONAL UPGRADES",)   # package headings of the non-Sydney families


def use_family(fam):
    """Point the section helpers at one family's heading and label map."""
    global UPGRADED_HEADING
    rules = FAMILY_RULES[fam]
    UPGRADED_HEADING = rules["heading"]
    LABEL_TO_CATEGORY.update(rules["labels"])
    return rules


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def key(t):
    """Match key for categories/labels: case, spacing, '&'/'and', hyphens ignored."""
    t = norm(t).lower().replace("&", " and ").replace("-", " ")
    return re.sub(r"[^a-z0-9]+", "", t)


def ptext(p):
    return html.unescape("".join(re.sub(r"<[^>]+>", "", m.group(0)) for m in T_RE.finditer(p)))


def is_blank(p):
    return not norm(ptext(p))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_colour(rpr):
    rpr = re.sub(r"<w:color [^>]*/>", "", rpr)
    rpr = re.sub(r"<w:highlight [^>]*/>", "", rpr)
    return rpr


def para_parts(p):
    """(opening <w:p ...> tag, pPr xml or '', first run rPr or '')."""
    open_tag = re.match(r"<w:p\b[^>]*>", p).group(0)
    ppr = PPR_RE.search(p)
    ppr = ppr.group(0) if ppr else ""
    run = RUN_RE.search(p)
    rpr = ""
    if run:
        m = RPR_RE.search(run.group(0))
        rpr = m.group(0) if m else ""
    if not rpr and ppr:
        m = RPR_RE.search(ppr)
        rpr = m.group(0) if m else ""
    return open_tag, ppr, rpr


def make_para(template_p, text):
    """A paragraph carrying `text` in the template paragraph's formatting, black."""
    _, ppr, rpr = para_parts(template_p)
    ppr, rpr = strip_colour(ppr), strip_colour(rpr)
    run = f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>' if text else ""
    return f"<w:p>{ppr}{run}</w:p>"


def set_text(p, text):
    return make_para(p, text)


def normalise_self_closing(xml):
    """`<w:p .../>` (an empty paragraph) becomes `<w:p ...></w:p>` so one regex sees every paragraph."""
    return re.sub(r"<w:p\b([^>]*?)/>", r"<w:p\1></w:p>", xml)


def body_table(xml):
    """(start, end) of the largest table - the two-column inclusions body."""
    best = max(re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S), key=lambda m: len(m.group(0)))
    return best.start(), best.end()


def outer_cells(tbl):
    """[(start, end)] of the table's top-level cells, relative to the table string."""
    depth, cells, start = 0, [], None
    for m in re.finditer(r"<w:tc>|</w:tc>", tbl):
        if m.group(0) == "<w:tc>":
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                cells.append((start, m.end()))
    return cells


class Columns:
    """The body table's two cells as editable paragraph lists."""

    def __init__(self, xml):
        self.xml = normalise_self_closing(xml)
        self.ts, self.te = body_table(self.xml)
        tbl = self.xml[self.ts:self.te]
        cells = outer_cells(tbl)
        if len(cells) != 2:
            raise SystemExit(f"ERROR: body table has {len(cells)} top-level cells, expected 2 - "
                             f"this is not the two-column inclusions body")
        (ls, le), (rs, re_) = cells
        self.left_prefix, self.left = self._split(tbl[ls:le])
        self.right_prefix, self.right = self._split(tbl[rs:re_])
        self.between = tbl[le:rs]
        self.tbl_head = tbl[:ls]
        self.tbl_tail = tbl[re_:]

    @staticmethod
    def _split(cell):
        m = P_RE.search(cell)
        prefix, body = cell[: m.start()], cell[m.start():]
        # A bookmark marker can sit between two paragraphs (the AUXILIARY blank
        # has one stray <w:bookmarkEnd/>); fold it into the paragraph before it,
        # where it is equally valid, so the cell is paragraphs only. No text moves.
        while True:
            body, n = re.subn(r"</w:p>(\s*)(<w:bookmark(?:Start|End)\b[^>]*/>)", r"\2</w:p>\1", body)
            if not n:
                break
        paras = P_RE.findall(body)
        if "".join(paras) != body[: len("".join(paras))]:
            raise SystemExit("ERROR: a body cell holds something other than paragraphs")
        tail = body[len("".join(paras)):]
        if tail.strip() != "</w:tc>":
            raise SystemExit(f"ERROR: unexpected cell tail {tail[:60]!r}")
        return prefix, paras

    def rebuild(self):
        tbl = (self.tbl_head + self.left_prefix + "".join(self.left) + "</w:tc>" + self.between
               + self.right_prefix + "".join(self.right) + "</w:tc>" + self.tbl_tail)
        return self.xml[: self.ts] + tbl + self.xml[self.te:]

    def outside_text(self):
        return ptext(self.xml[: self.ts]) + "\x1f" + ptext(self.xml[self.te:])


def find_idx(paras, pred, start=0):
    for i in range(start, len(paras)):
        if pred(paras[i]):
            return i
    return -1


def exact(text):
    return lambda p: norm(ptext(p)) == norm(text)


def contains(text):
    return lambda p: norm(text).lower() in norm(ptext(p)).lower()


def span_end(paras, i):
    """Index after paragraph i and the blank paragraphs that trail it."""
    j = i + 1
    while j < len(paras) and is_blank(paras[j]):
        j += 1
    return j


def blank_like(paras, near):
    """A blank paragraph to clone, taken from the neighbourhood of `near`."""
    for k in range(near, min(len(paras), near + 6)):
        if is_blank(paras[k]):
            return make_para(paras[k], "")
    for k in range(near - 1, max(-1, near - 6), -1):
        if is_blank(paras[k]):
            return make_para(paras[k], "")
    return "<w:p/>"


def read_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def write_docx(src, out, xml):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".partial")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, out)


# ---------------------------------------------------------------- the edits

def area_for(job, up, log):
    area = (up.get("area") or "").strip().lower()
    if area in AREAS:
        log.append(f"area          : {area} (from job JSON upgrades.area)")
        return area
    suburb = str(job.get("suburb", "")).upper()
    if "BOX HILL" in suburb or "GABLES" in suburb:
        area = "box_hill"
    elif "NORTH KELLYVILLE" in suburb:
        area = "north_kellyville"
    else:
        area = "other"
    log.append(f"area          : {area} (derived from suburb {job.get('suburb', '')!r} - "
               f"Box Hill/Gables -> box_hill, North Kellyville -> north_kellyville, else other)")
    return area


def edit_regional(cols, area, log):
    keep_label, keep_word = AREAS[area]
    L, R = cols.left, cols.right
    h = find_idx(L, exact(REGIONAL_HEADING))
    if h < 0:
        h = find_idx(L, contains("REGIONAL REGULATIONS"))
    if h < 0:
        raise SystemExit("ERROR: '18. REGIONAL REGULATIONS' heading not found in the left column")
    # left: delete the two other labels and the blanks trailing each
    for label in REGIONAL_LABELS:
        if label == keep_label:
            continue
        i = find_idx(L, exact(label), h)
        if i < 0:
            raise SystemExit(f"ERROR: regional label {label!r} not found after the heading")
        del L[i:span_end(L, i)]
        log.append(f"section 18    : deleted left label {label!r} (+ its spacing)")
    ki = find_idx(L, exact(keep_label), h)
    if ki < 0:
        raise SystemExit(f"ERROR: kept regional label {keep_label!r} not found")
    # right: delete the instruction line and the two other wordings
    instructions = [n for n in REGIONAL_INSTRUCTIONS if find_idx(R, contains(n)) >= 0]
    if not instructions:
        raise SystemExit(f"ERROR: none of the regional instruction lines {REGIONAL_INSTRUCTIONS} "
                         f"found in the right column")
    for needle in REGIONAL_WORDING:
        if needle == keep_word or (needle in REGIONAL_INSTRUCTIONS and needle not in instructions):
            continue
        i = find_idx(R, contains(needle))
        if i < 0:
            raise SystemExit(f"ERROR: regional wording {needle!r} not found in the right column")
        end = i + 1 if needle in REGIONAL_INSTRUCTIONS else span_end(R, i)
        del R[i:end]
        log.append(f"section 18    : deleted right wording starting {needle!r}")
    kw = find_idx(R, contains(keep_word))
    if kw < 0:
        raise SystemExit(f"ERROR: kept regional wording {keep_word!r} not found")
    if kw + 1 >= len(R) or not is_blank(R[kw + 1]):
        R.insert(kw + 1, blank_like(R, kw))
        log.append("section 18    : inserted the blank line after the kept wording")
    # One blank line between the NBN wording and the heading (issue #57). The
    # heading sits in the left column glued above the kept label, which the
    # layout pass levels with this wording, so the heading's height is set by
    # the blank paragraphs above the wording in the right column: one blank
    # line plus the two lines the heading wraps to. The blanks carry 2
    # (heading tight under NBN) and the AUXILIARY blank 11 (a page break typed
    # as padding, which strands the heading at a page foot once content moves).
    n = 0
    while kw - n - 1 >= 0 and is_blank(R[kw - n - 1]):
        n += 1
    if n != REGIONAL_RIGHT_BLANKS:
        if n > REGIONAL_RIGHT_BLANKS:
            del R[kw - n:kw - REGIONAL_RIGHT_BLANKS]
        else:
            for _ in range(REGIONAL_RIGHT_BLANKS - n):
                R.insert(kw - n, blank_like(R, kw - n))
        kw += REGIONAL_RIGHT_BLANKS - n
        log.append(f"section 18    : {n} -> {REGIONAL_RIGHT_BLANKS} blank paragraph(s) above the kept wording "
                   "(one blank line between NBN and the heading)")
    # ...and one blank line between the kept wording and section 19's one-line heading.
    # What follows the kept wording depends on which pair was kept (the last pair carries
    # the blank's 4 trailing blanks, a middle one 2), so the gap varied by area.
    end = kw + 1
    while end < len(R) and not is_blank(R[end]):
        end += 1   # the kept wording may run over several paragraphs
    n = 0
    while end + n < len(R) and is_blank(R[end + n]):
        n += 1
    if end + n < len(R) and n != REGIONAL_AFTER_BLANKS:
        if n > REGIONAL_AFTER_BLANKS:
            del R[end:end + n - REGIONAL_AFTER_BLANKS]
        else:
            for _ in range(REGIONAL_AFTER_BLANKS - n):
                R.insert(end, blank_like(R, end))
        log.append(f"section 18    : {n} -> {REGIONAL_AFTER_BLANKS} blank paragraph(s) after the kept wording "
                   "(one blank line before section 19)")
    log.append(f"section 18    : kept {keep_label!r} <-> {norm(ptext(R[kw]))[:50]!r}")
    return norm(ptext(L[ki])), norm(ptext(R[kw]))


def edit_bathroom2(cols, on, log):
    R = cols.right
    for needle in BATH2_NOTES:
        i = find_idx(R, contains(needle))
        if i >= 0:
            del R[i]
            log.append(f"bathroom 2    : deleted note {needle!r}")
    i = find_idx(R, contains(BATH2_INLINE))
    if i >= 0:
        t = norm(ptext(R[i]).replace(BATH2_INLINE, ""))
        R[i] = set_text(R[i], t)
        log.append(f"bathroom 2    : removed {BATH2_INLINE!r} -> {t!r}")
    if on:
        vanity = next((k for k in (find_idx(R, contains(n)) for n in BATH2_VANITY) if k >= 0), -1)
        basin = find_idx(R, contains(BATH2_LOCATION))
        fan = find_idx(R, contains(BATH2_FAN))
        if fan >= 0 and BATH2_OLD not in ptext(R[fan]):
            # AUXILIARY wording: the fan's rooms are on the next "Location:" line
            fan = find_idx(R, contains(BATH2_LOCATION), fan + 1)
        for role, i in (("vanity", vanity), ("basin location", basin), ("exhaust fan", fan)):
            if i < 0:
                log.append(f"bathroom 2    : WARNING {role} line not found - check the wording by hand")
                continue
            t = ptext(R[i])
            if BATH2_OLD in t and BATH2_NEW not in t:
                t2 = norm(t.replace(BATH2_OLD, BATH2_NEW))
                R[i] = set_text(R[i], t2)
                log.append(f"bathroom 2    : {norm(t)[:45]!r} -> {t2[:60]!r}")
    else:
        log.append("bathroom 2    : not on the ground floor - notes removed, wording unchanged")


def is_upgraded_heading(text):
    """`UPGRADED INCLUSIONS`, or one of the AUXILIARY blanks' `UPGRADED INCLUSIONS – <dwelling>`."""
    t = norm(text)
    return t == UPGRADED_HEADING or (t.startswith(UPGRADED_HEADING + " ")
                                     and any(t.endswith(d) for d in DWELLINGS))


def upgraded_headings(paras):
    """Indexes of the upgraded-section headings in a right column, in order."""
    return [i for i, p in enumerate(paras) if is_upgraded_heading(ptext(p))]


def dwelling_of(heading_text):
    t = norm(heading_text)
    return next((v for k, v in DWELLINGS.items() if t.endswith(k)), "single")


def upgraded_sections(cols):
    """The upgraded section(s): [{dwelling, heading, labels, groups}], in document order.

    One `UPGRADED INCLUSIONS` heading -> one section, dwelling "single". The
    AUXILIARY blanks -> "main" then "aux". The left column has no heading of
    its own there: its labels run on after Letterbox, the main dwelling's
    first, so they are split by the main section's wording-group count. That
    holds while both columns stay in step, which check_structure() enforces
    on every edit.
    """
    L, R = cols.left, cols.right
    ls = find_idx(L, exact(LAST_STANDARD_LABEL))
    if ls < 0:
        raise SystemExit(f"ERROR: last standard label {LAST_STANDARD_LABEL!r} not found")
    labels = [i for i in range(ls + 1, len(L)) if not is_blank(L[i])]
    heads = upgraded_headings(R)
    if not heads:
        raise SystemExit(f"ERROR: {UPGRADED_HEADING!r} heading not found in the right column")
    sections = []
    for n, hi in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(R)
        groups, i = [], hi + 1
        while i < end:
            if is_blank(R[i]):
                i += 1
                continue
            j = i
            while j < end and not is_blank(R[j]):
                j += 1
            groups.append((i, j))
            i = j
        sections.append({"dwelling": dwelling_of(ptext(R[hi])), "heading": norm(ptext(R[hi])),
                         "heading_i": hi, "groups": groups})
    if len(sections) > 1 and [s["dwelling"] for s in sections] != ["main", "aux"]:
        raise SystemExit(f"ERROR: upgraded headings {[s['heading'] for s in sections]} - expected "
                         f"MAIN DWELLING then AUX DWELLING")
    k = 0
    for s in sections:
        s["labels"] = labels[k:k + len(s["groups"])] if s is not sections[-1] else labels[k:]
        k += len(s["labels"])
    return sections


def upgraded_section(cols):
    """(label indexes, [(group start, group end)]) across every upgraded section."""
    secs = upgraded_sections(cols)
    return [i for s in secs for i in s["labels"]], [g for s in secs for g in s["groups"]]


def check_structure(cols, where):
    secs = upgraded_sections(cols)
    for s in secs:
        if len(s["labels"]) != len(s["groups"]):
            names = [norm(ptext(cols.left[i])) for i in s["labels"]]
            firsts = [norm(ptext(cols.right[a]))[:30] for a, _ in s["groups"]]
            raise SystemExit(f"ERROR ({where}): {len(s['labels'])} labels but {len(s['groups'])} wording "
                             f"groups in {s['heading']} - the template's structure has changed.\n"
                             f"  labels: {names}\n  groups: {firsts}")
    return [i for s in secs for i in s["labels"]], [g for s in secs for g in s["groups"]]


def edit_aircon(cols, spec, log):
    L, R = cols.left, cols.right
    i = find_idx(L, exact(AIRCON_NOTE))
    if i >= 0:
        del L[i]
        log.append(f"air con       : deleted red note {AIRCON_NOTE!r}")
    if spec and str(spec).strip():
        labels, groups = check_structure(cols, "before air con")
        gi = find_idx(R, contains(AIRCON_FIRST))
        if gi < 0:
            raise SystemExit(f"ERROR: air-conditioning wording {AIRCON_FIRST!r} not found")
        s, e = next((g for g in groups if g[0] <= gi < g[1]), (gi, gi + 1))
        lines = [l.strip() for l in str(spec).replace("\r", "").split("\n") if l.strip()]
        R[s:e] = [make_para(R[s], l) for l in lines]
        log.append(f"air con       : specified - wording replaced with {len(lines)} line(s): {lines[0][:60]!r}")
    else:
        log.append("air con       : not in the request - item kept, only the red note removed (sheet row 11)")


def category_rank(categories):
    return {key(c): n for n, c in enumerate(categories)}


def edit_items(cols, items, categories, log, flags):
    L, R = cols.left, cols.right
    ranks = category_rank(categories)
    touched = {}  # label key -> group index handled this run
    results = []
    for it in items:
        cat = str(it.get("category", "")).strip()
        wording = str(it.get("wording", "")).replace("\r", "").strip()
        conf = str(it.get("confidence", "") or "").lower() or "low"
        mode = str(it.get("mode", "") or "").lower()
        if not cat or (not wording and mode != "remove"):
            raise SystemExit(f"ERROR: upgrades item needs 'category' and 'wording': {it}")
        if conf not in ("high", "medium", "low"):
            flags.append(f"item {cat!r}: confidence {conf!r} is not high/medium/low - treated as low")
            conf = "low"
        if conf != "high":
            flags.append(f"item {cat!r}: confidence {conf} - confirm the wording before issue")
        lines = [l.strip() for l in wording.split("\n") if l.strip()]
        check_structure(cols, f"item {cat!r}")
        secs = upgraded_sections(cols)
        dwelling = str(it.get("dwelling", "") or "").strip().lower()
        if len(secs) == 1:
            if dwelling == "aux":
                raise SystemExit(f"ERROR: item {cat!r} is for the aux dwelling but this template has one "
                                 f"UPGRADED INCLUSIONS section - use an AUXILIARY blank")
            sec = secs[0]
        else:
            if not dwelling:
                flags.append(f"item {cat!r}: no 'dwelling' given on an auxiliary template - written under "
                             f"MAIN DWELLING; confirm")
                dwelling = "main"
            if dwelling not in ("main", "aux"):
                raise SystemExit(f"ERROR: item {cat!r}: dwelling {dwelling!r} - use \"main\" or \"aux\"")
            sec = next(s for s in secs if s["dwelling"] == dwelling)
        labels, groups, section = sec["labels"], sec["groups"], sec["heading"]
        if not labels:
            raise SystemExit(f"ERROR: {section} has no labels to place item {cat!r} against")
        # match the category to an existing label (direct, or through the alias map)
        li = None
        for n, i in enumerate(labels):
            lab = norm(ptext(L[i]))
            if key(lab) == key(cat) or key(LABEL_TO_CATEGORY.get(lab, "")) == key(cat):
                li = n
                break
        if mode == "remove":
            # the label and its wording leave the section together, each with the
            # blank lines that trail it (the layout pass re-levels what follows)
            if li is None:
                raise SystemExit(f"ERROR: item {cat!r}: mode \"remove\" but no such label in {section}")
            s, e = groups[li]
            lab = norm(ptext(L[labels[li]]))
            gone = [norm(ptext(R[k])) for k in range(s, e)]
            del R[s:span_end(R, e - 1)]
            del L[labels[li]:span_end(L, labels[li])]
            action = f"removed label {lab!r} and its {len(gone)} line(s)"
            lines = []
        elif li is not None:
            s, e = groups[li]
            lab = norm(ptext(L[labels[li]]))
            replaces = it.get("replaces")
            # `replaces` names one line to swap, so it wins over the "label already
            # written this run -> add" default (26059: the black shower rail and sink
            # mixer were added beside the chrome ones the promotion had written)
            if mode == "add" or (not mode and not replaces and (sec["dwelling"], key(lab)) in touched):
                R[e:e] = [make_para(R[s], l) for l in lines]
                action = f"added {len(lines)} line(s) under existing label {lab!r}"
            elif replaces:
                k = next((k for k in range(s, e) if norm(replaces).lower() in norm(ptext(R[k])).lower()), None)
                if k is None:
                    raise SystemExit(f"ERROR: item {cat!r}: no line containing {replaces!r} under {lab!r}")
                R[k:k + 1] = [make_para(R[k], l) for l in lines]
                action = f"replaced the line containing {replaces!r} under {lab!r}"
            else:
                R[s:e] = [make_para(R[s], l) for l in lines]
                action = f"replaced the {e - s} line(s) under existing label {lab!r}"
            touched[(sec["dwelling"], key(lab))] = True
        else:
            # new label: before the first ranked label whose category comes later in the sheet
            rank = ranks.get(key(cat))
            if rank is None:
                alias = next((v for k_, v in LABEL_TO_CATEGORY.items() if key(k_) == key(cat)), None)
                rank = ranks.get(key(alias)) if alias else None
            # nearest successor in sheet order: the existing label with the smallest
            # category rank above the new one (the template's own order is not quite
            # the sheet's - Alfresco sits second - so "first label ranked higher"
            # would drop Wardrobe Doors in front of Alfresco instead of Shelving)
            pos = len(labels)
            before = norm(str(it.get("before", "") or ""))
            at = next((n for n, i in enumerate(labels) if before and norm(ptext(L[i])) == before), None)
            if before and at is None:
                raise SystemExit(f"ERROR: item {cat!r}: 'before' label {before!r} not in {section}")
            if at is not None:
                # placed by the job JSON (the agreed document's own order wins over
                # the Standard Variation order, e.g. Trim after Windows & Sliding Doors)
                pos = at
            elif rank is not None:
                best = None
                for n, i in enumerate(labels):
                    lab = norm(ptext(L[i]))
                    r = ranks.get(key(LABEL_TO_CATEGORY.get(lab, lab)))
                    if r is not None and r > rank and (best is None or r < best[0]):
                        best = (r, n)
                if best:
                    pos = best[1]
            else:
                flags.append(f"item {cat!r}: not a Standard Variation category - appended at the end of "
                             f"{section}; confirm the position")
            label_template = L[labels[0]]
            word_template = R[groups[0][0]]
            if pos < len(labels):
                li_at, rg_at = labels[pos], groups[pos][0]
                L[li_at:li_at] = [make_para(label_template, cat), blank_like(L, li_at)]
                R[rg_at:rg_at] = [make_para(word_template, l) for l in lines] + [blank_like(R, rg_at)]
                after = norm(ptext(L[li_at + 2]))
                action = (f"inserted new label {cat!r} before {after!r} "
                          + ("(placed by the job JSON)" if at is not None else "(Standard Variation order)"))
            else:
                li_at = labels[-1] + 1
                rg_at = groups[-1][1]
                L[li_at:li_at] = [blank_like(L, li_at - 1), make_para(label_template, cat)]
                R[rg_at:rg_at] = [blank_like(R, rg_at - 1)] + [make_para(word_template, l) for l in lines]
                action = f"appended new label {cat!r} at the end of {section}"
            touched[(sec["dwelling"], key(cat))] = True
        if len(secs) > 1:
            action += f" [{sec['dwelling'].upper()} DWELLING]"
        results.append({**it, "dwelling": sec["dwelling"], "confidence": conf, "action": action,
                        "lines": lines})
        log.append(f"item          : {cat!r} - {action}")
    check_structure(cols, "after items")
    return results


def next_section_on_new_page(cols):
    """True when the paragraph right after the body table ends the section and the
    next section starts on a new page (no w:type, or nextPage / oddPage / evenPage)."""
    after = cols.xml[cols.te:]
    p = P_RE.search(after)
    if not p or after[: p.start()].strip() or "<w:sectPr" not in p.group(0):
        return False
    nxt = re.search(r"<w:sectPr\b.*?</w:sectPr>", after[p.end():], re.S)
    if not nxt:
        return False
    t = re.search(r'<w:type w:val="(\w+)"', nxt.group(0))
    return t is None or t.group(1) in ("nextPage", "oddPage", "evenPage")


def trim_table_end(cols, log):
    """Cut the padding at the foot of both columns to TABLE_END_BLANKS paragraphs."""
    counts = []
    for paras in (cols.left, cols.right):
        n = 0
        while n < len(paras) and is_blank(paras[len(paras) - 1 - n]):
            n += 1
        counts.append(n)
    if max(counts) <= TABLE_END_BLANKS:
        return
    if not next_section_on_new_page(cols):
        log.append(f"table end     : {counts[0]}/{counts[1]} blank paragraph(s) left at the foot of the columns - "
                   "the next section does not start on a new page here, so the padding may be holding it there")
        return
    for paras, n in zip((cols.left, cols.right), counts):
        if n > TABLE_END_BLANKS:
            del paras[len(paras) - n + TABLE_END_BLANKS:]
    log.append(f"table end     : {counts[0]}/{counts[1]} -> {TABLE_END_BLANKS} blank paragraph(s) at the foot of "
               "each column (the next section starts its own page; the padding spilled onto an empty page "
               "once the upgrades ran past one page)")


def is_package_heading(text):
    """INTERNAL / EXTERNAL TURNKEY PACKAGE and UPGRADED INCLUSIONS (with any '- MAIN/AUX DWELLING')."""
    t = norm(text).upper()
    return t in PAGE_TOP_HEADINGS[:2] or t.startswith(UPGRADED_HEADING) or t in OTHER_UPGRADE_HEADINGS


def end_cells_blank(cols, log):
    """Leave a blank paragraph at the end of each body column.

    The AUXILIARY blank ends both columns on text ("Provisions" on the left).
    Word measures a cell's last paragraph together with the end-of-cell mark,
    so the layout pass reads its position wrong and swings it +14 / -1 lines
    without ever levelling it (26032, 8 Oct 2026). A trailing blank paragraph
    is layout only - no text changes.
    """
    for name, col in (("left", cols.left), ("right", cols.right)):
        if not is_blank(col[-1]):
            col.append(blank_like(col, len(col) - 1))
            log.append(f"cell end      : blank paragraph added after the {name} column's last line "
                       f"({norm(ptext(col[-2]))[:30]!r}) so Word can measure it")


def hygiene(xml, log):
    # Everything black except the package headings, which keep the blank's blue
    # (issue #58, 14 Oct 2026 review: it reversed CD-9.8's "no exception").
    colour = re.compile(r'<w:color w:val="(?!000000")[^>]*/>')
    keep = [m.span() for m in P_RE.finditer(xml)
            if "<w:p " not in m.group(0)[4:] and "<w:p>" not in m.group(0)[4:]
            and is_package_heading(ptext(m.group(0))) and colour.search(m.group(0))]
    parts, pos, n_col = [], 0, 0
    for s, e in keep + [(len(xml), len(xml))]:
        segment, k = colour.subn('<w:color w:val="000000"/>', xml[pos:s])
        n_col += k
        parts += [segment, xml[s:e]]
        pos = e
    xml, kept = "".join(parts), len(keep)
    n_hl = len(re.findall(r"<w:highlight [^>]*/>", xml))
    xml = re.sub(r"<w:highlight [^>]*/>", "", xml)
    n_shd = 0

    def rpr_shd(m):
        nonlocal n_shd
        s, k = re.subn(r"<w:shd [^>]*/>", "", m.group(0))
        n_shd += k
        return s
    xml = RPR_RE.sub(rpr_shd, xml)
    log.append(f"hygiene       : {n_col} colour(s) set to black, {n_hl} highlight(s) and {n_shd} run "
               f"shading(s) removed; {kept} package heading(s) keep the template's colour "
               f"(sheet rows 3 and 13; issue #58)")
    return xml


def texts(paras):
    return [norm(ptext(p)) for p in paras if not is_blank(p)]


def scope_check(blank_cols, cols, log, dropped=()):
    """Everything outside the allowed regions must read exactly as the blank.

    `dropped`: the instruction lines fill_inclusions.py deletes for this family
    (DELETE_PARAS - SEQ's narrow-lot line); they are gone before this runs."""
    def kept(t):
        return not any(n.lower() in t.lower() for n in dropped)

    def left_seq(c):
        L = c.left
        ls = find_idx(L, exact(LAST_STANDARD_LABEL))
        return [t for t in texts(L[: ls + 1]) if t not in REGIONAL_LABELS and kept(t)]

    def right_seq(c):
        R = c.right
        heads = upgraded_headings(R)
        if not heads:
            raise SystemExit(f"ERROR: {UPGRADED_HEADING!r} heading not found in the right column")
        return [t for t in texts(R[:heads[0]])
                if not any(n.lower() in t.lower() for n in REGIONAL_WORDING) and kept(t)]

    # the upgraded headings themselves are template text too: same headings, same order
    if [norm(ptext(blank_cols.right[i])) for i in upgraded_headings(blank_cols.right)] != \
            [norm(ptext(cols.right[i])) for i in upgraded_headings(cols.right)]:
        log.append(f"SCOPE FAIL    : the {UPGRADED_HEADING} headings differ from the blank")
        return False
    problems = []
    for name, a, b in (("left", left_seq(blank_cols), left_seq(cols)),
                       ("right", right_seq(blank_cols), right_seq(cols))):
        if a != b:
            diff = [(x, y) for x, y in zip(a, b) if x != y][:3]
            problems.append(f"{name} column standard text differs from the blank: {diff or (len(a), len(b))}")
    if problems:
        for p in problems:
            log.append("SCOPE FAIL    : " + p)
        return False
    log.append("scope         : standard sections read exactly as the blank (sheet row 8)")
    return True


def build_plan(blank_measure, cols, regional_pair, tolerance=1.5):
    """Steps for word_layout.ps1 -Mode align, in document order."""
    L, R = cols.left, cols.right
    ltexts = [norm(ptext(p)) for p in L]
    rtexts = [norm(ptext(p)) for p in R]

    def ordinal(seq, idx):
        return sum(1 for t in seq[: idx + 1] if t == seq[idx])

    def find_n(seq, text, n):
        seen = 0
        for i, t in enumerate(seq):
            if t == norm(text):
                seen += 1
                if seen == n:
                    return i
        return -1

    steps = []
    # standard pairs from the blank measurement, re-located by text + ordinal
    bl = [norm(p["text"]) for p in blank_measure["left"]]
    br = [norm(p["text"]) for p in blank_measure["right"]]
    ls_blank = bl.index(norm(LAST_STANDARD_LABEL))
    for pr in layout_pairs.pairs_from_measure(blank_measure):
        if pr["right_i"] is None or pr["left_i"] > ls_blank or pr["left"] in REGIONAL_LABELS:
            continue
        if any(n.lower() in pr["right"].lower() for n in REGIONAL_WORDING):
            continue
        ln, rn = ordinal(bl, pr["left_i"]), ordinal(br, pr["right_i"])
        li, ri = find_n(ltexts, pr["left"], ln), find_n(rtexts, pr["right"], rn)
        if li < 0 or ri < 0:
            continue
        steps.append({"kind": "pair", "left": pr["left"], "left_n": ln, "right": pr["right"],
                      "right_n": rn, "_r": ri})
    # section 18: the kept pair (Sydney only)
    if regional_pair:
        kl, kw = regional_pair
        li, ri = ltexts.index(kl), rtexts.index(kw)
        steps.append({"kind": "pair", "left": kl, "left_n": ordinal(ltexts, li), "right": kw,
                      "right_n": ordinal(rtexts, ri), "_r": ri})
    # page-top headings: Sydney puts all three at the top of a page; another
    # family keeps a package heading there only where its blank does
    bR = blank_measure["right"]

    def starts_page_in_blank(h):
        n = next((n for n, r in enumerate(bR) if norm(r["text"]) == h), None)
        return n is not None and (n == 0 or bR[n - 1].get("end_page", bR[n - 1]["page"]) < bR[n]["page"])
    heads = PAGE_TOP_HEADINGS if regional_pair else \
        [h for h in PAGE_TOP_HEADINGS[:2] + (UPGRADED_HEADING,) if starts_page_in_blank(h)]
    for h in heads:
        ri = find_n(rtexts, h, 1)
        if ri >= 0:
            steps.append({"kind": "page_top", "right": h, "right_n": 1, "_r": ri})
    # the AUXILIARY blanks' MAIN / AUX DWELLING headings: kept at page top
    # wherever the blank itself starts a page with them
    for n, r in enumerate(bR):
        t = norm(r["text"])
        if t == UPGRADED_HEADING or not is_upgraded_heading(t):
            continue
        # the paragraph above ends on an earlier page (end_page since measure_version 2)
        if n == 0 or bR[n - 1].get("end_page", bR[n - 1]["page"]) < r["page"]:
            ri = find_n(rtexts, t, 1)
            if ri >= 0:
                steps.append({"kind": "page_top", "right": t, "right_n": 1, "_r": ri})
    # upgraded section: label k <-> first line of group k
    labels, groups = upgraded_section(cols)
    for i, (s, _) in zip(labels, groups):
        steps.append({"kind": "pair", "left": ltexts[i], "left_n": ordinal(ltexts, i),
                      "right": rtexts[s], "right_n": ordinal(rtexts, s), "_r": s})
    steps.sort(key=lambda s: s["_r"])
    for s in steps:
        s.pop("_r")
    return {"tolerance": tolerance, "expected_pages": blank_measure["pages"], "steps": steps}


def variation_context(job, items):
    """The normalised sheet wording of each item's chosen row, for the report (never applied)."""
    try:
        import variation_list
    except ImportError:
        return {}
    state = str(job.get("suburb", "")).upper().split()
    region = "QLD" if state and state[-1] == "QLD" else "NSW"
    try:
        data = variation_list.load(region)
    except SystemExit as e:
        return {"_error": str(e)}
    out = {"_sheet": f"{data['sheet']} (version date {data['version_date']})"}
    by_row = {r["row"]: r for r in data["rows"]}
    for it in items:
        row = it.get("variation_row")
        if row is None:
            continue
        r = by_row.get(int(row))
        out[int(row)] = (f"[{r['category']}] " + variation_list.normalise(r["text"])) if r else "ROW NOT IN SHEET"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True, help="the filled inclusions document")
    ap.add_argument("--job", required=True)
    ap.add_argument("--blank", required=True, help="the blank template the document was filled from")
    ap.add_argument("--blank-measure", required=True, help="word_layout.ps1 -Mode measure of the blank")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--plan")
    args = ap.parse_args()

    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    up = job.get("upgrades") or {}
    fam, _ = pick_family(args.blank)
    if fam not in FAMILY_RULES:
        print(f"edit_inclusions: family {fam!r} has no two-column content rules yet - nothing to do")
        return 0
    rules = use_family(fam)
    blank_measure = json.loads(Path(args.blank_measure).read_text(encoding="utf-8"))

    log, flags = [], []
    if not up:
        flags.append("job JSON has no 'upgrades' block - area from the suburb, Bathroom 2 assumed not on the "
                     "ground floor, air con assumed not requested, no upgrade items" if rules["sydney_edits"]
                     else "job JSON has no 'upgrades' block - no upgrade items")
    cols = Columns(read_xml(args.docx))
    blank_cols = Columns(read_xml(args.blank))
    outside_before = cols.outside_text()

    storeys = up.get("storeys")
    log.append(f"storeys       : {storeys if storeys in (1, 2) else 'not stated'}"
               + ("" if storeys in (1, 2) else " - say 2 when the request mentions an upper/first floor or a "
                  "ground-floor location, else read the design (sheet row 5)"))
    regional_pair = None
    if rules["sydney_edits"]:
        area = area_for(job, up, log)
        bath2 = up.get("bathroom2_ground")
        if bath2 is None:
            flags.append("upgrades.bathroom2_ground not stated - assumed NO ground-floor Bathroom 2; confirm")
            bath2 = False
        regional_pair = edit_regional(cols, area, log)
        edit_bathroom2(cols, bool(bath2), log)
        edit_aircon(cols, up.get("aircon"), log)
    elif up.get("aircon"):
        flags.append(f"upgrades.aircon is a Sydney key - on a {fam} blank give the air conditioning as an "
                     f"item under its own label; ignored")
    items = up.get("items") or []
    try:
        import variation_list
        categories = variation_list.load("QLD" if str(job.get("suburb", "")).upper().endswith("QLD") else "NSW")["categories"]
    except (ImportError, SystemExit) as e:
        categories = list(dict.fromkeys(LABEL_TO_CATEGORY.values()))
        flags.append(f"Standard Variation workbook not readable ({e}); category order taken from the "
                     f"built-in label map")
    results = edit_items(cols, items, categories, log, flags) if items else []
    end_cells_blank(cols, log)
    trim_table_end(cols, log)
    for r in results:
        if storeys == 1 and re.search(r"first floor|upper floor", " ".join(r["lines"]) + " "
                                      + str(r.get("variation_text", "")), re.I):
            flags.append(f"item {r['category']!r}: wording mentions an upper floor on a single-storey job")

    if not scope_check(blank_cols, cols, log, DELETE_PARAS.get(fam, ())):
        for l in log:
            print(l)
        print(f"\nREFUSED: an edit reached outside section 18 / the notes / {UPGRADED_HEADING}. Nothing written.")
        return 1

    xml = cols.rebuild()
    xml = hygiene(xml, log)
    after = Columns(xml)
    if after.outside_text() != outside_before:
        print("REFUSED: text outside the body table changed - nothing written.")
        return 1
    left_over = [n for n in EDITOR_NOTES if n.lower() in ptext(xml).lower()]
    if left_over:
        log.append(f"NOTES LEFT    : {left_over}")
    else:
        log.append("editor notes  : none left in the document")

    plan = build_plan(blank_measure, after, regional_pair)
    write_docx(args.docx, args.out, xml)
    if args.plan:
        Path(args.plan).write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")

    ctx = variation_context(job, items) if items else {}
    lines = [f"edit_inclusions : {Path(args.docx).name} -> {Path(args.out).name}",
             f"blank           : {Path(args.blank).name}", ""]
    lines += log
    lines += ["", f"layout plan     : {len(plan['steps'])} step(s) "
              f"({sum(1 for s in plan['steps'] if s['kind'] == 'pair')} label/wording pairs, "
              f"{sum(1 for s in plan['steps'] if s['kind'] == 'page_top')} page-top headings); "
              f"expected pages {plan['expected_pages']}"]
    if results:
        lines += ["", f"{UPGRADED_HEADING} items - a person confirms each row and wording before issue "
                  "(row choice and custom wording stay human, 10 Sep 2026):"]
        if ctx.get("_sheet"):
            lines.append(f"  sheet: {ctx['_sheet']}")
        for r in results:
            lines += ["", f"  [{r['confidence'].upper():6}] {r['category']} - {r['action']}",
                      f"    request : {r.get('request', '(not recorded)')}"]
            row = r.get("variation_row")
            if row is not None:
                lines.append(f"    row {row}  : " + str(ctx.get(int(row), r.get('variation_text', '?'))).replace("\n", "\n              "))
            else:
                lines.append("    row     : none (custom wording - a person approves it)")
            lines.append("    written : " + ("\n              ".join(r["lines"]) or "(label and wording removed)"))
            if r.get("note"):
                lines.append(f"    note    : {r['note']}")
    if flags:
        lines += ["", "TO CONFIRM:"] + [f"  - {f}" for f in flags]
    report = "\n".join(lines) + "\n"
    print(report)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    return 1 if left_over else 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
