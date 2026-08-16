"""Fill the blank NSW PRELIMINARY AGREEMENT from a job JSON. Stdlib only.

    python fill_prelim.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_prelim.py --template <blank.docx> --job <job.json> --check

Writes the client, addresses, fee and signature names into the blank template
exactly the way the completed agreements on the drive do it (CD-4). Verified
against eight completed preliminary agreements: the two Tamworth jobs at Pioneer
Close (26036, 26045 - reproduced text-for-text by regress_prelim.py), plus five
Sydney and one Gunnedah/SEQ-filed job for the structural conventions:

  - Client row: a single client's name replaces the "&" run as "  <name>";
    two clients keep the template's cells - name 1 typed after "And", name 2
    after "&" (the cell-preserving shape used by the majority of two-client
    jobs; the others hand-merge the cells and agree on nothing).
  - Single-client jobs also carry a 62-space layout run pushing the
    "(Current Residential Address)" label right - both Tamworth singles have
    exactly this run, so reproducing them requires it.
  - Addresses: typed after their labels - 3 spaces before the residential
    address, 6 before "Lot <site address>" (the Tamworth pair agree exactly;
    Sydney jobs use anything from 1 to 9 spaces - hand-typed, no convention).
  - Signature block: every one of the eight jobs types owner 1 two paragraphs
    above the first "Client Name" label, owner 2 two above the second, and
    Michael CRONK three above "Name who is authorised..." - i.e. onto the
    printed signing lines.

THE FEE IS A MANDATORY INPUT. The template's $30,000 is not the job's fee and
has been wrong in practice (CD-4.3): every observed job edits it ($2,500 to
$32,035). A job JSON without prelim_fee is refused, never defaulted.

Whether the job needs a preliminary agreement at all is a human decision
(CD-4.4) - the request email saying "no prelim required" has been overridden in
practice. Ask; do not resolve it either way.

--check reports every anchor without writing anything - run it first.
"""
import argparse
import html
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

