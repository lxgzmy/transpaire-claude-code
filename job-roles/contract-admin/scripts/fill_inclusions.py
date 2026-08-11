"""Fill a blank Transpire INCLUSIONS template from a job JSON. Stdlib only.

    python fill_inclusions.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_inclusions.py --template <blank.docx> --job <job.json> --check

Copies the blank template and writes the client/lot values into it the same way a
person editing in Word does: a new run inserted after the label's whitespace,
inheriting that run's formatting. The template's own wording, styles, numbering
and inclusion text are never touched, so the output is the existing template with
values in it - not a regenerated document.

Every anchor is filled at ALL of its occurrences, because the signature pages are
duplicated for the builder's copy and the owner's copy (manual: "Repeat this on
the Builders and Owners copy").

Field anchors were verified against the blank Gunnedah INTEGRITY template and
three completed jobs in Z:\\PROJECTS\\TAMWORTH (lots 141, 143, 144). Rules: see
job-roles/contract-admin/rules/contract-docs.md (CD-*).

--check reports which anchors were found without writing anything, so a template
that has moved on can be caught before it produces a half-filled contract.
"""
import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

T_RE = re.compile(r"<w:t(?: [^>]*)?>.*?</w:t>", re.S)
RUN_RE = re.compile(r"<w:r(?: [^>]*)?>(?:(?!<w:r[ >]).)*?</w:r>", re.S)
# A gap run holds no value - only whitespace, and sometimes the label's colon,
# because Word splits "SUBURB:" into a 'SUBURB' run and a ':  ' run.
GAP_ONLY = re.compile(r"^[:\s\u00a0]*$")
# An empty floating text box - the owner-name box under ACKNOWLEDGEMENTS & SIGNATURE
# has no placeholder text at all. Word stores it twice (mc:Choice + mc:Fallback),
# so filling both is what a person editing in Word produces.
EMPTY_TXBX = re.compile(
    r"<w:txbxContent><w:p\b[^>]*>(?:<w:pPr>(?:(?!</w:p>).)*?</w:pPr>)?</w:p></w:txbxContent>",
    re.S,
)

# (anchor, json key, mode, exact)
#
# mode:
#   gap         - insert the value as a new run after the label's trailing gap runs
#   suffix      - label and value share one run, e.g. "PRICE : $"
#   dotted      - type the value into the anchor run's own dotted line
#   dotted_next - type the value into the dotted line in the FOLLOWING run
#   prefix      - append the value to following runs that already read "Lot "
#   textbox     - fill the empty floating text box(es) that follow the anchor
#
# exact=True matches the whole run text, which matters because "SUBURB" is a
# substring of page 1's "SUBURB :" and would otherwise be filled twice.
FIELDS = [
    # --- page 1 header table (CD-2) ---
    ("Lot No. :",           "lot_no",      "gap",    True),
    ("STREET :",            "street",      "gap",    True),
    ("SUBURB :",            "suburb",      "gap",    True),
    ("ESTATE :",            "estate",      "gap",    True),
    ("HOUSE TYPE :",        "house_type",  "gap",    True),
    ("HOUSE SIZE :",        "house_size",  "gap",    True),
    ("HOUSE FA\u00c7ADE :", "facade",      "gap",    True),
    ("GARAGE SIDE :",       "garage_side", "gap",    True),
    ("PRICE : $",           "price",       "suffix", True),
    # --- pages 10-13 signature / acknowledgement blocks (CD-3) ---
    ("Name of Owner 1:",    "owner_1",     "gap",         True),
    ("Name of Owner 2:",    "owner_2",     "dotted_next", True),
    ("LOT No:",             "lot_no",      "gap",         True),
    ("STREET:",             "street",      "gap",         True),
    ("SUBURB",              "suburb",      "gap",         True),
    ("Being the owners of the proposed new home to be located at;",
     "site_address", "prefix", True),
    ("Builders Representative:", "builders_rep", "dotted", False),
    ("ACKNOWLEDGEMENTS & SIGNATURE", "owner_1", "textbox", True),
]


def read_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run_text(run):
    """Visible text of a single <w:r>, with XML entities decoded."""
    return html.unescape("".join(
        re.sub(r"<[^>]+>", "", m.group(0))
        for m in T_RE.finditer(run)
    ))


def set_run_text(run, new):
    """Replace the text of a run's first <w:t>, dropping any others."""
    esc = xml_escape(new)
    seen = [False]

    def sub(m):
        if seen[0]:
            return ""
        seen[0] = True
        space = ' xml:space="preserve"' if esc != esc.strip() else ""
        return f"<w:t{space}>{esc}</w:t>"

    return T_RE.sub(sub, run)


def clone_run(run, text):
    """A new run carrying `text` with this run's formatting."""
    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S)
    return (
        "<w:r>"
        + (rpr.group(0) if rpr else "")
        + f'<w:t xml:space="preserve">{xml_escape(text)}</w:t>'
        + "</w:r>"
    )


