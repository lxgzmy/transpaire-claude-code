r"""Self-test for pdf_fields.py (24 Sep 2026).

    python test_pdf_fields.py

Synthetic values only. Builds two PDFs in memory - no client data, no files:

  1. a plain AcroForm with the field dictionaries as top-level objects, literal
     and UTF-16 hex string values, one octal escape, one checkbox name value;
  2. the same fields packed into a compressed /ObjStm object stream (the way
     the marketers' online EOI form arrives) plus an incremental update that
     re-defines two fields with new values - the CURRENT revision must win and
     --history must still show the old one.

Also checks that pdf_text.py's hex-string support decodes a <hex> Tj and that
pdf_probe.py's scan sees text fields packed in an object stream.
"""
import io
import re
import sys
import zlib
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pdf_fields  # noqa: E402
import pdf_probe  # noqa: E402
import pdf_text  # noqa: E402


def obj(num, body):
    return f"{num} 0 obj\n".encode() + body + b"\nendobj\n"


def build_plain():
    fields = [
        obj(10, b"<< /FT /Tx /T (Buyer-1-fn) /V (Alex) >>"),
        obj(11, b"<< /FT /Tx /T (Buyer-1-ln) /V <FEFF0053004D0049005400480045> >>"),  # UTF-16BE 'SMITHE'
        obj(12, b"<< /FT /Tx /T (Postcode) /V (2\\0611) >>"),  # octal \061 = '1' -> '211'
        obj(13, b"<< /FT /Btn /T (Dual-Key) /V /Yes >>"),
        obj(14, b"<< /FT /Tx /T (Empty) >>"),
    ]
    return b"%PDF-1.7\n" + b"".join(fields) + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"


def objstm(num, entries):
    """entries: list of (objnum, dict bytes). Returns a compressed object stream object."""
    header = b""
    body = b""
    for n, d in entries:
        header += f"{n} {len(body)} ".encode()
        body += d + b"\n"
    content = header + body
    packed = zlib.compress(content)
    return (f"{num} 0 obj\n<< /Type /ObjStm /N {len(entries)} /First {len(header)} "
            f"/Length {len(packed)} /Filter /FlateDecode >>\nstream\n").encode() + packed + b"\nendstream\nendobj\n"


def build_packed():
    rev1 = objstm(50, [
        (10, b"<< /FT /Tx /T (Buyer-1-fn) /V (Christopher) >>"),
        (11, b"<< /FT /Tx /T (Buyer-1-ln) /V (Newman) >>"),
        (12, b"<< /FT /Tx /T (Suburb) /V (Diggers Rest) >>"),
    ])
    # incremental update: a later object stream re-defines 10 and 11
    rev2 = objstm(60, [
        (10, b"<< /FT /Tx /T (Buyer-1-fn) /V (Ivy) >>"),
        (11, b"<< /FT /Tx /T (Buyer-1-ln) /V (Nguyen) >>"),
    ])
    return b"%PDF-1.7\n" + rev1 + b"trailer\n<< /Root 1 0 R >>\n%%EOF\n" + rev2 + b"trailer\n<< /Root 1 0 R /Prev 9 >>\n%%EOF\n"


def build_hex_text_pdf():
    content = b"BT /F1 12 Tf 10 10 Td <48656C6C6F20776F726C64> Tj ET"  # 'Hello world'
    packed = zlib.compress(content)
    return (b"%PDF-1.7\n" + obj(20, f"<< /Length {len(packed)} /Filter /FlateDecode >>\nstream\n".encode()
            + packed + b"\nendstream") + b"%%EOF\n")


def main():
    fails = []

    def check(cond, msg):
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    print("1. plain AcroForm")
    f = pdf_fields.fields_from_bytes(build_plain())
    check(f.get("Buyer-1-fn") == "Alex", "literal value")
    check(f.get("Buyer-1-ln") == "SMITHE", "UTF-16BE hex value")
    check(f.get("Postcode") == "211", "octal escape in literal")
    check(f.get("Dual-Key") == "/Yes", "checkbox name value")
    check("Empty" in f and f["Empty"] is None, "field with no value is listed as None")

    print("2. object streams + incremental update")
    data = build_packed()
    f = pdf_fields.fields_from_bytes(data)
    check(f.get("Buyer-1-fn") == "Ivy" and f.get("Buyer-1-ln") == "Nguyen", "current revision wins")
    check(f.get("Suburb") == "Diggers Rest", "field untouched by the update is kept")
    hist = pdf_fields.fields_from_bytes(data, history=True)
    check(len(hist) == 2, f"two revisions in history (got {len(hist)})")
    check(hist[0].get("Buyer-1-fn") == "Christopher", "superseded value visible in history")

    print("3. pdf_probe sees fields inside an object stream")
    buf = io.StringIO()
    tmp = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_test_pdf_fields.pdf"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)
    try:
        with redirect_stdout(buf):
            pdf_probe.probe(str(tmp))
        report = buf.getvalue()
        check("text fields: 5" in report, "text fields counted through the object streams")
        check("FILLABLE FORM" in report, "verdict is FILLABLE FORM")
        check("pdf_fields.py" in report, "probe points at pdf_fields.py when values are present")
        tmp.write_bytes(build_hex_text_pdf())
        pieces = pdf_text.text_of(str(tmp))
        check(pieces == ["Hello world"], f"pdf_text decodes a <hex> Tj (got {pieces})")
    finally:
        tmp.unlink(missing_ok=True)

    print()
    if fails:
        print(f"FAILED: {len(fails)}")
        for m in fails:
            print("  -", m)
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
