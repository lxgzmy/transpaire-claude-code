r"""Regression tests for the contract admin feedback sheet of 5 Nov 2026. Stdlib only.

    python test_feedback_0511.py

Synthetic documents and names only (no client data). Each test names the
sheet row it guards:

  row 1   the request email saved into the job folder as Outlook names it
  row 5   amounts in one column line up on their digits
  row 7   the house number bracketed alike in every NSW document; a parent
          address ("29 Sample & 25 Example Street") replaced by the lot's own
          street when the plans name exactly one (CD-2.4, job 26060)
  row 11  QLD building period from storeys and house size
  rows 8-10, 12, 13, 16  a company owner: name with its ACN, sized to its
          line, "<signatory> on behalf of <company> ACN: ..." under it
  row 14  a promotion line the blank already carries is not added twice
  row 15  one blank line between upgrade items, and the gate fails either fault

The build contract's own fills are covered end to end by regress_hia.py
(QLD company, QLD period unknown, NSW company; every amount column checked
for alignment); the OSC phone form by shared/mcp/osc-api's gate tests.
"""
import io
import sys
import tempfile
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import edit_inclusions as E  # noqa: E402
import fill_hia  # noqa: E402
import fill_inclusions  # noqa: E402
import font_fit  # noqa: E402
import gate_inclusions  # noqa: E402
import msg_extract  # noqa: E402
import owner_names  # noqa: E402

FAILS = []


def check(cond, what):
    print(("  ok   " if cond else "  FAIL ") + what)
    if not cond:
        FAILS.append(what)


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def para(text):
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>' if text else "<w:p></w:p>"


def body_doc(left, right):
    """A two-column inclusions body as the SEQ blanks have it: labels left,
    wording right, the upgraded section after Letterbox / its heading."""
    cell = lambda ps: "<w:tc>" + "".join(para(t) for t in ps) + "</w:tc>"  # noqa: E731
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>'
            f"<w:tbl><w:tr>{cell(left)}{cell(right)}</w:tr></w:tbl>"
            "<w:p></w:p><w:sectPr/></w:body></w:document>")


def write_docx(path, xml):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)
    return path


LEFT = ["Letterbox", "", "Plumbing", "", "", "", "Electrical", ""]
RIGHT = ["Render style letter box", "PROMOTIONAL UPGRADES", "Sample sink to Kitchen",
         "Note: sample mixer note", "", "", "Two (2) sample pendant lights", ""]


def test_rows_14_15():
    print("rows 14-15: promotion lines already in the blank; blank lines between items")
    E.use_family("seq")
    cols = E.Columns(body_doc(LEFT, RIGHT))
    items = [{"category": "Plumbing", "wording": "Sample sink to Kitchen\nNote: sample mixer note\nNew tap line",
              "mode": "add", "confidence": "high"},
             {"category": "Electrical", "wording": "Two (2) sample pendant lights", "mode": "add",
              "confidence": "high"}]
    log, flags = [], []
    res = E.edit_items(cols, items, ["Plumbing Hardware", "Electrical - Lighting"], log, flags)
    right = [E.norm(E.ptext(p)) for p in cols.right]
    check(right.count("Sample sink to Kitchen") == 1, "a line the label already carries is not added again")
    check("New tap line" in right, "a line the label lacks is still added")
    check(right.count("Two (2) sample pendant lights") == 1, "an add whose every line is there adds nothing")
    check("already there, not repeated" in res[0]["action"], "the report says which lines were already there")
    before = [e - s for _, _, s, e in E.item_gaps(cols)]
    E.one_blank_between_items(cols, log, flags)
    after = [e - s for _, _, s, e in E.item_gaps(cols)]
    check(before == [2] and after == [1], f"two blank lines after Plumbing become one ({before} -> {after})")
    check(any("item gaps" in l for l in log), "the gap change is reported")

    with tempfile.TemporaryDirectory() as tmp:
        good = write_docx(Path(tmp) / "good.docx", cols.rebuild())
        out = []
        check(gate_inclusions.check_upgrade_items(str(good), out, "seq"), "the gate passes the edited section")
        bad_right = RIGHT[:4] + ["Sample sink to Kitchen"] + RIGHT[4:]
        bad = write_docx(Path(tmp) / "bad.docx", body_doc(LEFT, bad_right))
        out = []
        ok = gate_inclusions.check_upgrade_items(str(bad), out, "seq")
        check(not ok and "repeats" in out[0] and "2 blank lines after 'Plumbing'" in out[0],
              "the gate fails a repeated line and a double gap")
        # a blank paragraph that holds a page break is never removed: the gap
        # after Plumbing is a break and a plain blank - only the plain one goes
        cols2 = E.Columns(body_doc(LEFT, RIGHT))
        cols2.right[5] = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        flags2 = []
        E.one_blank_between_items(cols2, [], flags2)
        gaps = [e - s for _, _, s, e in E.item_gaps(cols2)]
        check(any("w:br" in p for p in cols2.right) and gaps == [1] and not flags2,
              f"a blank paragraph with a break stays, the plain one goes ({gaps})")
        cols3 = E.Columns(body_doc(LEFT, RIGHT))
        cols3.right[4] = cols3.right[5] = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        flags3 = []
        E.one_blank_between_items(cols3, [], flags3)
        check(len(flags3) == 1 and [e - s for _, _, s, e in E.item_gaps(cols3)] == [2],
              "a gap of breaks only is left and flagged")


