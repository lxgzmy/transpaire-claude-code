r"""Read the filled-in values of a PDF form (AcroForm). Stdlib only.

    python pdf_fields.py <file.pdf>                 # name -> value, final revision
    python pdf_fields.py <file.pdf> --json          # same as JSON
    python pdf_fields.py <file.pdf> --history       # every revision, oldest first

Why this exists (24 Sep 2026, job 26057): the marketers' EOI is an online form
that arrives as a PDF whose typed values live in AcroForm field dictionaries
(`/T name /V value`), not in the page text. Every text route on this server
misses them - `pdf_text.py` reads page content streams (the form's own
appearance streams also use hex strings), Word's PDF reflow (`pdf_to_docx.ps1`)
re-typesets the blank form, and there is no rasteriser for an eye read. So a
perfectly digital EOI looked "unreadable" and a person typed the names in.

Two PDF details matter and are handled here:

  * Object streams. Modern producers pack the field dictionaries into
    compressed `/Type /ObjStm` streams, so a raw-bytes scan (`pdf_probe.py`
    before 24 Sep 2026) sees no `/FT`, no `/Widget`, no values. Every Flate
    stream is decompressed and its objects are read.
  * Incremental updates. A re-used or re-submitted form appends a new
    revision; the previous values are still in the file. Objects are keyed by
    object number and the LAST definition in file order wins, which is the
    current revision. `--history` shows the earlier ones - useful for spotting
    that a marketer re-used another buyer's form, which happens.

Values are the client's data: keep them in the job's runtime workdir on Z:,
never in the repo. Nothing here writes; it prints.
"""
import argparse
import json
import re
import sys
import zlib
from pathlib import Path

LIT = rb"\((?:[^()\\]|\\.)*\)"
HEX = rb"<[0-9A-Fa-f\s]*>"
STRING = rb"(?:" + LIT + rb"|" + HEX + rb")"
OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b(.*?)endobj", re.S)
STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
           b"(": b"(", b")": b")", b"\\": b"\\"}


def pdf_string(tok):
    """Decode a PDF literal or hex string token to text (PDFDocEncoding ~ latin-1, or UTF-16BE with BOM)."""
    if tok.startswith(b"<"):
        h = re.sub(rb"[^0-9A-Fa-f]", b"", tok[1:-1])
        if len(h) % 2:
            h += b"0"
        raw = bytes.fromhex(h.decode("ascii"))
    else:
        body = tok[1:-1]
        out = bytearray()
        i = 0
        while i < len(body):
            c = body[i:i + 1]
            if c == b"\\" and i + 1 < len(body):
                nxt = body[i + 1:i + 2]
                if nxt in ESCAPES:
                    out += ESCAPES[nxt]
                    i += 2
                    continue
                if nxt.isdigit():
                    oct_digits = re.match(rb"[0-7]{1,3}", body[i + 1:i + 4]).group(0)
                    out.append(int(oct_digits, 8) & 0xFF)
                    i += 1 + len(oct_digits)
                    continue
                if nxt in (b"\r", b"\n"):  # line continuation
                    i += 2
                    continue
                out += nxt
                i += 2
                continue
            out += c
            i += 1
        raw = bytes(out)
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be", "replace")
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le", "replace")
    return raw.decode("latin-1", "replace")


def _objects_in_objstm(content, first=None):
    """Yield (objnum, bytes) for each object packed in a decoded object stream.

    The stream starts with N pairs "objnum offset"; the objects follow at
    /First bytes in. Without the /First value the header is read greedily -
    number pairs until the first token that is not a number - which is where
    the first object's dictionary begins.
    """
    pairs = []
    pos = 0
    for mm in re.finditer(rb"\s*(\d+)\s+(\d+)", content):
        if mm.start() != pos:
            break
        pairs.append((int(mm.group(1)), int(mm.group(2))))
        pos = mm.end()
    if not pairs:
        return
    body_start = first if first is not None else pos
    while first is None and body_start < len(content) and content[body_start:body_start + 1].isspace():
        body_start += 1
    for i, (num, off) in enumerate(pairs):
        start = body_start + off
        end = body_start + pairs[i + 1][1] if i + 1 < len(pairs) else len(content)
        yield num, content[start:end]


