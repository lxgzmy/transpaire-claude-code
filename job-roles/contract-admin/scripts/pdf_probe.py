"""Report whether a PDF is a fillable form and who produced it. Stdlib only.

Usage: python pdf_probe.py <file.pdf> [...]

Scans for /AcroForm, /XFA and field markers, and pulls the Producer / Creator
strings. Enough to tell a form-fillable contract apart from a flattened export,
without needing a PDF library installed.

Since 24 Sep 2026 the scan also looks inside decompressed object streams
(`/Type /ObjStm`): modern producers pack the field dictionaries there, so a
raw-bytes scan reported the marketers' filled EOI form as "flattened" with 0
text fields. `pdf_fields.py` reads the values out of such a form.
"""
import re
import sys
import zlib


def _with_object_streams(data):
    """Raw bytes plus every decompressed Flate stream, so packed objects are scanned too."""
    parts = [data]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            parts.append(zlib.decompress(m.group(1)))
        except zlib.error:
            continue
    return b"\n".join(parts)


def probe(path):
    with open(path, "rb") as f:
        raw = f.read()
    data = _with_object_streams(raw)

    print(f"=== {path.rsplit(chr(92), 1)[-1]}  ({len(raw)/1024:,.0f} KB)")
    print(f"    version   : {raw[:8].decode('latin-1', 'replace').strip()}")

    for key in ("Producer", "Creator"):
        m = re.search(rb"/" + key.encode() + rb"\s*\(((?:[^()\\]|\\.)*)\)", data)
        val = m.group(1).decode("latin-1", "replace") if m else "-"
        # UTF-16 hex strings show up on some producers
        if not m:
            m = re.search(rb"/" + key.encode() + rb"\s*<([0-9A-Fa-f]+)>", data)
            if m:
                raw = bytes.fromhex(m.group(1).decode())
                val = raw.decode("utf-16-be", "replace").lstrip("﻿")
        print(f"    {key:<10}: {val}")

    acroform = b"/AcroForm" in data
    xfa = b"/XFA" in data
    widgets = len(re.findall(rb"/Subtype\s*/Widget", data))
    textfields = len(re.findall(rb"/FT\s*/Tx", data))
    sigs = len(re.findall(rb"/FT\s*/Sig", data))
    objstm = len(re.findall(rb"/Type\s*/ObjStm", raw))
    filled = len(re.findall(rb"/FT\s*/Tx(?:(?!endobj|>>\s*endobj).){0,400}?/V\s*[(<]", data, re.S))
    print(f"    AcroForm  : {acroform}   XFA: {xfa}   object streams: {objstm}")
    print(f"    widgets   : {widgets}   text fields: {textfields}   sig fields: {sigs}")
    print(f"    pages     : {len(re.findall(rb'/Type\s*/Page[^s]', data))}")
    if textfields and filled:
        print(f"    values    : {filled} text field(s) carry a value - read them with pdf_fields.py")
    verdict = (
        "FILLABLE FORM" if textfields else
        "flattened / no fillable text fields"
    )
    print(f"    verdict   : {verdict}")
    print()


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            probe(p)
        except Exception as exc:  # keep going across a batch
            print(f"=== {p}\n    ERROR: {exc}\n")
