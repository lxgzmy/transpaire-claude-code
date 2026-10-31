"""Quality gate for a finished Sydney or SEQ inclusions document. Fail = it does not ship. Stdlib only.

    python gate_inclusions.py --docx <final.docx> --measure <align_report.json|measure.json>
                              --plan <layout_plan.json> [--report <gate_inclusions.txt>]

Checks (NSW inclusions feedback sheet 9.9, issue #35):

  layout    every label/wording pair in the plan sits level within the plan's
            tolerance (rows 1, 2, 4, 14, 15); each package heading is first on
            its page (row 4.1)
  pages     no empty page (row 12); page count against the blank's (a longer
            document is reported, an empty page fails)
  colour    every run black except the package headings, which must keep the
            template's colour (rows 3, 13; issue #58); no highlight, no shading
  section 18  one blank line between the NBN wording and the heading, and the
            heading on the same page as its label (issue #57)
  notes     no template editor instruction left (fill_inclusions.EDITOR_NOTES)
  page 1    the values of each header column start at one x (row 1)
  page 13   the signature lines (a text box, which Word cannot measure) carry
            the tab stops that put the owner's name under the builder's and
            every "Date:" at one x (rows 14, 15) - checked in the XML
  site box  the address is typed in the box under "located at;", the same in
            both of Word's copies, and nothing after the sentence itself - a
            flat-text read cannot tell the two apart (SEQ blank 1, 31 Oct 2026)

The measurement comes from word_layout.ps1 (the align report carries one under
"measure"; a plain measure JSON is accepted too). Exit 0 = PASS, 1 = FAIL.

--family seq (SEQ ESSENTIALS blanks, CD-9.12, 28 Oct 2026): layout, pages,
colour, notes, section 18 (absent there), page 13 (the same tab stops since
issue #94) and footer run as for Sydney; page 1 is Sydney's tab-stop rule,
which the SEQ fill does not set, so it is reported as not checked.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fill_inclusions import EDITOR_NOTES, SIG_LABELS, SITE_ANCHOR, run_text, RUN_RE, site_box  # noqa: E402
from edit_inclusions import P_RE, REGIONAL_RIGHT_BLANKS, is_package_heading, ptext  # noqa: E402

XTOL = 1.0   # pt - horizontal agreement for tab-stopped values
TEXT_LINE_PT = 13.5   # pt - one line of body text in the Sydney blanks (measured 13.1-14.6)
EDITOR_BLANKS = REGIONAL_RIGHT_BLANKS   # blank lines the editor leaves above the kept section 18 wording
RIGHT_COLUMN = ("HOUSE TYPE :", "HOUSE SIZE :", "HOUSE FAÇADE :", "GARAGE SIDE :")
LEFT_COLUMN = ("Lot No. :", "STREET :", "SUBURB :", "ESTATE :", "PRICE :")


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def find_n(paras, text, n):
    want, seen = norm(text), 0
    for p in paras:
        if norm(p["text"]) == want:
            seen += 1
            if seen == n:
                return p
    return None


def flow(p, usable):
    return p["page"] * usable + p["top"]


def check_layout(measure, plan, out):
    tol = float(plan.get("tolerance", 1.5))
    bad = 0
    if "steps" in measure:
        # align/check report: word_layout.ps1 measured every step after its edits
        for s in measure["steps"]:
            if s.get("status") == "level" or s.get("status") == "page top":
                continue
            bad += 1
            if s["kind"] == "pair":
                d = s.get("delta")
                out.append(f"  FAIL {s['left']!r:34} {('is %+.1f pt off' % d) if d is not None else 'not found /'} "
                           f"{(s['right'] or '')[:40]!r} (p{s.get('left_page')})")
            else:
                out.append(f"  FAIL {s['right']!r} {s.get('status')} (p{s.get('right_page')})")
        n_pairs = sum(1 for s in measure["steps"] if s["kind"] == "pair")
        n_heads = len(measure["steps"]) - n_pairs
        out.insert(0, f"layout   : {n_pairs} pairs level within {tol} pt, {n_heads} headings at page top"
                   if not bad else f"layout   : {bad} problem(s)")
        return bad == 0
    usable = float(measure.get("usable") or 635.0)
    L, R = measure["left"], measure["right"]
    for s in plan["steps"]:
        if s["kind"] == "pair":
            l, r = find_n(L, s["left"], s["left_n"]), find_n(R, s["right"], s["right_n"])
            if not l or not r:
                out.append(f"  FAIL pair not found: {s['left']!r} / {s['right'][:40]!r}")
                bad += 1
                continue
            d = flow(r, usable) - flow(l, usable)
            if abs(d) > tol:
                out.append(f"  FAIL {s['left']!r:34} is {d:+.1f} pt off {s['right'][:40]!r} (p{l['page']})")
                bad += 1
        else:
            h = find_n(R, s["right"], s["right_n"])
            if not h:
                out.append(f"  FAIL heading not found: {s['right']!r}")
                bad += 1
                continue
            prev = R[h["i"] - 1] if h["i"] > 0 else None
            if prev and prev.get("end_page", prev["page"]) >= h["page"]:   # the paragraph above ends on its page
                out.append(f"  FAIL {s['right']!r} is not first on its page (p{h['page']})")
                bad += 1
    n_pairs = sum(1 for s in plan["steps"] if s["kind"] == "pair")
    n_heads = len(plan["steps"]) - n_pairs
    out.insert(0, f"layout   : {n_pairs} pairs level within {tol} pt, {n_heads} headings at page top"
               if not bad else f"layout   : {bad} problem(s)")
    return bad == 0


def check_pages(measure, plan, out):
    ok = True
    empty = list(measure.get("empty_pages") or [])
    pages, expected = measure.get("pages"), plan.get("expected_pages")
    if empty:
        out.append(f"pages    : FAIL - empty page(s) {empty} (sheet row 12)")
        ok = False
    if expected and pages != expected:
        out.append(f"pages    : {pages} pages (the blank has {expected}) - "
                   + ("content grew past the blank; every page carries text, so this is a longer document, not a blank page"
                      if pages > expected and not empty else "check the page flow"))
    else:
        out.append(f"pages    : {pages}, none empty")
    return ok


def check_xml(docx, out):
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        others = {n: z.read(n).decode("utf-8") for n in z.namelist()
                  if re.match(r"word/(header|footer)\d*\.xml", n)}
    ok = True
    # The package headings keep the template's blue (issue #58); every other run is black.
    heads = [m for m in P_RE.finditer(xml) if not re.search(r"<w:p[ >]", m.group(0)[4:])
             and is_package_heading(ptext(m.group(0)))]
    rest, pos = [], 0
    for m in heads:
        rest.append(xml[pos:m.start()])
        pos = m.end()
    rest.append(xml[pos:])
    # colour on text a reader sees: a blank paragraph Word inserts before a heading inherits the
    # heading's blue on its empty paragraph mark, which prints nothing
    colours = sorted({c for r in RUN_RE.finditer("".join(rest)) if run_text(r.group(0)).strip()
                      for c in re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', r.group(0))} - {"000000"})
    if colours:
        out.append(f"colour   : FAIL - non-black colours {colours} outside the package headings (sheet row 3)")
        ok = False
    lost = [norm(ptext(m.group(0))) for m in heads
            if not set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', m.group(0))) - {"000000"}]
    if lost:
        out.append(f"colour   : FAIL - package heading(s) {lost} lost the template's colour (issue #58)")
        ok = False
    elif heads:
        out.append(f"colour   : {len(heads)} package heading(s) keep the template's colour")
    hl = len(re.findall(r"<w:highlight ", xml))
    shd = sum(len(re.findall(r"<w:shd ", m.group(0))) for m in re.finditer(r"<w:rPr>.*?</w:rPr>", xml, re.S))
    if hl or shd:
        out.append(f"colour   : FAIL - {hl} highlight(s), {shd} run shading(s) (sheet row 13)")
        ok = False
    if ok:
        out.append("colour   : everything else black, no highlight, no shading")
    text = " ".join(run_text(m.group(0)) for m in RUN_RE.finditer(xml)).lower()
    notes = [n for n in EDITOR_NOTES if n.lower() in text]
    if notes:
        out.append(f"notes    : FAIL - editor instructions still present: {notes}")
        ok = False
    else:
        out.append("notes    : no template editor instructions left")
    hf = sorted({c for x in others.values() for c in re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', x)} - {"000000"})
    if hf:
        out.append(f"note     : header/footer carry colours {hf} (template artwork, left as the blank has it)")
    return ok


def check_anchors(measure, out):
    ok = True
    anchors = measure.get("anchors") or []
    if isinstance(anchors, dict):  # older measure shape
        anchors = [{"anchor": k, **v} for k, v in anchors.items()]

    def xs(names, field="value_left"):
        return [(a["anchor"], a[field]) for a in anchors if a["anchor"] in names and a.get(field) is not None
                and a.get("value_text", "x").strip()]
    for label, names in (("page-1 right column", RIGHT_COLUMN), ("page-1 left column", LEFT_COLUMN)):
        vals = xs(names)
        if len(vals) >= 2:
            spread = max(v for _, v in vals) - min(v for _, v in vals)
            if spread > XTOL:
                out.append(f"page 1   : FAIL - {label} values start at different x: "
                           + ", ".join(f"{n.strip(' :')} {v}" for n, v in vals) + " (sheet row 1)")
                ok = False
            else:
                out.append(f"page 1   : {label} values share one x ({vals[0][1]} pt, spread {spread:.2f})")
    return ok


def check_section18(measure, out):
    """Issue #57: one blank line between the NBN wording and "18. REGIONAL REGULATIONS",
    and the heading on the same page as its label (never stranded at a page foot)."""
    s = measure.get("section18")
    if not s:
        out.append("section 18: not measured (no heading or NBN wording found)")
        return True
    # one body-text line (Segoe UI Light 11). Not the layout pass's blank-paragraph height:
    # two wordings one blank line apart measure ~27 pt top to top in these blanks.
    line = TEXT_LINE_PT
    problems = []
    if s.get("label_page") and s["heading_page"] < s["label_page"]:
        problems.append(f"the heading is stranded at the foot of page {s['heading_page']}, "
                        f"its label starts page {s['label_page']}")
    gap = None
    if s.get("note_page"):
        if s["heading_page"] == s["note_page"]:
            gap = (s["heading_top"] - s["note_last_top"]) / line - 1
            if not 0.5 <= gap <= 1.6:
                problems.append(f"{gap:.1f} blank line(s) between the NBN wording and the heading, want one")
        elif s["heading_page"] > s["note_page"] and "blanks_on_note_page" in s:
            # a new page is right when the kept area wording itself could not fit on the NBN
            # wording's page: it starts the new page with no more than the editor's 3 blank lines
            # left behind it (one blank line and the heading's two). Word decided it did not fit;
            # no line arithmetic - the wording needs 3 blanks plus at least 2 of its own lines (Word
            # keeps a lone line off a page foot), so "free lines" undercounted it (15 Oct 2026).
            # More blanks there is #57's gap pushing the heading over. The heading then starts the
            # page, the wording beside its label.
            if s["blanks_on_note_page"] > EDITOR_BLANKS:
                problems.append(f"{s['blanks_on_note_page']} blank lines follow the NBN wording on page "
                                f"{s['note_page']} (the editor leaves {EDITOR_BLANKS}): a gap pushed the heading "
                                f"to page {s['heading_page']}")
            if s.get("wording_page") != s["heading_page"]:
                problems.append(f"the heading starts page {s['heading_page']} but its area wording starts "
                                f"page {s.get('wording_page')}")
            if not s.get("heading_starts_page"):
                problems.append(f"the heading is on page {s['heading_page']} after the NBN wording's page "
                                f"but does not start it")
        elif s["heading_page"] > s["note_page"]:
            # measured before 15 Oct 2026 (no blank count): the old free-lines rule, which can only
            # fail a good document, never pass a bad one
            room = float(measure.get("page_top") or 0) + float(measure.get("usable") or 0) - s["note_last_top"]
            if room > 4 * line:
                problems.append(f"the heading starts page {s['heading_page']} although {room / line:.0f} lines "
                                f"are free below the NBN wording on page {s['note_page']}")
    if problems:
        out.append("section 18: FAIL - " + "; ".join(problems) + " (issue #57)")
        return False
    out.append("section 18: " + (f"{gap:.1f} blank line below the NBN wording" if gap is not None
                                 else "heading starts a new page") + ", heading on its label's page")
    return True


def check_footer_total(docx, out):
    """The footer's "Page n of N": N is Word's page count (NUMPAGES), never a typed number -
    the blanks type their own count, and a longer document read "Page 17 of 16" (16 Oct 2026;
    fill_inclusions.py makes it the field)."""
    import fill_inclusions as fi
    typed = 0
    with zipfile.ZipFile(docx) as z:
        for name in z.namelist():
            if re.fullmatch(r"word/footer\d*\.xml", name):
                x = z.read(name).decode("utf-8")
                typed += sum(1 for pm in fi.P_RE.finditer(x)
                             if fi.PAGE_INSTR_RE.search(pm.group(0)) and "NUMPAGES" not in pm.group(0)
                             and re.search(r"\bof\s*\d", "".join(fi.run_text(r.group(0))
                                                                for r in fi.RUN_RE.finditer(pm.group(0)))))
    if typed:
        out.append(f"footer   : FAIL - {typed} footer page number(s) give a typed total, not the page count")
        return False
    out.append("footer   : page totals are Word's page count")
    return True


def check_signature_lines(docx, out, family="sydney"):
    """Page 13 (a text box - Word cannot measure x there): the signature lines carry
    the two tab stops fill_inclusions.py sets, the owner's name follows a tab and the
    builder's name follows the label directly, so the names share one x and every
    Date: sits at one x by construction (sheet rows 14, 15)."""
    from fill_inclusions import FAMILIES, run_text as rt
    tabs = FAMILIES[family].get("tabs") or {}
    t_name, t_date = tabs.get("sig_name"), tabs.get("sig_date")
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    ok, seen, problems = True, 0, []
    for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", xml, re.S):
        p = m.group(0)
        runs = [r.group(0) for r in RUN_RE.finditer(p)]
        text = "".join(rt(r) for r in runs)
        label = next((l for l in SIG_LABELS if text.startswith(l)), None)
        if "Date:" not in text:
            continue
        if not label:
            # any other "Label: ... Date:" line would put its Date: off the shared x (issue #56:
            # the Owners Witness Name line was left out and its Date: sat 2 cm to the right)
            other = re.match(r"\s*([A-Z][^:]{2,40}:)", text[:text.index("Date:")])
            if other:
                problems.append(f"{other.group(1)} line carries a Date: that is not on the signature tab stops")
            continue
        seen += 1
        if f'w:pos="{t_name}"' not in p or f'w:pos="{t_date}"' not in p:
            problems.append(f"{label} line lacks tab stops {t_name}/{t_date}")
        body = text[len(label):text.index("Date:")].replace("\u2026", "").replace(".", "")
        tabs_in = p.count("<w:tab/>")
        if label == "Builders Representative:":
            if not text[len(label):].startswith(" ") or tabs_in != 1:
                problems.append("Builders Representative: name must follow the label directly, one tab before Date:")
        else:
            # a blank line's dotted run reaches past the name stop, so one tab
            # takes Date: to its stop; with no dots the first tab stops at the
            # name stop and a second is needed (SEQ blank 1's Name of Owner 2:)
            dots = "…" in text[len(label):text.index("Date:")]
            if body.strip() and tabs_in != 2:
                problems.append(f"{label} needs a tab before the name and one before Date:")
            if not body.strip() and dots and tabs_in != 1:
                problems.append(f"{label} (blank) needs one tab before Date:")
            if not body.strip() and not dots and tabs_in != 2:
                problems.append(f"{label} (blank, no dotted line) needs two tabs before Date:")
    if seen == 0:
        out.append("page 13  : no tab-stopped signature lines found (non-Sydney template?)")
    elif problems:
        out.append("page 13  : FAIL - " + "; ".join(sorted(set(problems))) + " (sheet rows 14, 15)")
        ok = False
    else:
        out.append(f"page 13  : {seen} signature lines on tab stops - names at {t_name} twips "
                   f"(the builder label's measured width), every Date: at {t_date} twips")
    return ok


def check_site_box(docx, out):
    """The site address sits in the box under the "located at;" sentence, once per
    copy of that box, and the sentence ends at "located at;" - as on every
    completed job. Flattened text reads a doubled inline address and the box's two
    copies alike, which is how blank 1 shipped the address outside its box."""
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    hits = [m.start() for m in re.finditer(re.escape(SITE_ANCHOR), xml)]
    if not hits:
        out.append("site box : not checked - no \"located at;\" sentence in this blank")
        return True
    problems = []
    for n, at in enumerate(hits, 1):
        end = at + len(SITE_ANCHOR)
        seg = xml[end:xml.find("</w:p>", at)]
        if (seg[:seg.find("<")] + run_text(seg)).strip():
            problems.append(f"sentence {n}: text typed after \"located at;\"")
        copies = [run_text(xml[s:e]).strip() for s, e in site_box(xml, at, end)]
        if not copies:
            problems.append(f"sentence {n}: no address box with it")
        elif not copies[0].upper().startswith("LOT"):
            problems.append(f"sentence {n}: the address box is empty or does not start with Lot")
        elif len(set(copies)) != 1:
            problems.append(f"sentence {n}: the address box's copies differ")
    if problems:
        out.append("site box : FAIL - " + "; ".join(problems))
        return False
    out.append(f"site box : the address in its box under each of {len(hits)} \"located at;\" sentence(s), "
               "both copies alike, nothing typed after the sentence")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--measure", required=True, help="align report (with 'measure') or a measure JSON")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--report")
    ap.add_argument("--family", default="sydney", help="template family (fill_inclusions.pick_family)")
    args = ap.parse_args()

    data = json.loads(Path(args.measure).read_text(encoding="utf-8"))
    measure = data.get("measure", data)
    if "line_height" in data and "line_height" not in measure:
        measure["line_height"] = data["line_height"]
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    out = []
    sydney = args.family == "sydney"
    results = [check_layout(measure, plan, out), check_pages(measure, plan, out), check_xml(args.docx, out)]
    if sydney:
        results.append(check_anchors(measure, out))
    else:
        out.append(f"page 1   : not checked - the page-1 tab stops are Sydney's; the {args.family} blank's "
                   f"typed spacing is kept")
    results.append(check_section18(measure, out))
    results.append(check_signature_lines(args.docx, out, args.family))
    results.append(check_site_box(args.docx, out))
    results.append(check_footer_total(args.docx, out))
    verdict = "PASS" if all(results) else "FAIL"
    lines = [f"gate_inclusions : {Path(args.docx).name}", ""] + out + ["", f"verdict  : {verdict}"
             + ("" if verdict == "PASS" else " - the document does not ship until every FAIL above is fixed")]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    return 0 if verdict == "PASS" else 1


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
