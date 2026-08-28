"""Fill the blank NSW PRELIMINARY AGREEMENT from a job JSON. Stdlib only.

    python fill_prelim.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_prelim.py --template <blank.docx> --job <job.json> --check

Writes the client, addresses, fee and signature names into the blank template
the way the team's corrected agreements do it (CD-4.5). The conventions were
rebuilt 28 Aug 2026 from the team's review of the AI-filled documents
(AI.Manual.comparison (2).xlsx, "Preliminary Agreement" sheet) and verified
against the three corrected Sydney agreements that review screenshots (jobs
26019, 26032, 26052 - regress_prelim.py reproduces 26032 and 26052
space-for-space):

  - Client row, as the team wrote it out (confirmed 28 Aug 2026):
        single buyer  And <First> <Middle> <LAST NAME>  (“Client”)
        two buyers    And <buyer 1> & <buyer 2>  (“Clients”)
    The name(s) flow straight after "And" with the one tab kept before
    ("Client"), which becomes ("Clients") when there are two. Each name is
    First name + Middle name + LAST NAME with the surname in CAPS (CD-3.1) -
    the middle name comes off the client ID and is easy to miss, and it is
    typed the same way in the inclusions (executed 25176 carries "Shaun Leslie
    MCMEEKEN" in both documents). The corrected 26052 predates the plural and
    keeps ("Client"); the team confirmed the plural, so it stays.
  - "(Current Residential Address)" starts its own paragraph, cloned from the
    client row's properties, with the value one space after the label. The old
    62-space layout run (measured off the Tamworth pair) is gone - on every
    job with a different name length it dragged the label up onto the client
    line, which is the exact fault the team flagged.
  - "(For Construction Address)": value five spaces after the label, prefixed
    "Lot " (the corrected 26032/26052 agree on five).
  - The fee: replaced when the job supplies one; ABSENT MEANS THE TEMPLATE'S
    $30,000 STANDS. CD-4.3 reversed 28 Aug 2026 - the team: "$30,000 is the
    standard prelim fees amount, please proceed ... without asking"; only a
    fee named in the request changes it.
  - 3. ENDING AGREEMENT: the third paragraph (the sunset-clause insertion) and
    the empty spacer above it are re-indented to match their neighbours
    (left 820 / right 105, justified BodyText). The master template was
    corrected at source 28 Aug 2026 (CD-4.6), so this is a no-op on the current
    blank; it is kept as a guard for older copies and any future revision that
    reintroduces the fault, and it still applies to the Stage F2 sibling.
  - Signature block: owner 1 goes two paragraphs above the first "Client Name"
    label, owner 2 two above the second, and the builders representative three
    above "Name who is authorised..." - typed in Calibri 12, confirmed by the
    team 28 Aug 2026. Cloning the blank's paragraph marks rendered the names at
    8-9pt, the "too small" fault the team flagged; the corrected documents
    themselves sit at 10-11pt, and the team chose 12 over both.

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
PPR_RE = re.compile(r"<w:pPr>.*?</w:pPr>", re.S)

RESI_LABEL = "(Current Residential Address)"
CONS_LABEL = "(For Construction Address)"
FEE_TEXT = "$30,000."
RESI_PAD, CONS_PAD = 1, 5  # spaces between label and value (corrected 26032/26052)
SIG_LEAD = {"owner_1": "  ", "owner_2": "  ", "builders_rep": "   "}
# Calibri 12 for the typed signature names (comparison sheet; team-confirmed
# 28 Aug 2026, over both the blank's 8-9pt and the corrected docs' 10-11pt)
SIG_RPR = ('<w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Calibri"'
           ' w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="24"/>'
           '<w:szCs w:val="24"/></w:rPr>')
# What the paragraphs around the sunset clause use; the corrected agreements
# re-indent the clause and its spacer to exactly this
BODY_PPR = ('<w:pPr><w:pStyle w:val="BodyText"/>'
            '<w:ind w:left="820" w:right="105"/><w:jc w:val="both"/></w:pPr>')
SUNSET_ANCHOR = "pursuant to a sunset clause"


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def name_advisory(key, value):
    """Flag a client name that is not First name + Middle name + LAST NAME.

    Advisory only, never fatal: the surname's CAPS is the checkable half of
    the team's format (CD-3.1), while a missing middle name is indistinguishable
    from a client who has none. Company/trust owners (CD-3.9) are typed in CAPS
    throughout and pass.
    """
    value = (value or "").strip()
    if not value:
        return None
    last = value.split()[-1]
    if any(c.isalpha() for c in last) and last != last.upper():
        return (f"{key} \"{value}\": surname is not in CAPS - the team's format "
                "is First name + Middle name + LAST NAME (CD-3.1). Check it "
                "against the client ID before this goes out.")
    return None


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
        if owner_2:
            note("owner_2", "And ... & (client row)", owner_2)
    else:
        i_and, i_amp = pairs[0]
        s, e, amp_run = runs[i_amp]
        # the name(s) flow straight after "And": the corrected agreements
        # delete the tab ahead of the old "&" (it sits INSIDE the & run) so
        # nothing lands on a tab stop before ("Client")
        names = f"  {owner_1} & {owner_2}" if owner_2 else f"  {owner_1}"
        edits.append((s, e, set_run_text(amp_run, names).replace("<w:tab/>", "")))
        for j in range(i_and + 1, i_amp):  # tab as its own run, same rule
            if "<w:tab" in runs[j][2] and not run_text(runs[j][2]):
                edits.append((runs[j][0], runs[j][1], ""))
        if owner_2:
            note("owner_1", "after And (two clients)", f"{owner_1} & …", 1)
            note("owner_2", "joined with & (two clients)", owner_2, 1)
            # two buyers sign as ("Clients") - team-confirmed 28 Aug 2026
            for j in range(i_amp + 1, min(i_amp + 8, len(runs))):
                if run_text(runs[j][2]) == "Client”":
                    edits.append((runs[j][0], runs[j][1],
                                  set_run_text(runs[j][2], "Clients”")))
                    note("clients_plural", "(“Client”) → (“Clients”)",
                         "Clients", 1)
                    break
            else:
                note("clients_plural", "(“Client”) after the names", "Clients")
        else:
            note("owner_1", "replaces & (single client)", owner_1, 1)
            note("owner_2", "Name of Owner 2", skipped=True)

    # --- the two addresses, typed after their labels ---
    for key, label, pad, prefix, own_line in (
            ("residential_address", RESI_LABEL, RESI_PAD, "", True),
            ("site_address", CONS_LABEL, CONS_PAD, "Lot ", False)):
        value = (values.get(key) or "").strip()
        lbl = joined.find(label)
        if lbl == -1:
            note(key, label, value)
            continue
        if not value:
            note(key, label, skipped=True)
            continue
        k0 = run_at(offsets, lbl)
        k = run_at(offsets, lbl + len(label) - 1)
        edits.append((runs[k][1], runs[k][1],
                      clone_run(runs[k][2], f"{' ' * pad}{prefix}{value}")))
        note(key, label, f"{prefix}{value}", 1)
        if not own_line:
            continue
        # the label starts its own paragraph, directly under the client name
        # (comparison sheet, 28 Aug 2026): split the client-row paragraph
        # just before the label, cloning the paragraph properties
        para = next((m for m in P_RE.finditer(xml)
                     if m.start() < runs[k0][0] < m.end()), None)
        before = ""
        if para:
            before = "".join(T_RE.findall(para.group(0)[:runs[k0][0] - para.start()]))
        if para and offsets[k0] == lbl and before.strip():
            ppr = PPR_RE.search(para.group(0))
            edits.append((runs[k0][0], runs[k0][0],
                          "</w:p><w:p>" + (ppr.group(0) if ppr else "")))
            note("resi_own_line", "new paragraph before label", "", 1)
        elif para and not before.strip():
            # already at the start of its paragraph - nothing to split
            note("resi_own_line", "label already starts a paragraph", "", 1)
        else:
            note("resi_own_line", "label run not clean to split")

    # --- the fee: replace when the job names one; otherwise the template's
    # standard $30,000 stands (CD-4.3, reversed 28 Aug 2026) ---
    fee = (values.get("prelim_fee") or "").strip().lstrip("$").rstrip(".")
    fee_hits = [i for i, (_, _, r) in enumerate(runs) if FEE_TEXT in run_text(r)]
    if len(fee_hits) != 1:
        note("prelim_fee", FEE_TEXT, fee or "(template default)")
    elif not fee:
        note("prelim_fee", FEE_TEXT, "$30,000. (standard fee kept)", 1)
    else:
        s, e, r = runs[fee_hits[0]]
        t = run_text(r).replace(FEE_TEXT, f"${fee}.")
        edits.append((s, e, set_run_text(r, t)))
        note("prelim_fee", FEE_TEXT, f"${fee}.", 1)

    # --- 3. ENDING AGREEMENT: re-indent the sunset paragraph and its spacer
    # to match the neighbouring paragraphs (every corrected agreement does) ---
    ps = list(P_RE.finditer(xml))
    sun = next((n for n, m in enumerate(ps)
                if SUNSET_ANCHOR in run_text(m.group(0))), None)
    if sun is None:
        note("sunset_align", SUNSET_ANCHOR)
    else:
        m = ps[sun]
        ppr = PPR_RE.search(m.group(0))
        if ppr and ppr.group(0) != BODY_PPR:
            edits.append((m.start() + ppr.start(), m.start() + ppr.end(),
                          BODY_PPR))
        note("sunset_align", "sunset clause ¶ → 820/105", "", 1)
        spacer = ps[sun - 1] if sun else None
        if spacer is not None and not run_text(spacer.group(0)).strip():
            sppr = PPR_RE.search(spacer.group(0))
            if sppr and sppr.group(0) != BODY_PPR:
                edits.append((spacer.start() + sppr.start(),
                              spacer.start() + sppr.end(), BODY_PPR))
            note("sunset_spacer", "empty ¶ above → 820/105", "", 1)
        else:
            note("sunset_spacer", "no empty ¶ above sunset clause")

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
        edits.append((at, at,
                      f'<w:r>{SIG_RPR}<w:t xml:space="preserve">'
                      f'{xml_escape(SIG_LEAD[key] + value)}</w:t></w:r>'))
        note(f"sig:{key}", anchor, f"{value} (Calibri 12)", 1)
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
    fee = (values.get("prelim_fee") or "").strip()
    if fee and not re.fullmatch(r"[\d,]+", fee.lstrip("$").rstrip(".")):
        print(f"ERROR: prelim_fee {values['prelim_fee']!r} is not a plain "
              "figure like 5,000", file=sys.stderr)
        return 2

    with zipfile.ZipFile(args.template) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    report = []
    new_xml = fill(xml, values, report)

    print(f"template : {Path(args.template).name}")
    print(f"job      : {Path(args.job).name}")
    if not fee:
        print("fee      : none supplied - the template's standard $30,000 "
              "stands (CD-4.3, 28 Aug 2026)")
    for advisory in (name_advisory("owner_1", values.get("owner_1")),
                     name_advisory("owner_2", values.get("owner_2"))):
        if advisory:
            print(f"NOTE     : {advisory}")
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
