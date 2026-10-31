"""Check the address and owners boxes and the blank signature line, on synthetic XML.

    python test_site_box.py

The shapes are the live blanks' (31 Oct 2026, the job 26059 follow-up):

  blank 1 (Transpire)  empty owners box, "located at;", then an empty address
                       box written <w:p/>
  blanks 2, 3          the same with a "Lot " run in the address box
  Owner Occupier       page 15 as blank 1, then a colour-selections page whose
                       address box floats in the sentence's own paragraph,
                       followed by empty colour tick boxes

Each box is Word's pair of copies (mc:Choice + mc:Fallback). Asserts the
address is typed into its box as "Lot <address>" in both copies and nowhere
else, each owners box takes the owners and no other box does, an empty
"Name of Owner 2:" line with no dotted line gets two tabs, and that
gate_inclusions.py fails the shapes the old filler produced. Exit 0 = pass.
"""
import os
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(os.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))
import fill_inclusions as fi  # noqa: E402
import gate_inclusions as gi  # noqa: E402

OUT = HERE.parents[2] / "runtime" / "contract-admin" / "reports" / "_test_site_box"
ADDRESS = "9101, Sample Road (Sample Estate), SAMPLETOWN QLD 4000"
JOB = {"owners": "Alex SAMPLE & Sam SAMPLE", "site_address": ADDRESS}
HEADING = "ACKNOWLEDGEMENTS &amp; SIGNATURE"
SENTENCE = f"<w:r><w:t>{fi.SITE_ANCHOR}</w:t></w:r>"


def box(inner):
    return ('<w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wps:txbx>'
            f"<w:txbxContent>{inner}</w:txbxContent></wps:txbx></w:drawing></mc:Choice>"
            f"<mc:Fallback><w:pict><v:textbox><w:txbxContent>{inner}</w:txbxContent></v:textbox>"
            "</w:pict></mc:Fallback></mc:AlternateContent></w:r>")


def para(*runs):
    return "<w:p>" + "".join(runs) + "</w:p>"


def words(text):
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


EMPTY = "<w:p><w:pPr></w:pPr></w:p>"
PAGE15 = para(words(HEADING)) + para(box(EMPTY)) + para(words("I/ We")) + para(SENTENCE)
SHAPES = {
    "blank 1": PAGE15 + para(box("<w:p/>")),
    "blank 3": PAGE15 + para(box(para(words("Lot ")))),
    "owner occupier": PAGE15 + para(box(para(words("Lot ")))) + para(words("COLOUR SELECTIONS"))
    + para(words(HEADING)) + para(box(EMPTY)) + para(words("I/We")) + para(box(EMPTY), SENTENCE)
    + para(words("Have reviewed all colour selections.")) + para(box(EMPTY)),
}
LEGACY_INLINE = PAGE15.replace(SENTENCE, SENTENCE + words(f" Lot {ADDRESS}") + words(f"Lot {ADDRESS}")) \
    + para(box("<w:p/>"))

BLANK_OWNER_2 = ('<w:p><w:pPr></w:pPr>' + words("Name of Owner 2:") + words(" " * 20)
                 + "<w:r><w:tab/></w:r>" * 8 + words("Date:") + words(" …….. / …….. / ……..")
                 + "</w:p>")
DOTTED_OWNER_2 = BLANK_OWNER_2.replace(words(" " * 20), words(" " + "…" * 34))


def body(xml):
    return f'<w:document xmlns:w="w" xmlns:mc="mc"><w:body>{xml}</w:body></w:document>'


def docx(name, xml):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", body(xml))
    return str(path)


def box_texts(xml):
    return [fi.run_text(m.group(0)).strip() for m in fi.TXBX_RE.finditer(xml)]


def main():
    failures = []

    def check(ok, what):
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    for name, xml in SHAPES.items():
        report = []
        out = fi.fill(xml, JOB, report, fi.FAMILIES["seq"])
        boxes = box_texts(out)
        n_sentences = out.count(fi.SITE_ANCHOR)
        want = [JOB["owners"]] * 2 + [f"Lot {ADDRESS}"] * 2
        want = want * n_sentences + ([""] * 2 if name == "owner occupier" else [])
        check(boxes == want, f"{name}: owners then address in both copies of each box, tick boxes empty {boxes}")
        check(all(re.search(re.escape(fi.SITE_ANCHOR) + r"</w:t></w:r></w:p>", out[m.start():])
                  for m in re.finditer(re.escape(fi.SITE_ANCHOR), out)),
              f"{name}: nothing typed after \"located at;\"")
        lines = []
        check(gi.check_site_box(docx(name.replace(" ", "_"), out), lines), f"{name}: gate passes - {lines[-1]}")

    lines = []
    check(not gi.check_site_box(docx("legacy_inline", LEGACY_INLINE), lines),
          f"old filler's doubled inline address fails the gate - {lines[-1]}")

    report = []
    out = fi.fill(PAGE15 + para(words("Other words")) + para(box("<w:p/>")), JOB, report, fi.FAMILIES["seq"])
    site = next(e for e in report if e["key"] == "site_address")
    check(site["hits"] == 0 and "why" in site and box_texts(out)[-2:] == ["", ""],
          "a box past other text is not taken for the address box, and the miss is reported")

    for name, line, tabs in (("no dotted line", BLANK_OWNER_2, 2), ("dotted line", DOTTED_OWNER_2, 1)):
        out, rebuilt = fi.signature_tabs(line, {}, fi.FAMILIES["seq"])
        check(rebuilt == 1 and out.count("<w:tab/>") == tabs,
              f"empty Name of Owner 2: with {name} gets {tabs} tab(s) before Date: (got {out.count('<w:tab/>')})")
        lines = []
        check(gi.check_signature_lines(docx(f"sig_{tabs}", out), lines, "seq"), f"gate passes it - {lines[-1]}")
    one_tab = BLANK_OWNER_2.replace("<w:r><w:tab/></w:r>" * 8, "<w:r><w:tab/></w:r>")
    one_tab = one_tab.replace("<w:pPr></w:pPr>", "<w:pPr>" + fi.tab_stop_xml(2235, 7560) + "</w:pPr>")
    lines = []
    check(not gi.check_signature_lines(docx("sig_old", one_tab.replace(words(" " * 20), "")), lines, "seq"),
          f"one tab on a line with no dotted line fails the gate - {lines[-1]}")

    print(f"\n{'PASS' if not failures else 'FAIL'} - {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
