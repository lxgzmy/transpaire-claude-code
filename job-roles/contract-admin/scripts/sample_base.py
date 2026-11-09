r"""Another job's inclusions as the base of this job's (CD-6.6). Stdlib only.

    python sample_base.py --blank <family blank.docx> --sample <sample.docx> --job <job.json>
                          --out-blank <sample base.docx> [--docx <filled.docx>] [--report <sample_base.txt>]
    python sample_base.py --scan <docx> --sample <sample.docx> --job <job.json>

Why (job 26061 feedback sheet, 9 Nov 2026 row 5): a contract request can send a
completed inclusions of another lot as the base - "I have attached sample
inclusions from an Aux dwelling at another lot - just remove the note about
infrastructure fees". The Gunnedah family has no AUXILIARY blank, so the aux
dwelling's upgrades exist only in such a sample. The 26061 run refilled the
sample by hand in chat, outside every check, and shipped a label with nothing
beside it, a Date out of line and the blank's highlights.

What it does. The base is the family's CURRENT blank with the sample's body
table (the two-column specification) in place of the blank's. Everything else -
page 1, the signature and acknowledgement pages, the site box, headers and
footers - is the blank's, so the run fills every client and lot value as it
does for any job and nothing of the sample's client can survive there. With
--docx, the filled document gets the same body. edit_inclusions.py then treats
the base as the blank (--family gunnedah): the request's removals, the layout
plan, the Word layout pass and the quality gate run as they do for Sydney and
SEQ.

It stops, writing nothing, when:
  - the blank is not a Gunnedah-family blank (Sydney and SEQ have AUXILIARY
    blanks of their own: a sample base there is a person's edit);
  - the sample's standard sections do not read exactly as the blank's (it was
    built on another blank or another version - a person decides);
  - its upgraded sections do not pair label with wording (the structure check);
  - its body names its own client: the lot, the street, an owner, the price;
  - its body uses a list, style or relationship the blank does not define.

--scan is the last check before the save: no text of the document (body, text
boxes, headers, footers) names the sample's client. Details this job shares
(the same owner name, the same lot number) are left out of both scans.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import edit_inclusions as E  # noqa: E402
from fill_inclusions import pick_family  # noqa: E402

FAMILIES = ("gunnedah",)   # families with no AUXILIARY blank, where a sample base is the way in
STREET_TYPES = {
    "street", "st", "road", "rd", "close", "cl", "drive", "dr", "avenue", "ave", "court", "ct", "place",
    "pl", "crescent", "cres", "way", "lane", "ln", "parade", "pde", "circuit", "cct", "boulevard", "bvd",
    "terrace", "tce", "grove", "gr", "rise", "loop", "link", "row", "walk", "glen", "view", "heights",
    "nsw", "qld", "the",
}
NAME_STOP = {"and", "the", "pty", "ltd", "limited", "trust", "trustee", "for", "atf", "family"}
PARA_TEXT = E.ptext


def norm(t):
    return E.norm(t)


def parts_text(path, names=None):
    """{part name: [paragraph texts]} of document.xml, headers and footers."""
    out = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if re.fullmatch(r"word/(document|header\d*|footer\d*)\.xml", n) and (names is None or n in names):
                xml = z.read(n).decode("utf-8")
                out[n] = [norm(PARA_TEXT(p)) for p in E.P_RE.findall(E.normalise_self_closing(xml))]
    return out


def client_of(xml):
    """The sample's own client and lot details, read off its labelled paragraphs
    outside the body table: {'lot', 'street', 'owners', 'price', 'site'}."""
    c = E.Columns(xml)
    outside = c.xml[:c.ts] + c.xml[c.te:]
    found = {"lot": set(), "street": set(), "owners": set(), "price": set(), "site": set()}
    for p in E.P_RE.findall(outside):
        t = norm(PARA_TEXT(p))
        dotless = norm(re.sub(r"[.\u2026]{2,}", " ", t))
        m = re.match(r"(?:Lot No\. ?:|LOT No:)\s*(\S+)", t)
        if m:
            found["lot"].add(m.group(1).strip(","))
        m = re.match(r"STREET ?:\s*(.+)", t)
        if m:
            found["street"].add(m.group(1))
        m = re.match(r"PRICE ?:\s*\$?\s*([\d,]+)", t)
        if m and re.search(r"\d", m.group(1)):
            found["price"].add(m.group(1).rstrip(","))
        m = re.match(r"Name of Owner \d:\s*(.*?)\s*(?:Date:.*)?$", dotless)
        if m and re.search(r"[A-Za-z]", m.group(1)):
            found["owners"].add(norm(m.group(1)))
        m = re.match(r"Lot (\d+\w*), (.+)", t)
        if m:
            found["site"].add(t)
            found["lot"].add(m.group(1))
    return found


def tokens(client, job):
    """[(label, compiled pattern)] that name the sample's client and not this job."""
    mine = " ".join(str(job.get(k, "")) for k in ("owner_1", "owner_2", "owners", "street", "lot_no",
                                                     "price", "site_address", "land_street")).lower()
    out = []
    for lot in sorted(client["lot"]):
        if lot.lower() != str(job.get("lot_no", "")).strip().lower():
            out.append((f"lot {lot}", re.compile(rf"\bLot\s*(?:No\.?\s*:?\s*)?{re.escape(lot)}\b", re.I)))
    words = set()
    for s in client["street"]:
        for w in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", s):
            if w.lower() not in STREET_TYPES:
                words.add(w)
    for w in sorted(words):
        if not re.search(rf"\b{re.escape(w.lower())}\b", mine):
            out.append((f"street name {w!r}", re.compile(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])", re.I)))
    names = set()
    for o in client["owners"]:
        names.add(o)
        for w in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", o):
            if w.lower() not in NAME_STOP:
                names.add(w)
    for n in sorted(names, key=len, reverse=True):
        if not re.search(rf"(?<![a-z]){re.escape(n.lower())}(?![a-z])", mine):
            # case kept: a surname in capitals, a given name capitalised - "WHITE"
            # the owner is not "white" the colour
            out.append((f"owner {n!r}", re.compile(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])")))
    for p in sorted(client["price"]):
        if p.replace(",", "") not in mine.replace(",", ""):
            out.append((f"price {p}", re.compile(re.escape(p))))
    return out


def scan(texts, toks):
    """[(label, where, line)] for every hit."""
    hits = []
    for where, lines in texts.items():
        for line in lines:
            for label, rx in toks:
                if rx.search(line):
                    hits.append((label, where, line[:90]))
    return hits


def standard_diff(blank_cols, cols):
    """Differences between the standard sections (labels up to the last standard
    label; wording up to the first upgraded heading) of two documents."""
    def left(c):
        ls = E.find_idx(c.left, E.exact(E.LAST_STANDARD_LABEL))
        if ls < 0:
            raise SystemExit(f"STOP: no {E.LAST_STANDARD_LABEL!r} label - not the family's two-column body")
        return E.texts(c.left[: ls + 1])

    def right(c):
        heads = E.upgraded_headings(c.right)
        if not heads:
            raise SystemExit(f"STOP: no {E.UPGRADED_HEADING!r} heading in the right column")
        return E.texts(c.right[: heads[0]])

    out = []
    for name, a, b in (("labels", left(blank_cols), left(cols)), ("wording", right(blank_cols), right(cols))):
        if a != b:
            pairs = [(x, y) for x, y in zip(a, b) if x != y][:5]
            out.append(f"{name}: blank {len(a)} lines, sample {len(b)}; first differences "
                       + ("; ".join(f"{x[:50]!r} -> {y[:50]!r}" for x, y in pairs) or "(one is longer)"))
    return out


def section_lines(cols):
    secs = E.upgraded_sections(cols)
    out = []
    for s in secs:
        lines = [norm(PARA_TEXT(cols.right[k])) for a, b in s["groups"] for k in range(a, b)]
        labels = [norm(PARA_TEXT(cols.left[i])) for i in s["labels"]]
        out.append((s["heading"], s["dwelling"], labels, lines))
    return out


def defs(z, part):
    try:
        return z.read(part).decode("utf-8")
    except KeyError:
        return ""


def num_def(numbering, num_id):
    """The <w:num> of `num_id` and the <w:abstractNum> it points to, as text."""
    m = re.search(rf'<w:num w:numId="{num_id}"[^>]*>.*?</w:num>', numbering, re.S)
    if not m:
        return None
    a = re.search(r'<w:abstractNumId w:val="(\d+)"', m.group(0))
    ab = re.search(rf'<w:abstractNum\b[^>]*w:abstractNumId="{a.group(1)}"[^>]*>.*?</w:abstractNum>',
                   numbering, re.S) if a else None
    strip = (lambda s: re.sub(r'\s(?:w15:|w16[a-z]*:)?(?:restartNumberingAfterBreak|nsid|tmpl)[^=]*="[^"]*"|'
                              r'<w:(?:nsid|tmpl)[^>]*/>', "", s))
    return strip(m.group(0)), strip(ab.group(0)) if ab else None


def references(blank, sample, body):
    """Problems with what the sample body points to outside itself."""
    problems = []
    with zipfile.ZipFile(blank) as zb, zipfile.ZipFile(sample) as zs:
        if re.search(r'\br:(?:id|embed|link|pict)="', body):
            rb, rs = defs(zb, "word/_rels/document.xml.rels"), defs(zs, "word/_rels/document.xml.rels")
            for rid in sorted(set(re.findall(r'\br:(?:id|embed|link|pict)="([^"]+)"', body))):
                tb = re.search(rf'Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', rb)
                ts = re.search(rf'Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', rs)
                if not tb or not ts or tb.group(1) != ts.group(1):
                    problems.append(f"relationship {rid} ({ts.group(1) if ts else '?'}) is not the blank's")
        nb, ns = defs(zb, "word/numbering.xml"), defs(zs, "word/numbering.xml")
        for nid in sorted(set(re.findall(r'<w:numId w:val="(\d+)"', body)), key=int):
            if nid == "0":
                continue
            mine = num_def(nb, nid)
            if mine is None:
                problems.append(f"list numbering {nid} is not defined in the blank")
            elif mine != num_def(ns, nid):
                problems.append(f"list numbering {nid} differs from the blank's")
        sb = defs(zb, "word/styles.xml")
        for sid in sorted(set(re.findall(r'<w:(?:pStyle|rStyle|tblStyle) w:val="([^"]+)"', body))):
            if f'w:styleId="{sid}"' not in sb:
                problems.append(f"style {sid!r} is not in the blank")
        if re.search(r"<w:(?:footnoteReference|endnoteReference|commentReference)\b", body):
            problems.append("a footnote, endnote or comment reference")
    return problems


def tidy_ids(xml, ts, te):
    """Paragraph ids and bookmarks of the transplanted body that clash with the
    rest of the document: duplicate w14 ids dropped (Word makes new ones), a
    clashing bookmark removed (its text stays)."""
    body, rest = xml[ts:te], xml[:ts] + xml[te:]
    taken = set(re.findall(r'w14:paraId="([0-9A-Fa-f]+)"', rest))
    body = re.sub(r'\sw14:(?:paraId|textId)="([0-9A-Fa-f]+)"',
                  lambda m: "" if m.group(1) in taken else m.group(0), body)
    names = set(re.findall(r'<w:bookmarkStart\b[^>]*w:name="([^"]+)"', rest))
    ids = set(re.findall(r'<w:bookmark(?:Start|End)\b[^>]*w:id="(\d+)"', rest))
    for m in list(re.finditer(r'<w:bookmarkStart\b[^>]*/>', body)):
        name = re.search(r'w:name="([^"]+)"', m.group(0))
        bid = re.search(r'w:id="(\d+)"', m.group(0))
        if (name and name.group(1) in names) or (bid and bid.group(1) in ids):
            b = bid.group(1) if bid else None
            body = body.replace(m.group(0), "", 1)
            if b:
                body = re.sub(rf'<w:bookmarkEnd\b[^>]*w:id="{b}"[^>]*/>', "", body, count=1)
    return xml[:ts] + body + xml[te:]


def heading_colour(blank_xml, sample_xml, log):
    """The sample's upgrade headings in the blank's heading formatting where a sample
    left one black: the package headings keep the template's blue (issue #58), and
    the gate fails a heading without it. The blank heading's run formatting is
    copied whole (font, size, colour), so no run property is pieced together."""
    bc = E.Columns(blank_xml)
    bh = E.upgraded_headings(bc.right)
    run = E.RUN_RE.search(bc.right[bh[0]]) if bh else None
    rpr = E.RPR_RE.search(run.group(0)) if run else None
    if not rpr or not re.search(r'<w:color w:val="(?!000000)', rpr.group(0)):
        return sample_xml
    cols = E.Columns(sample_xml)
    fixed = []
    for i in E.upgraded_headings(cols.right):
        p = cols.right[i]
        if re.search(r'<w:color w:val="(?!000000)[0-9A-Fa-f]{6}"', p):
            continue

        def recolour(m):
            r = m.group(0)
            return E.RPR_RE.sub(rpr.group(0), r, count=1) if E.RPR_RE.search(r) else \
                re.sub(r"^(<w:r\b[^>]*>)", r"\1" + rpr.group(0), r, count=1)
        cols.right[i] = E.RUN_RE.sub(recolour, p)
        fixed.append(norm(PARA_TEXT(p)))
    if fixed:
        log.append(f"headings      : {fixed} given the blank's heading formatting (the template's blue, issue #58)")
        return cols.rebuild()
    return sample_xml


def with_body(target_xml, sample_xml):
    """`target_xml` with its body table replaced by the sample's."""
    t = E.normalise_self_closing(target_xml)
    s = E.normalise_self_closing(sample_xml)
    tts, tte = E.body_table(t)
    sts, ste = E.body_table(s)
    body = s[sts:ste]
    out = t[:tts] + body + t[tte:]
    return tidy_ids(out, tts, tts + len(body))


def cache_name(blank, sample):
    """A stable name for the base of one blank + one sample body: the same sample
    sent again reuses its Word measurement (draft_contract.blank_measure_for)."""
    h = hashlib.sha1(Path(blank).read_bytes())
    s = E.normalise_self_closing(E.read_xml(sample))
    a, b = E.body_table(s)
    h.update(s[a:b].encode("utf-8"))
    return f"sample-base-{h.hexdigest()[:12]}.docx"


def build(args, job, log, flags):
    fam = pick_family(args.blank)[0]
    if fam not in FAMILIES:
        raise SystemExit(f"STOP: a sample base is used on the {', '.join(FAMILIES)} inclusions only - this blank "
                         f"is {fam or 'not a known family'}. Sydney and SEQ have AUXILIARY blanks of their own; "
                         f"anything a sample adds there is a person's edit (CD-6.6).")
    E.use_family(fam)
    blank_xml, sample_xml = E.read_xml(args.blank), E.read_xml(args.sample)
    blank_cols, sample_cols = E.Columns(blank_xml), E.Columns(sample_xml)
    log.append(f"blank         : {Path(args.blank).name} ({fam})")
    log.append(f"sample        : {Path(args.sample).name}")

    drift = standard_diff(blank_cols, sample_cols)
    if drift:
        raise SystemExit("STOP: the sample's standard sections do not read as the current blank's - it was "
                         "built on another blank or an older version, and copying its body would bring that "
                         "wording back. A person decides (refill from the blank, or update the sample):\n  "
                         + "\n  ".join(drift))
    log.append(f"standard      : the sample's standard sections read exactly as the blank "
               f"({len(E.texts(blank_cols.left))} labels and {len(E.texts(blank_cols.right))} lines compared)")
    try:
        E.check_structure(sample_cols, "the sample")
    except SystemExit as e:
        raise SystemExit(f"STOP: {e}")
    blank_secs = {d: (lab, lines) for _, d, lab, lines in section_lines(blank_cols)}
    for heading, dwelling, labels, lines in section_lines(sample_cols):
        log.append(f"section       : {heading} - {len(labels)} label(s), {len(lines)} line(s)")
        base = blank_secs.get(dwelling) or blank_secs.get("single") or blank_secs.get("main")
        if dwelling == "aux" or base is None:
            flags.append(f"{heading}: all {len(lines)} line(s) come from the sample (the blank has no such "
                         f"section) - copied as the sample words them")
            continue
        extra = [l for l in lines if l not in base[1]]
        gone = [l for l in base[1] if l not in lines]
        if extra or gone:
            flags.append(f"{heading}: {len(extra)} line(s) the blank does not have"
                         + (f" ({'; '.join(x[:50] for x in extra[:3])}{' ...' if len(extra) > 3 else ''})" if extra else "")
                         + (f", {len(gone)} of the blank's not in the sample" if gone else ""))
    flags.append("the sample's upgrade wording is copied as it stands: room names and items that depend on this "
                 "job's plans (26061: \"Bathroom 2\", \"and Ensuite\") are a person's check")

    a, b = E.body_table(E.normalise_self_closing(sample_xml))
    body = E.normalise_self_closing(sample_xml)[a:b]
    refs = references(args.blank, args.sample, body)
    if refs:
        raise SystemExit("STOP: the sample's body points to definitions the blank does not have - "
                         + "; ".join(refs))
    client = client_of(sample_xml)
    toks = tokens(client, job)
    hits = scan({"sample body": [norm(PARA_TEXT(p)) for p in E.P_RE.findall(body)]}, toks)
    if hits:
        raise SystemExit("STOP: the sample's specification names its own client - edit the sample or the "
                         "document by hand:\n  " + "\n  ".join(f"{lab}: {line!r}" for lab, _, line in hits[:10]))
    log.append(f"client        : the sample's client details ({len(client['lot'])} lot, "
               f"{len(client['street'])} street, {len(client['owners'])} owner name(s), "
               f"{len(client['price'])} price) appear nowhere in its specification")

    sample_xml = heading_colour(blank_xml, sample_xml, log)
    base_xml = with_body(blank_xml, sample_xml)
    out = Path(args.out_blank)
    if out.exists() and E.read_xml(out) == base_xml:
        log.append(f"base          : {out.name} (unchanged - its Word measurement is reused)")
    else:
        E.write_docx(args.blank, out, base_xml)
        log.append(f"base          : {out.name} - the blank with the sample's specification")
    if args.docx:
        filled = E.read_xml(args.docx)
        E.write_docx(args.docx, args.docx, with_body(filled, sample_xml))
        log.append(f"document      : {Path(args.docx).name} - the sample's specification in place of the blank's; "
                   f"the request's removals, the layout pass and the gate follow")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blank")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out-blank")
    ap.add_argument("--docx", help="the filled document: its body becomes the sample's")
    ap.add_argument("--report")
    ap.add_argument("--scan", help="a finished document: fail if it names the sample's client")
    args = ap.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))

    if args.scan:
        toks = tokens(client_of(E.read_xml(args.sample)), job)
        hits = scan(parts_text(args.scan), toks)
        if hits:
            print("sample scan   : FAIL - the document names the sample's client:")
            for lab, where, line in hits[:10]:
                print(f"  {lab} in {where}: {line!r}")
            return 1
        print(f"sample scan   : none of the sample's client details ({len(toks)} checked) in "
              f"{Path(args.scan).name} - body, text boxes, headers, footers")
        return 0

    if not (args.blank and args.out_blank):
        ap.error("--blank and --out-blank are required (or --scan)")
    log, flags = [], []
    try:
        rc = build(args, job, log, flags)
    except SystemExit as e:
        msg = str(e)
        lines = log + ["", msg if msg.startswith("STOP") else f"STOP: {msg}", "Nothing written."]
        text = "\n".join(lines) + "\n"
        print(text)
        if args.report:
            Path(args.report).write_text(text, encoding="utf-8")
        return 1
    lines = [f"sample_base   : another job's inclusions as this job's base (CD-6.6)"] + log
    if flags:
        lines += ["", "TO CONFIRM:"] + [f"  - {f}" for f in flags]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    return rc


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
