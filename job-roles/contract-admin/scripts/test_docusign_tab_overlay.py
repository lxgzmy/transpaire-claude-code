r"""Self-test for docusign_tab_overlay.py's pure functions. Stdlib only, no PDF library.

    python test_docusign_tab_overlay.py

Synthetic DocuSign JSON only: no names, emails or ids from any account.
Checks the kind match by name, the geometry extract (and that nothing naming
a person comes through), tabs past a document's last page, and the refusal to
write anywhere but the checkout's runtime folder. Drawing the pages needs
pypdfium2 and is not covered here.
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docusign_tab_overlay as ov  # noqa: E402

DOCUMENTS = {"documents": [
    {"documentId": "1", "name": "BUILD CONTRACT _LOT 1_SAMPLEVILLE_EXAMPLE.pdf", "pages": "37"},
    {"documentId": "86000001", "name": "INCLUSIONS_LOT 1_SAMPLEVILLE_EXAMPLE.pdf", "pages": "15"},
    {"documentId": "3", "name": "PLANS_LOT 1_SAMPLEVILLE_EXAMPLE.pdf", "pages": "4"},
    {"documentId": "9", "name": "Summary", "type": "summary"},
]}
RECIPIENTS = {"recipients": {
    "signers": [
        {"roleName": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com", "tabs": {
            "signHereTabs": [{"documentId": "1", "pageNumber": "13", "xPosition": "147", "yPosition": "268",
                              "tabLabel": "Signature 1", "name": "SignHere"}],
            "initialHereTabs": [{"documentId": "86000001", "pageNumber": "12", "xPosition": "356",
                                 "yPosition": "795"},
                                {"documentId": "86000001", "pageNumber": "15", "xPosition": "356",
                                 "yPosition": "795"}],
            "dateSignedTabs": [{"documentId": "3", "pageNumber": "4", "xPosition": "473.5",
                                "yPosition": "494", "value": "01/01/2026"}]}},
        {"roleName": "Builder", "name": "Pat BUILDER", "email": "pat@example.com", "tabs": {
            "signHereTabs": [{"documentId": "1", "pageNumber": "13", "xPosition": "147",
                              "yPosition": "451"}]}},
    ],
    "carbonCopies": [], "recipientCount": "2"}}


def check_kinds():
    assert ov.kind_of("BUILD CONTRACT _LOT 1_X.pdf") == "BUILD CONTRACT"
    assert ov.kind_of("EXECUTED-PRELIMINARY AGREEMENT.pdf") == "PRELIMINARY AGREEMENT"
    assert ov.kind_of("Summary") is None
    assert ov.kinds_by_document_id(DOCUMENTS["documents"]) == {
        "1": "BUILD CONTRACT", "86000001": "INCLUSIONS", "3": "PLANS"}
    # a draft's list is "envelopeDocuments"
    assert ov.kinds_by_document_id(ov._documents({"envelopeDocuments": DOCUMENTS["documents"]}))["3"] == "PLANS"
    print("  kinds: ok")


def check_geometry():
    tabs = ov.geometry(RECIPIENTS, DOCUMENTS)
    assert len(tabs) == 5, tabs
    assert {"kind": "PLANS", "page": 4, "type": "dateSigned", "role": "Buyer", "x": 473, "y": 494} in tabs
    for t in tabs:
        assert set(t) == {"kind", "page", "type", "role", "x", "y"}, t
    dumped = json.dumps(tabs)
    for secret in ("Alex", "alex@", "Pat BUILDER", "Signature 1", "01/01/2026"):
        assert secret not in dumped, secret
    # the bare recipients object works too
    assert ov.geometry(RECIPIENTS["recipients"], DOCUMENTS["documents"]) == tabs
    print("  geometry: ok")


def check_past_end():
    tabs = ov.geometry(RECIPIENTS, DOCUMENTS)
    docs = ov.by_document(tabs, {"BUILD CONTRACT": 37, "INCLUSIONS": 13, "PLANS": 4})
    inc = docs["INCLUSIONS"]
    assert [t["page"] for t in inc["past_end"]] == [15], inc
    assert list(inc["on_page"]) == [12]
    assert len(docs["BUILD CONTRACT"]["on_page"][13]) == 2
    lines = ov.summary_lines(docs, {})
    assert any(l.strip().startswith("MISSING p15") for l in lines), lines
    assert lines[0].startswith("BUILD CONTRACT: 2 tabs, PDF pages: 37"), lines
    assert ov.box({"type": "signHere", "x": 10, "y": 20}) == (10, 20, 100, 56)
    print("  past the last page: ok")


def check_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ov.check_out_dir(tmp)
        except ov.Refusal as e:
            assert "runtime" in str(e)
        else:
            raise AssertionError("an output folder outside runtime was accepted")
        try:
            ov.check_out_dir(ov.RUNTIME / ".." / "docs")
        except ov.Refusal:
            pass
        else:
            raise AssertionError("a path that climbs out of runtime was accepted")
    assert ov.check_out_dir(ov.RUNTIME / "docusign-sandbox" / "evidence" / "x").name == "x"
    assert ov.parse_pdf_args(["inclusions=/tmp/a.pdf"]) == {"INCLUSIONS": Path("/tmp/a.pdf")}
    for bad in (["CONTRACT=/tmp/a.pdf"], ["PLANS"], ["PLANS=/a.pdf", "plans=/b.pdf"]):
        try:
            ov.parse_pdf_args(bad)
        except ov.Refusal:
            pass
        else:
            raise AssertionError(f"accepted {bad}")
    assert ov.main(["--recipients", "x.json", "--documents", "y.json", "--out", "/tmp/elsewhere"]) == 2
    print("  refusals: ok")


if __name__ == "__main__":
    check_kinds()
    check_geometry()
    check_past_end()
    check_refusals()
    print("docusign_tab_overlay self-test: all ok")