def dot_line(prefix, value, dots, lead=3):
    """Type `value` into a dotted line, keeping the line roughly its original length."""
    keep = dots[:lead]
    tail = dots[lead + len(value):]
    return f"{prefix}{keep}{value}{tail}"


def fill(xml, values, report):
    """Apply every field to every occurrence of its anchor."""
    runs = [(m.start(), m.end(), m.group(0)) for m in RUN_RE.finditer(xml)]
    texts = [run_text(r[2]) for r in runs]
    edits = []  # (start, end, replacement)

    for anchor, key, mode, exact in FIELDS:
        value = values.get(key)
        entry = {"key": key, "anchor": anchor, "hits": 0}
        report.append(entry)
        if value is None or str(value).strip() == "":
            entry["skipped"] = True
            continue
        value = str(value)

        if mode == "textbox":
            # empty floating boxes after the anchor - no placeholder run to find
            apos = xml.find(xml_escape(anchor))
            if apos == -1:
                entry["value"] = value
                continue
            for m in EMPTY_TXBX.finditer(xml):
                if m.start() < apos:
                    continue
                at = m.start() + m.group(0).rindex("</w:p>")
                edits.append(
                    (at, at, f'<w:r><w:t xml:space="preserve">{xml_escape(value)}</w:t></w:r>')
                )
                entry["hits"] += 1
            entry["value"] = value
            continue

        for i, t in enumerate(texts):
            if (t.strip() != anchor) if exact else (anchor not in t):
                continue
            s, e, run = runs[i]

            if mode == "suffix":
                # "PRICE : $" -> "PRICE :     $606,000.00"
                base = anchor.rstrip("$ ")
                edits.append((s, e, set_run_text(run, f"{base}     ${value}")))

            elif mode == "dotted":
                edits.append((s, e, set_run_text(
                    run, dot_line(anchor, value, t[len(anchor):]))))

            elif mode == "dotted_next":
                # the dotted line lives in the following run
                if i + 1 >= len(runs):
                    continue
                sj, ej, rj = runs[i + 1]
                edits.append((sj, ej, set_run_text(
                    rj, dot_line("", value, texts[i + 1], lead=1))))

            elif mode == "prefix":
                # the sentence continues in following runs that already read "Lot "
                j = i + 1
                while j < len(runs) and texts[j].strip() in ("Lot", "Lot:", ""):
                    if texts[j].strip():
                        sj, ej, rj = runs[j]
                        edits.append((sj, ej, set_run_text(rj, f"{texts[j]}{value}")))
                        entry["hits"] += 1
                    j += 1
                continue

            else:  # gap - insert a new run after the label's trailing gap runs
                # A run with no text at all is a tab or a break, and marks the end
                # of the gap: on page 10 the name is typed straight after the label,
                # before the tab stops, not out past them.
                j = i + 1
                while j < len(runs) and texts[j] != "" and GAP_ONLY.match(texts[j]):
                    j += 1
                at = runs[j - 1] if j - 1 > i else runs[i]
                edits.append((at[1], at[1], clone_run(at[2], value)))

            entry["hits"] += 1

        entry["value"] = value

    # apply back-to-front so offsets stay valid
    for s, e, repl in sorted(edits, key=lambda x: -x[0]):
        xml = xml[:s] + repl + xml[e:]
    return xml


def write_docx(template, out, xml):
    """Copy the template zip, swapping in the new document.xml."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name
    with zipfile.ZipFile(template) as zin, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp_path, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    values = json.loads(Path(args.job).read_text(encoding="utf-8"))
    xml = read_xml(args.template)
    report = []
    new_xml = fill(xml, values, report)

    print(f"template : {Path(args.template).name}")
    print(f"job      : {Path(args.job).name}")
    print()
    print(f"{'field':<13} {'hits':>4}  {'anchor':<26} value")
    print("-" * 88)
    problems = []
    for info in report:
        key, anchor, hits = info["key"], info["anchor"][:26], info["hits"]
        if info.get("skipped"):
            print(f"{key:<13} {'-':>4}  {anchor:<26} (no value - left blank)")
            continue
        flag = "" if hits else "   <-- ANCHOR NOT FOUND"
        print(f"{key:<13} {hits:>4}  {anchor:<26} {info['value'][:30]}{flag}")
        if not hits:
            problems.append(f"{key} ({info['anchor'][:24]})")
    print()

    unknown = sorted(set(values) - {f[1] for f in FIELDS})
    if unknown:
        print(f"NOTE: job JSON has keys this template does not use: {', '.join(unknown)}")

    if problems:
        print(f"WARNING: no anchor found for: {', '.join(problems)}")
        print("The template may have changed. Do not issue this document - check it.")

    if args.check:
        print("(--check: nothing written)")
        return 1 if problems else 0

    if not args.out:
        print("ERROR: --out is required unless --check is given", file=sys.stderr)
        return 2

    out = write_docx(args.template, args.out, new_xml)
    print(f"written  : {out}")
    print("DRAFT - a person must read this against the email and plans before it goes out.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