def objects(data):
    """Yield (objnum, body, order) for every object definition, file order, including inside object streams."""
    order = 0
    for m in OBJ_RE.finditer(data):
        num = int(m.group(1))
        body = m.group(3)
        yield num, body, order
        order += 1
        sm = STREAM_RE.search(body)
        if sm and b"/ObjStm" in body:
            try:
                decoded = zlib.decompress(sm.group(1))
            except zlib.error:
                continue
            fm = re.search(rb"/First\s+(\d+)", body[:sm.start()])
            first = int(fm.group(1)) if fm else None
            for inner_num, inner_body in _objects_in_objstm(decoded, first):
                yield inner_num, inner_body, order
                order += 1


def dict_entry(body, key):
    """Return the string token for /key in a dictionary body, or None."""
    m = re.search(rb"/" + key + rb"\s*(" + STRING + rb")", body)
    return m.group(1) if m else None


def field_records(data):
    """All field-like objects (have /T), file order: [(objnum, name, value or None)]."""
    recs = []
    for num, body, order in objects(data):
        if b"/T" not in body:
            continue
        # /T must be a direct string on this dictionary (not /Type, /TU, /TM ...)
        tm = re.search(rb"/T\s*(" + STRING + rb")", body)
        if not tm:
            continue
        name = pdf_string(tm.group(1))
        vtok = dict_entry(body, b"V")
        value = pdf_string(vtok) if vtok is not None else None
        if vtok is None:
            # /V may be a name (checkbox state): /V /Yes
            nm = re.search(rb"/V\s*/([^\s/>\[\]]+)", body)
            if nm:
                value = "/" + nm.group(1).decode("latin-1", "replace")
        recs.append((num, name, value, order))
    return recs


def fields_from_bytes(data, history=False):
    """Final-revision {name: value}. With history=True, a list of revisions oldest first."""
    recs = field_records(data)
    if not history:
        latest = {}
        for num, name, value, order in recs:
            latest[num] = (name, value)   # last definition in file order wins
        out = {}
        for num in sorted(latest, key=lambda n: n):
            name, value = latest[num]
            if value is None and name in out:
                continue
            out[name] = value
        return out
    # history: group by pass over object numbers - a new revision restarts the set
    revisions, seen, current = [], set(), {}
    for num, name, value, order in recs:
        if num in seen:
            revisions.append(current)
            seen, current = set(), {}
        seen.add(num)
        current[name] = value
    if current:
        revisions.append(current)
    return revisions


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    ap.add_argument("--history", action="store_true", help="show every revision, oldest first")
    args = ap.parse_args()

    data = Path(args.pdf).read_bytes()
    if args.history:
        revs = fields_from_bytes(data, history=True)
        if args.json:
            print(json.dumps(revs, indent=2, ensure_ascii=False))
            return
        for i, rev in enumerate(revs, 1):
            tag = "CURRENT" if i == len(revs) else "superseded"
            print(f"--- revision {i} of {len(revs)} ({tag}) ---")
            for k, v in rev.items():
                print(f"  {k:<28} {'' if v is None else v}")
        return

    fields = fields_from_bytes(data)
    if args.json:
        print(json.dumps(fields, indent=2, ensure_ascii=False))
        return
    print(f"{Path(args.pdf).name}: {len(fields)} form fields (final revision)")
    if not fields:
        print("  no AcroForm fields found - not a filled form; try pdf_text.py, pdf_images.py or Word reflow")
    for k, v in fields.items():
        shown = "" if v is None else v.strip()
        print(f"  {k:<28} {shown}")


# This console is cp1252; names and addresses carry accents.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