def test_row_5_alignment():
    print("row 5: amounts lined up on their digits")
    values = {"price_excl_gst": "$499,909.09", "gst_amount": "$49,990.91", "price_incl_gst": "$549,900.00",
              "progress_1": "$54,990.00", "progress_2": "$54,990.00", "progress_3": "$137,475.00",
              "progress_4": "$137,475.00", "progress_5": "$109,980.00", "progress_6": "$54,990.00",
              "progress_total": "$549,900.00"}
    a = fill_hia.aligned_amounts(values, "NSW")
    check(a.get("gst_amount") == "$  49,990.91", f"GST pads to the 6-digit column ({a.get('gst_amount')!r})")
    check("price_excl_gst" not in a and "progress_3" not in a, "the widest amounts are typed as they are")
    big = fill_hia.aligned_amounts({"price_excl_gst": "$954,545.45", "gst_amount": "$95,454.55",
                                    "price_incl_gst": "$1,050,000.00"}, "QLD")
    check(big.get("price_excl_gst") == "$   954,545.45" and big.get("gst_amount") == "$     95,454.55",
          f"a 7-digit price: one digit and a comma more pad ({big})")
    w = [font_fit.text_width_pt(s, "Arial", 24) for s in ("$499,909.09", a["gst_amount"], "$549,900.00")]
    if all(exact for _, exact in w):
        check(max(x for x, _ in w) - min(x for x, _ in w) < 0.01, "in Arial the three print at one width")
    else:
        print("  skip Arial width check - font file not on this machine")


def test_row_11_period():
    print("row 11: QLD building period")
    bp = fill_hia.building_period
    check(bp({"storeys": 1})[0] == 210, "single storey 210 days")
    check(bp({"upgrades": {"storeys": 2}, "house_size": "291.00 m²"})[0] == 240, "double, 291 m2: 240 days")
    check(bp({"storeys": "2", "house_size": "320.10 m²"})[0] == 260, "double, 320 m2: 260 days")
    check(bp({"storeys": 2})[0] is None, "double with no house size: not guessed")
    check(bp({"storeys": 2, "house_size": "300 m²"})[0] is None, "exactly 300 m2: a person picks")
    check(bp({})[0] is None, "no storeys: not guessed")


COMPANY = "SAMPLE HOLDINGS No.2 PTY LTD ATF SAMPLE AND EXAMPLE No.2 FAMILY TRUST"


