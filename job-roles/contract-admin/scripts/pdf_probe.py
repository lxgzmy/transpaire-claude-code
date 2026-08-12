"""Report whether a PDF is a fillable form and who produced it. Stdlib only.

Usage: python pdf_probe.py <file.pdf> [...]

Scans the raw bytes for /AcroForm, /XFA and field markers, and pulls the
Producer / Creator strings. Enough to tell a form-fillable contract apart from a
flattened export, without needing a PDF library installed.
"""
import re
import sys


def probe(path):
    with open(path, "rb") as f:
        data = f.read()

    print(f"=== {path.rsplit(chr(92), 1)[-1]}  ({len(data)/1024:,.0f} KB)")
    print(f"    version   : {data[:8].decode('latin-1', 'replace').strip()}")

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
    print(f"    AcroForm  : {acroform}   XFA: {xfa}")
    print(f"    widgets   : {widgets}   text fields: {textfields}   sig fields: {sigs}")
    print(f"    pages     : {len(re.findall(rb'/Type\s*/Page[^s]', data))}")
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