T_RE = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
RUN_RE = re.compile(r"<w:r(?: [^>]*)?>(?:(?!<w:r[ >]).)*?</w:r>", re.S)
P_RE = re.compile(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", re.S)

RESI_LABEL = "(Current Residential Address)"
CONS_LABEL = "(For Construction Address)"
FEE_TEXT = "$30,000."
# pads measured off the two completed Tamworth agreements (26036, 26045)
RESI_PAD, CONS_PAD, CLIENT_PAD = 3, 6, 62
SIG_LEAD = {"owner_1": "  ", "owner_2": "  ", "builders_rep": "   "}


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run_text(run):
    return html.unescape("".join(
        re.sub(r"<[^>]+>", "", m.group(0)) for m in T_RE.finditer(run)))


def clone_run(run, text):
    rpr = re.search(r"<w:rPr>.*?</w:rPr>", run, re.S)
    return ("<w:r>" + (rpr.group(0) if rpr else "")
            + f'<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>')


def set_run_text(run, new):
    esc = xml_escape(new)
    seen = [False]

    def sub(m):
        if seen[0]:
            return ""
        seen[0] = True
        space = ' xml:space="preserve"' if esc != esc.strip() else ""
        return f"<w:t{space}>{esc}</w:t>"

    return T_RE.sub(sub, run)


def joined_index(runs):
    """Concatenated text of all runs, with each run's start offset in it."""
    joined, offsets = [], []
    pos = 0
    for _, _, r in runs:
        t = run_text(r)
        offsets.append(pos)
        joined.append(t)
        pos += len(t)
    return "".join(joined), offsets


def run_at(offsets, pos):
    """Index of the run whose text contains joined-text position pos."""
    lo = 0
    for i, off in enumerate(offsets):
        if off <= pos:
            lo = i
        else:
            break
    return lo


def para_rpr(p_xml):
    """The paragraph mark's run properties - what Word gives a run typed here."""
    m = re.search(r"<w:pPr>.*?(<w:rPr>.*?</w:rPr>).*?</w:pPr>", p_xml, re.S)
    return m.group(1) if m else ""


def fill(xml, values, report):
    runs = [(m.start(), m.end(), m.group(0)) for m in RUN_RE.finditer(xml)]
    joined, offsets = joined_index(runs)
    edits = []  # (start, end, replacement)

    def note(key, anchor, value=None, hits=0, skipped=False):
        report.append({"key": key, "anchor": anchor, "value": value,
                       "hits": hits, "skipped": skipped})

    owner_1 = (values.get("owner_1") or "").strip()
    owner_2 = (values.get("owner_2") or "").strip()
    rep = (values.get("builders_rep") or "Michael CRONK").strip()

    # --- client row: the one "And" followed by a "&" run within three runs ---
    pairs = [(i, j) for i, (_, _, r) in enumerate(runs) if run_text(r) == "And"
             for j in range(i + 1, min(i + 4, len(runs)))
             if run_text(runs[j][2]) == "&"]
    if len(pairs) != 1:
        note("owner_1", "And ... & (client row)", owner_1)
    else:
        i_and, i_amp = pairs[0]
        s, e, amp_run = runs[i_amp]
        if owner_2:
            edits.append((runs[i_and][1], runs[i_and][1],
                          clone_run(runs[i_and][2], f" {owner_1}")))
            edits.append((e, e, clone_run(amp_run, f" {owner_2}")))
            note("owner_1", "after And (two clients)", owner_1, 1)
            note("owner_2", "after & (two clients)", owner_2, 1)
        else:
            # every completed single-client agreement also deletes the tab
            # before the old "&" (it sits INSIDE the & run, ahead of the
            # text), so the name flows straight after "And" - keeping it
            # shifts the name a tab stop right
            new_run = set_run_text(amp_run, f"  {owner_1}").replace("<w:tab/>", "")
            edits.append((s, e, new_run))
            for j in range(i_and + 1, i_amp):  # tab as its own run, same rule
                if "<w:tab" in runs[j][2] and not run_text(runs[j][2]):
                    edits.append((runs[j][0], runs[j][1], ""))
            note("owner_1", "replaces & (single client)", owner_1, 1)
            note("owner_2", "Name of Owner 2", skipped=True)
            # both completed single-client Tamworth jobs carry this layout run
            lbl = joined.find(RESI_LABEL)
            if lbl != -1:
                k = run_at(offsets, lbl)
                edits.append((runs[k][0], runs[k][0],
                              clone_run(runs[k][2], " " * CLIENT_PAD)))

    # --- the two addresses, typed after their labels ---
    for key, label, pad, prefix in (
            ("residential_address", RESI_LABEL, RESI_PAD, ""),
            ("site_address", CONS_LABEL, CONS_PAD, "Lot ")):
        value = (values.get(key) or "").strip()
        lbl = joined.find(label)
        if lbl == -1:
            note(key, label, value)
            continue
        if not value:
            note(key, label, skipped=True)
            continue
        k = run_at(offsets, lbl + len(label) - 1)
        edits.append((runs[k][1], runs[k][1],
                      clone_run(runs[k][2], f"{' ' * pad}{prefix}{value}")))
        note(key, label, f"{prefix}{value}", 1)

    # --- the fee: replace the template's figure, never keep it ---
    fee = (values.get("prelim_fee") or "").strip().lstrip("$").rstrip(".")
    fee_hits = [i for i, (_, _, r) in enumerate(runs) if FEE_TEXT in run_text(r)]
    if len(fee_hits) != 1:
        note("prelim_fee", FEE_TEXT, fee)
    else:
        s, e, r = runs[fee_hits[0]]
        t = run_text(r).replace(FEE_TEXT, f"${fee}.")
        edits.append((s, e, set_run_text(r, t)))
        note("prelim_fee", FEE_TEXT, f"${fee}.", 1)

    # --- signature block: names typed onto the printed signing lines ---
    ex = xml.find("EXECUTED")
    sig_ps = []
    if ex != -1:
        for m in P_RE.finditer(xml, ex):
            sig_ps.append(m)
            if "authorised" in run_text(m.group(0)):
                break
    labels = [n for n, m in enumerate(sig_ps)
              if "Client Name" in run_text(m.group(0))]
    auth = len(sig_ps) - 1 if sig_ps and "authorised" in run_text(sig_ps[-1].group(0)) else None
    targets = []
    if len(labels) == 2 and auth is not None:
        targets = [("owner_1", owner_1, labels[0] - 2),
                   ("owner_2", owner_2, labels[1] - 2),
                   ("builders_rep", rep, auth - 3)]
    for key, value, n in targets:
        anchor = {"owner_1": "1st Client Name - 2", "owner_2": "2nd Client Name - 2",
                  "builders_rep": "authorised - 3"}[key]
        if not value:
            note(f"sig:{key}", anchor, skipped=True)
            continue
        if n < 0 or n >= len(sig_ps) or run_text(sig_ps[n].group(0)).strip():
            note(f"sig:{key}", anchor, value)   # target missing or not empty
            continue
        p = sig_ps[n].group(0)
        at = sig_ps[n].start() + p.rindex("</w:p>")
        rpr = para_rpr(p)
        edits.append((at, at,
                      f'<w:r>{rpr}<w:t xml:space="preserve">'
                      f'{xml_escape(SIG_LEAD[key] + value)}</w:t></w:r>'))
        note(f"sig:{key}", anchor, value, 1)
    if not targets:
        for key in ("owner_1", "owner_2", "builders_rep"):
            note(f"sig:{key}", "signature block not recognised")

    for s, e, repl in sorted(edits, key=lambda x: -x[0]):
        xml = xml[:s] + repl + xml[e:]
    return xml


def write_docx(template, out, xml):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the output, NOT the system temp dir - that is on C:.
    tmp_path = out.with_suffix(".partial")
    with zipfile.ZipFile(template) as zin, zipfile.ZipFile(
            tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
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

    if "PRELIMINARY AGREEMENT" not in Path(args.template).name.upper():
        print(f"ERROR: {Path(args.template).name} does not look like the "
              "preliminary agreement template", file=sys.stderr)
        return 2
    if not (values.get("owner_1") or "").strip():
        print("ERROR: owner_1 is required - a preliminary agreement without a "
              "client is not a draft", file=sys.stderr)
        return 2
    if not (values.get("prelim_fee") or "").strip():
        print("ERROR: prelim_fee is required and must be sourced or confirmed "
              "for THIS job (CD-4.3).", file=sys.stderr)
        print("       The template's $30,000 is not the job's fee - observed "
              "jobs range $2,500-$32,035.", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[\d,]+", values["prelim_fee"].strip().lstrip("$").rstrip(".")):
        print(f"ERROR: prelim_fee {values['prelim_fee']!r} is not a plain "
              "figure like 5,000", file=sys.stderr)
        return 2

    with zipfile.ZipFile(args.template) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    report = []
    new_xml = fill(xml, values, report)

    print(f"template : {Path(args.template).name}")
    print(f"job      : {Path(args.job).name}")
    print()
    print(f"{'field':<22} {'hits':>4}  {'anchor':<28} value")
    print("-" * 88)
    problems = []
    for info in report:
        key, anchor = info["key"], info["anchor"][:28]
        if info["skipped"]:
            print(f"{key:<22} {'-':>4}  {anchor:<28} (no value - left blank)")
            continue
        flag = "" if info["hits"] else "   <-- ANCHOR NOT FOUND"
        print(f"{key:<22} {info['hits']:>4}  {anchor:<28} {str(info['value'])[:30]}{flag}")
        if not info["hits"]:
            problems.append(key)
    print()

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
    print("DRAFT - whether the job needs a preliminary agreement at all is a "
          "human decision (CD-4.4).")
    return 1 if problems else 0


# This console is cp1252; document text carries curly quotes and dotted leaders.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