def test_company_names():
    print("rows 8-10, 12, 13, 16: a company owner")
    v = {"owner_1": COMPANY, "owners": COMPANY + " ACN: 600 000 000", "owner_2": "",
         "company_signatory": "Alex SAMPLE"}
    check(owner_names.company_name(v) == COMPANY + " ACN: 600 000 000", "a company is the entity plus its ACN")
    check(owner_names.signer_line(v) == f"Alex SAMPLE on behalf of {COMPANY} ACN: 600 000 000",
          "the signer line names the signatory and the company with its ACN")
    check(owner_names.company_name({"owner_1": "Alex SAMPLE", "owners": "Alex SAMPLE"}) is None,
          "one person is not a company")
    check(owner_names.company_name({"owner_1": "A SAMPLE", "owner_2": "B SAMPLE",
                                    "owners": "A SAMPLE & B SAMPLE"}) is None, "two people are not a company")
    check(owner_names.signer_line({**v, "company_signatory": ""}) is None, "no signatory, no signer line")

    # the inclusions' tab-stopped signature line: name at the name stop, the
    # signer's line under it, Date: on a line of its own after two tabs
    tabs = '<w:pPr><w:tabs><w:tab w:val="left" w:pos="2235"/><w:tab w:val="left" w:pos="7560"/></w:tabs></w:pPr>'
    face = '<w:rPr><w:rFonts w:ascii="Segoe UI Light" w:hAnsi="Segoe UI Light"/><w:b/></w:rPr>'
    line = (f"<w:p>{tabs}<w:r>{face}<w:t>Name of Owner 1:</w:t></w:r><w:r><w:tab/></w:r>"
            f"<w:r>{face}<w:t>{COMPANY}</w:t></w:r><w:r><w:tab/></w:r>"
            f"<w:r>{face}<w:t>Date: …….. / ……..</w:t></w:r></w:p>")
    cell = (f'<w:tbl><w:tr><w:tc><w:tcPr><w:tcW w:w="8225" w:type="dxa"/></w:tcPr>'
            f"<w:p><w:r>{face}<w:t>Name of Owner 1:</w:t></w:r><w:r>{face}"
            f'<w:t xml:space="preserve">       {COMPANY}</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    xml = (f"<w:document {W}><w:body>{line}{cell}<w:sectPr><w:pgSz w:w=\"11910\"/>"
           f'<w:pgMar w:top="0" w:right="560" w:left="460"/></w:sectPr></w:body></w:document>')
    out, notes = fill_inclusions.company_owner_lines(xml, v, 22)
    paras = [m.group(0) for m in fill_inclusions.PARA_RE.finditer(out)]
    first = paras[0]
    check(out.count(f"{COMPANY} ACN: 600 000 000") == 4, "both lines carry the ACN, with and in the signer line")
    check(first.split("<w:br/>")[0].count("<w:tab/>") == 1 and first.split("<w:br/>")[-1].count("<w:tab/>") == 2
          and "Date:" in first.split("<w:br/>")[-1], "Date: moves to its own line, two tabs to its stop")
    check("on behalf of" in paras[1] and "<w:br/>" in paras[1], "the table-cell line gets the signer line")
    sizes = [int(s) for s in __import__("re").findall(r'<w:sz w:val="(\d+)"', out)]
    check(sizes and max(sizes) <= 22 and min(sizes) >= 14, f"sizes stay between 7 and 11 pt ({sorted(set(sizes))})")
    check(len(notes) >= 3, "the report lists each line's size")
    with tempfile.TemporaryDirectory() as tmp:
        doc = write_docx(Path(tmp) / "sig.docx", out)
        rep = []
        check(gate_inclusions.check_signature_lines(str(doc), rep, "seq"),
              "the gate's signature-line check accepts the company layout")
    unchanged, n = fill_inclusions.company_owner_lines(xml, {"owner_1": "Alex SAMPLE", "owners": "Alex SAMPLE"})
    check(unchanged == xml and n == [], "an individual owner's lines are untouched")


def test_font_fit():
    print("font_fit: the size that keeps a line on one line")
    hp, fits, exact = font_fit.fit_size("A" * 40, "Arial", 24, 20 * 400)
    check(fits and hp <= 24, f"a 40-letter line fits 400 pt at {hp / 2} pt")
    hp, fits, _ = font_fit.fit_size("A" * 400, "Arial", 24, 20 * 100)
    check(not fits and hp == 14, "a line that cannot fit stops at 7 pt and says so")
    w, exact = font_fit.text_width_pt("abc", "No Such Font", 20)
    check(not exact and w > 0, "a missing font is estimated, and marked so")
    check(font_fit.container_width('<w:tc><w:tcPr><w:tcW w:w="5000" w:type="dxa"/></w:tcPr><w:p>', 40) == 4770,
          "a table cell's width less its padding")


