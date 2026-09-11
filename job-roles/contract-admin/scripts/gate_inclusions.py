"""Quality gate for a finished Sydney inclusions document. Fail = it does not ship. Stdlib only.

    python gate_inclusions.py --docx <final.docx> --measure <align_report.json|measure.json>
                              --plan <layout_plan.json> [--report <gate_inclusions.txt>]

Checks (NSW inclusions feedback sheet 9.9, issue #35):

  layout    every label/wording pair in the plan sits level within the plan's
            tolerance (rows 1, 2, 4, 14, 15); each package heading is first on
            its page (row 4.1)
  pages     no empty page (row 12); page count against the blank's (a longer
            document is reported, an empty page fails)
  colour    every run black, no highlight, no run shading (rows 3, 13)
  notes     no template editor instruction left (fill_inclusions.EDITOR_NOTES)
  page 1    the values of each header column start at one x (row 1)
  page 13   the signature lines (a text box, which Word cannot measure) carry
            the tab stops that put the owner's name under the builder's and
            every "Date:" at one x (rows 14, 15) - checked in the XML

The measurement comes from word_layout.ps1 (the align report carries one under
"measure"; a plain measure JSON is accepted too). Exit 0 = PASS, 1 = FAIL.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fill_inclusions import EDITOR_NOTES, run_text, RUN_RE  # noqa: E402

XTOL = 1.0   # pt - horizontal agreement for tab-stopped values
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
            if prev and prev["page"] >= h["page"]:
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
    colours = sorted(set(re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', xml)) - {"000000"})
    if colours:
        out.append(f"colour   : FAIL - non-black colours {colours} (sheet row 3)")
        ok = False
    hl = len(re.findall(r"<w:highlight ", xml))
    shd = sum(len(re.findall(r"<w:shd ", m.group(0))) for m in re.finditer(r"<w:rPr>.*?</w:rPr>", xml, re.S))
    if hl or shd:
        out.append(f"colour   : FAIL - {hl} highlight(s), {shd} run shading(s) (sheet row 13)")
        ok = False
    if ok:
        out.append("colour   : all black, no highlight, no shading")
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


SIG_LABELS = ("Name of Owner 1:", "Name of Owner 2:", "Builders Representative:")


def check_signature_lines(docx, out):
    """Page 13 (a text box - Word cannot measure x there): the signature lines carry
    the two tab stops fill_inclusions.py sets, the owner's name follows a tab and the
    builder's name follows the label directly, so the names share one x and every
    Date: sits at one x by construction (sheet rows 14, 15)."""
    from fill_inclusions import FAMILIES, run_text as rt
    tabs = FAMILIES["sydney"].get("tabs") or {}
    t_name, t_date = tabs.get("sig_name"), tabs.get("sig_date")
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    ok, seen, problems = True, 0, []
    for m in re.finditer(r"<w:p\b[^>]*>.*?</w:p>", xml, re.S):
        p = m.group(0)
        runs = [r.group(0) for r in RUN_RE.finditer(p)]
        text = "".join(rt(r) for r in runs)
        label = next((l for l in SIG_LABELS if text.startswith(l)), None)
        if not label or "Date:" not in text:
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
            if body.strip() and tabs_in != 2:
                problems.append(f"{label} needs a tab before the name and one before Date:")
            if not body.strip() and tabs_in != 1:
                problems.append(f"{label} (blank) needs one tab before Date:")
    if seen == 0:
        out.append("page 13  : no tab-stopped signature lines found (non-Sydney template?)")
    elif problems:
        out.append("page 13  : FAIL - " + "; ".join(sorted(set(problems))) + " (sheet rows 14, 15)")
        ok = False
    else:
        out.append(f"page 13  : {seen} signature lines on tab stops - names at {t_name} twips "
                   f"(the builder label's measured width), every Date: at {t_date} twips")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--measure", required=True, help="align report (with 'measure') or a measure JSON")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--report")
    args = ap.parse_args()

    data = json.loads(Path(args.measure).read_text(encoding="utf-8"))
    measure = data.get("measure", data)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    out = []
    results = [check_layout(measure, plan, out), check_pages(measure, plan, out),
               check_xml(args.docx, out), check_anchors(measure, out),
               check_signature_lines(args.docx, out)]
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