def test_row_7_brackets():
    print("row 7: the house number in brackets, the same in every document")
    import street_format as S
    b = S.bracket_street
    check(b("3 Sample Road")[0] == "(3) Sample Road", "a bare number is bracketed")
    check(b("(3) Sample Road")[0] == "(3) Sample Road", "a bracketed number is left")
    check(b("12-14 Sample Road")[0] == "(12-14) Sample Road" and b("3A Sample Road")[0] == "(3A) Sample Road",
          "a range and a lettered number keep their form")
    check(b("Sample Road")[0] == "Sample Road" and b("Road 28")[0] == "Road 28", "no leading number, no brackets")
    s, note = b("29 Sample & 25 Example Street")
    check(s == "29 Sample & 25 Example Street" and note, "a two-number parent address is left and reported")
    check(S.bracket_site("209, 3 Sample Road, SAMPLEVILLE NSW 2000") == "209, (3) Sample Road, SAMPLEVILLE NSW 2000",
          "the site address brackets the number after the lot")
    v, _ = S.bracket_job({"street": "3 Sample Road", "land_street": "3 Sample Road",
                          "site_hia": "3 Sample Road, SAMPLEVILLE NSW 2000",
                          "site_address": "209, 3 Sample Road, SAMPLEVILLE NSW 2000"})
    check(v["street"] == v["land_street"] == "(3) Sample Road" and v["site_hia"].startswith("(3) ")
          and v["site_address"] == "209, (3) Sample Road, SAMPLEVILLE NSW 2000",
          "every document's street key reads alike")
    check(S.applies("NSW") and S.applies("sydney") and S.applies("gunnedah"), "NSW documents bracket")


def plan_pdf(path, *lines):
    """A minimal PDF whose one Flate content stream shows the given text lines."""
    import zlib
    body = b"BT " + b" ".join(b"(" + s.encode("latin-1") + b") Tj" for s in lines) + b" ET"
    blob = zlib.compress(body)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"%%PDF-1.4\n1 0 obj << /Length %d /Filter /FlateDecode >>\nstream\n" % len(blob)
                           + blob + b"\nendstream\nendobj\n%%EOF\n")
    return path


def test_row_7_parent_address():
    print("row 7 / CD-2.4: a parent address gives way to the lot's own street from the plans")
    import street_format as S
    import draft_contract as D
    f = S.lot_street_from_plan_text
    check(f("Cossies 170 - Karri facade Lot  5  Example  Street  Sampleville NSW Floor Plan", "5") == "Example Street",
          "the title block's street is found, spacing ignored")
    check(f("Lot 5 Example St Sampleville", "5") == "Example Street", "an abbreviated type is written out")
    check(f("Lot 5 Example Street ... Lot 5 Other Road", "5") is None, "plans naming two streets give none")
    check(f("Lot 15 Example Street", "5") is None and f("Lot 5 - Cossies 170", "5") is None,
          "another lot, or no street after the lot, gives none")
    check(f("Lot 5 29 Example Street", "5") is None, "a numbered street is not the lot's")
    parent = "29 Sample & 25 Example Street"
    check(f("Lot 5 New Road ... Lot 5 Example Street Sampleville", "5", parent) == "Example Street",
          "with the request's address: a placeholder New Road on the plans is ignored")
    check(f("Lot 5 Other Court Sampleville", "5", parent) is None,
          "with the request's address: a street it does not name is never taken (a suburb, a neighbour)")
    check(f("Lot 5 Sample Road ... Lot 5 Example Street", "5", parent) is None,
          "plans naming both of the request's streets give none")
    check(S.parent_street_names(parent) == {"SAMPLE", "EXAMPLE"}, "the parent address's street names")
    check(S.is_parent_address("29 Sample & 25 Example Street") and not S.is_parent_address("(3) Sample Road"),
          "a two-number street is a parent address")
    job = {"lot_no": "5", "street": "29 Sample & 25 Example Street", "land_street": "29 Sample & 25 Example Street",
           "site_address": "5, 29 Sample & 25 Example Street, SAMPLEVILLE NSW 2000",
           "site_hia": "29 Sample & 25 Example Street, SAMPLEVILLE NSW 2000", "estate": ""}
    v, note = S.use_lot_street(job, "Example Street", "PLANS.pdf")
    check(v["street"] == v["land_street"] == "Example Street"
          and v["site_address"] == "5, Example Street, SAMPLEVILLE NSW 2000"
          and v["site_hia"] == "Example Street, SAMPLEVILLE NSW 2000" and v["estate"] == "" and note,
          "every street and site key takes the lot's street, ESTATE untouched, with a note")
    v2, _ = S.bracket_job(v)
    check(v2["street"] == "Example Street", "the bracket step leaves a numberless street alone")
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        work, jobdir = t / "work", t / "CONTRACT DOCUMENTATION"
        work.mkdir(); jobdir.mkdir()
        jp = work / "job.json"
        import json
        jp.write_text(json.dumps(job), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            p0, v0 = D.resolve_lot_street(job, jp, work, jobdir)
        check(p0 == jp and v0 == job and "no plans" in buf.getvalue(), "no plans: as given, flagged")
        plan_pdf(jobdir / "PLANS_LOT 5_SAMPLEVILLE.pdf", "Lot 5 Example Street Sampleville", "Floor Plan")
        plan_pdf(jobdir / "Sales Advice.pdf", "Lot 5 Wrong Road")
        buf = io.StringIO()
        with redirect_stdout(buf):
            p1, v1 = D.resolve_lot_street(job, jp, work, jobdir)
        check(p1 != jp and p1.parent == jp.parent and v1["street"] == "Example Street" and "confirm" in buf.getvalue()
              and json.loads(p1.read_text(encoding="utf-8"))["site_address"].startswith("5, Example Street,")
              and json.loads(jp.read_text(encoding="utf-8"))["street"] == job["street"],
              "plans in the job folder: the lot's street in a resolved copy, the job JSON untouched")
        other = t / "other-workdir"; other.mkdir()
        with redirect_stdout(io.StringIO()):
            p3, _ = D.resolve_lot_street(job, jp, other, jobdir)
        check(p3.parent == jp.parent, "another --workdir: the resolved copy still sits beside the job JSON "
              "and its request text")
        plan_pdf(work / "attachments" / "Contract Plans.pdf", "Lot 5 Sample Road")
        buf = io.StringIO()
        with redirect_stdout(buf):
            p2, v2 = D.resolve_lot_street(job, jp, work, jobdir)
        check(p2 == jp and v2 == job and "none puts lot 5" in buf.getvalue(),
              "plans that disagree: as given, flagged")
        single = dict(job, street="3 Sample Road")
        check(D.resolve_lot_street(single, jp, work, jobdir) == (jp, single), "a normal street is not touched")


def test_row_1_email_name():
    print("row 1: the request email named as Outlook saves it")
    n = msg_extract.outlook_file_name
    check(n("Request Contract : Lot 4153 Sample Park ") == "Request Contract _ Lot 4153 Sample Park .msg",
          "a colon becomes _ and the trailing space stays")
    check(n("New Build Contract Order:  Lot 209, 3 SAMPLE ROAD, SAMPLEVILLE NSW 2000") ==
          "New Build Contract Order_  Lot 209_ 3 SAMPLE ROAD_ SAMPLEVILLE NSW 2000.msg", "commas become _")
    check(n("") == "Contract request.msg", "no subject: a plain name")
    check(n('a/b\\c*d?e"f<g>h|i') == "a_b_c_d_e_f_g_h_i.msg", "characters Windows refuses become _")
    import draft_contract as D
    with tempfile.TemporaryDirectory() as t:
        work, jobdir = Path(t) / "work", Path(t) / "CONTRACT DOCUMENTATION"
        work.mkdir(); jobdir.mkdir()
        with redirect_stdout(io.StringIO()):
            none = D.save_request_email(work, jobdir)
            (jobdir / "Request _ Lot 1 Sample Road.msg").write_bytes(b"x")
            held = D.save_request_email(work, jobdir)
            (work / "a.msg").write_bytes(b"x"); (work / "b.msg").write_bytes(b"x")
            two = D.save_request_email(work, jobdir)
        check("NOT saved" in none and "no .msg" in none, "no request email anywhere: reported for a person")
        check("already in the job folder" in held and "Request _ Lot 1" in held,
              "an email dragged straight into the job folder: not reported missing")
        check("NOT saved" in two and "2 .msg" in two and len(list(jobdir.glob("*.msg"))) == 1,
              "two emails in the workdir: nothing copied, reported")


def main():
    for t in (test_rows_14_15, test_row_5_alignment, test_row_11_period, test_company_names, test_font_fit,
              test_row_7_brackets, test_row_7_parent_address, test_row_1_email_name):
        buf = io.StringIO()
        with redirect_stdout(buf):
            t()
        print(buf.getvalue(), end="")
    print("PASS" if not FAILS else f"FAIL - {len(FAILS)} check(s): {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
