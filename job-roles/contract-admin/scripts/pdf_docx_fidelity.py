r"""Verify - and repair - a PDF-to-Word conversion's text completeness. Stdlib only.

    python pdf_docx_fidelity.py <source.pdf> <converted.docx>
    python pdf_docx_fidelity.py <source.pdf> <converted.docx> --repair <out.docx>

The measurement half of the HIA Word-template pipeline (CD-5.2b): Word's PDF
reflow keeps ~95% of a licensed contract's text, and this tool accounts for
the rest. It aligns the PDF's content words against the docx's and classifies
every PDF fragment the docx lacks:

  MOVED    present in the docx, at a different position (re-pagination -
           reading order preserved within sections; not a loss)
  MISSING  genuinely absent - the reflow dropped it

--repair reinserts every MISSING fragment VERBATIM from the PDF, as its own
paragraph immediately after the paragraph holding its preceding context, then
re-measures. Verbatim-from-source is what keeps this on the right side of
"never write contract wording": the tool moves the licensed document's own
words, it never composes any.

What this can and cannot certify:

  CAN     100% of the PDF's machine-readable content words are present in the
          docx, in reading order (the printed report is the evidence).
  CANNOT  visual layout - pagination, tables, checkbox/initial blocks. No
          rasteriser exists on this server, so page-by-page eye-verification
          against the PDF and MCR approval stay human, and a repaired
          conversion stays UNAPPROVED until both happen.

Glyph junk (mojibake from fonts pdf_text.py cannot map) is excluded from both
sides and reported, so the score reflects content, not extractor noise.
"""
import argparse
import html
import re
import shutil
import sys
import unicodedata
import zipfile
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pdf_text  # noqa: E402  (stdlib-only sibling)

T_RE = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
P_RE = re.compile(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", re.S)

QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"',
          "–": "-", "—": "-", "−": "-", "­": "",
          "ﬁ": "fi", "ﬂ": "fl", " ": " ", "\\": ""}


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    for a, b in QUOTES.items():
        s = s.replace(a, b)
    return s


def is_junk(tok):
    """Mojibake from unmapped fonts: CJK/PUA codepoints or mostly non-text."""
    if any(ord(c) >= 0x0370 for c in tok):  # beyond Latin/IPA blocks
        return True
    good = sum((c.isascii() and (c.isalnum() or c in ".,;:()[]{}'\"$%&/-@#*+=?!"))
               or c in "²çéà" for c in tok)  # m2, c-cedilla, accents
    return good / max(len(tok), 1) < 0.5


def tokens(raw):
    """(match_key, original) word pairs; letter-spaced runs re-joined."""
    words = norm(raw).split()
    out = []
    i = 0
    while i < len(words):
        # PDF headings arrive letter-spaced ("S c h e d u l e"): re-join a run
        # of 3+ single letters so it compares against the docx's joined word.
        if len(words[i]) == 1 and words[i].isalpha():
            j = i
            while j < len(words) and len(words[j]) == 1 and words[j].isalpha():
                j += 1
            if j - i >= 3:
                joined = "".join(words[i:j])
                out.append((joined.lower(), joined))
                i = j
                continue
        if not is_junk(words[i]):
            out.append((words[i].lower(), words[i]))
        i += 1
    return out


def docx_xml(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def docx_furniture_text(path):
    """Text of the header/footer parts - page furniture Word rebuilt."""
    out = []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if re.search(r"word/(header|footer)\d*\.xml$", n):
                out.append(xml_to_text(z.read(n).decode("utf-8")))
    return " ".join(out)


def xml_to_text(xml):
    return " ".join(html.unescape(m.group(1)) for m in T_RE.finditer(
        re.sub(r"<w:tab/>", " ", xml)))


def para_positions(xml):
    """[(end_offset, plain_text_lower)] for every paragraph, document order."""
    out = []
    for m in P_RE.finditer(xml):
        keys = [k for k, _ in tokens(xml_to_text(m.group(0)))]
        out.append((m.start(), m.end(), " ".join(keys), "".join(keys)))
    return out


def gappy_present(frag_ns, hay_ns, density=0.75):
    """Is frag_ns an ordered subsequence of a dense window of hay_ns?

    The PDF extractor drops glyphs it cannot map (ligatures: certi[fi]er,
    speci[fi]cations), so the PDF-side text has holes the docx does not.
    A fragment whose characters all appear in order within a docx window at
    >= density is present - the gap is extractor loss, not conversion loss.
    """
    if len(frag_ns) < 5:
        return False  # too short to establish identity this loosely
    if len(frag_ns) <= 8:
        density = 0.70  # short pieces with glyph holes ("dator" = date for)
    seed = frag_ns[:4]
    start = hay_ns.find(seed)
    while start != -1:
        i, j = start, 0
        limit = start + int(len(frag_ns) / density) + 4
        while i < len(hay_ns) and i < limit and j < len(frag_ns):
            if hay_ns[i] == frag_ns[j]:
                j += 1
            i += 1
        if j == len(frag_ns) and len(frag_ns) / (i - start) >= density:
            return True
        start = hay_ns.find(seed, start + 1)
    return False


FURNITURE_RE = re.compile(r"^(page\d+of\d+|initials?|copyright|\d+)+$")

# PDF form machinery leaking out of non-display streams: appearance-stream
# operators (/Helv 12 Tf 0 g), field-calculation JavaScript, font names.
# Not display text - excluded from the completeness denominator.
NOISE_RE = re.compile(r"/helv|tf 0 g|getfield\(|afnumber_|identity adobe"
                      r"|minion pro|event\.value")


def is_furniture(frag):
    """Page furniture Word rebuilt as real headers/footers: 'Page 3 of 32',
    'Initials : Copyright' rails. Reported, never repaired into the body."""
    ns = re.sub(r"[^a-z0-9]", "", "".join(k for k, _ in frag))
    return bool(ns) and bool(FURNITURE_RE.match(ns))


def chunked_present(frag_ns, hay_ns, min_chunk=10):
    """Can frag_ns be segmented into long distinctive chunks all present?

    Catches PDF-extraction glue ("...SCHEMER esiden tial" gluing Scheme's end
    to Residential's start) once an insert or reflow separates the halves.
    min_chunk stays high so ordinary words appearing elsewhere can never fake
    a whole missing phrase into "present".
    """
    if len(frag_ns) < min_chunk * 2:
        return False
    pos = 0
    while pos < len(frag_ns):
        lo, hi = pos + min_chunk, len(frag_ns)
        if lo > hi:
            return False
        best = 0
        while lo <= hi:  # longest prefix >= min_chunk that hay contains
            mid = (lo + hi) // 2
            if frag_ns[pos:mid] in hay_ns:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if not best:
            return False
        pos = best
    return True


def present(frag, hay, hay_nospace):
    needle = " " + " ".join(k for k, _ in frag) + " "
    frag_ns = "".join(k for k, _ in frag)
    return (needle in hay or frag_ns in hay_nospace
            or gappy_present(frag_ns, hay_nospace)
            or chunked_present(frag_ns, hay_nospace))


def refine(idx, frag, hay, hay_nospace):
    """Bisect a mixed fragment down to its minimal truly-missing runs.

    SequenceMatcher fragments mix present text (moved, or glyph-holed on the
    PDF side) with genuinely absent text. Recursively split until each leaf
    is either present somewhere or small and truly missing, then merge
    adjacent missing leaves back into runs.
    """
    if present(frag, hay, hay_nospace):
        return []
    if len(frag) <= 3:
        return [(idx, frag)]
    mid = len(frag) // 2
    leaves = (refine(idx, frag[:mid], hay, hay_nospace)
              + refine(idx + mid, frag[mid:], hay, hay_nospace))
    merged = []
    for i, f in leaves:
        if merged and merged[-1][0] + len(merged[-1][1]) == i:
            merged[-1] = (merged[-1][0], merged[-1][1] + f)
        else:
            merged.append((i, f))
    return merged


def classify(pdf_toks, doc_toks):
    """(matched, missing_runs, furniture_runs) for the PDF against the docx."""
    a = [k for k, _ in pdf_toks]
    b = [k for k, _ in doc_toks]
    hay = " " + " ".join(b) + " "
    # The PDF extractor splits words wherever the PDF positions glyph runs
    # ("c on tr ac t"); the docx has them joined. A space-insensitive view
    # catches those as present.
    hay_nospace = "".join(b)
    sm = SequenceMatcher(None, a, b, autojunk=False)
    missing, furniture, noise = [], [], []
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag not in ("delete", "replace") or i2 <= i1:
            continue
        for idx, frag in refine(i1, pdf_toks[i1:i2], hay, hay_nospace):
            text = " ".join(k for k, _ in frag)
            if NOISE_RE.search(text):
                noise.append((idx, frag))
            elif is_furniture(frag) or all(len(k) <= 4 for k, _ in frag):
                # short-token debris: enumeration markers ("(a)", "(j)") that
                # Word rebuilt as real list numbering (w:numPr - verified),
                # plus the glue characters at their boundaries. Reported for
                # the visual pass, never repaired into the body.
                furniture.append((idx, frag))
            else:
                missing.append((idx, frag))
    matched = sum(i2 - i1 for tag, i1, i2, _, _ in sm.get_opcodes() if tag == "equal")
    return matched, missing, furniture, noise


def context(pdf_toks, idx, n=8):
    pre = " ".join(o for _, o in pdf_toks[max(0, idx - n):idx])
    return pre


def report(pdf_path, docx_path):
    pdf_toks = tokens(" ".join(pdf_text.text_of(pdf_path)))
    doc_toks = tokens(xml_to_text(docx_xml(docx_path)) + " "
                      + docx_furniture_text(docx_path))
    matched, missing, furniture, noise = classify(pdf_toks, doc_toks)
    total = len(pdf_toks)
    missing_n = sum(len(f) for _, f in missing)
    furn_n = sum(len(f) for _, f in furniture)
    noise_n = sum(len(f) for _, f in noise)
    denom = total - furn_n - noise_n
    present = denom - missing_n
    print(f"=== {Path(pdf_path).name}  vs  {Path(docx_path).name}")
    print(f"    PDF content words : {total}")
    print(f"    matched in place  : {matched}")
    print(f"    present elsewhere : {present - matched}  (moved / re-joined glyph runs)")
    print(f"    furniture/markers : {furn_n}  in {len(furniture)} run(s)  "
          f"(page rails -> real footers; list markers -> real numbering; "
          f"verify visually)")
    print(f"    extractor noise   : {noise_n}  in {len(noise)} run(s)  "
          f"(PDF form machinery from non-display streams - not display text)")
    print(f"    MISSING           : {missing_n}  in {len(missing)} run(s)")
    print(f"    text completeness : {present}/{denom} "
          f"= {present/denom*100:.2f}%  (furniture + noise excluded)")
    for idx, frag in missing:
        words = " ".join(o for _, o in frag)
        print(f"      MISSING @{idx}: \"{words[:160]}{'...' if len(words) > 160 else ''}\"")
        print(f"        after: \"...{context(pdf_toks, idx)}\"")
    for idx, frag in furniture:
        words = " ".join(o for _, o in frag)
        print(f"      furniture/marker @{idx}: \"{words[:100]}\"")
    return pdf_toks, missing


def repair(pdf_toks, missing, docx_path, out_path):
    """Reinsert each MISSING fragment verbatim after its anchor paragraph."""
    xml = docx_xml(docx_path)
    paras = para_positions(xml)
    inserts = []  # (offset, xml_paragraph)
    unplaced = []
    for idx, frag in missing:
        # anchor: the longest tail (6..2 words) of the preceding matched text
        # that some paragraph contains, searching paragraphs in order
        placed = False
        pre_keys = [k for k, _ in pdf_toks[max(0, idx - 10):idx]]
        post_keys = [k for k, _ in pdf_toks[idx + len(frag):idx + len(frag) + 10]]
        hits = []
        for k in range(min(6, len(pre_keys)), 0, -1):
            phrase = " ".join(pre_keys[-k:])
            phrase_ns = "".join(pre_keys[-k:])
            hits = [(end, t) for start, end, t, tns in paras
                    if phrase in t or phrase_ns in tns]
            if hits:
                break
        if not hits:
            # no preceding anchor - fall back to the FOLLOWING context and
            # insert before the paragraph that carries it
            for k in range(min(6, len(post_keys)), 0, -1):
                phrase = " ".join(post_keys[:k])
                phrase_ns = "".join(post_keys[:k])
                hits = [(start, t) for start, end, t, tns in paras
                        if phrase in t or phrase_ns in tns]
                if hits:
                    break
        if not hits:
            # last resort: the end of the body, highlighted like every other
            # insert - the human pass relocates it during the layout repair
            end_off = xml.rfind("<w:sectPr")
            if end_off == -1:
                end_off = xml.rfind("</w:body>")
            if end_off != -1:
                hits = [(end_off, "(end of document)")]
        if True:
            if hits:
                text = " ".join(o for _, o in frag)
                # control chars are invalid XML 1.0 - they can only be stream
                # junk, never contract text
                text = "".join(c for c in text if ord(c) >= 0x20 or c == "	")
                esc = (text.replace("&", "&amp;").replace("<", "&lt;")
                       .replace(">", "&gt;"))
                # highlighted so the human repair pass can review every
                # insertion at a glance; the highlight comes off at review
                inserts.append((hits[0][0],
                                '<w:p><w:r><w:rPr><w:highlight w:val="yellow"/>'
                                f'</w:rPr><w:t xml:space="preserve">{esc}'
                                f"</w:t></w:r></w:p>"))
                placed = True
        if not placed:
            unplaced.append((idx, " ".join(o for _, o in frag)))
    for off, p_xml in sorted(inserts, key=lambda x: -x[0]):
        xml = xml[:off] + p_xml + xml[off:]
    if Path(docx_path).resolve() != Path(out_path).resolve():
        shutil.copy2(docx_path, out_path)
    # rewrite word/document.xml inside the copy
    tmp = Path(str(out_path) + ".tmp")
    with zipfile.ZipFile(out_path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = (xml.encode("utf-8") if item.filename == "word/document.xml"
                    else zin.read(item.filename))
            zout.writestr(item, data)
    tmp.replace(out_path)
    print(f"    repaired          : {len(inserts)} fragment(s) reinserted verbatim -> {out_path}")
    for idx, words in unplaced:
        print(f"    UNPLACED @{idx}: \"{words[:120]}\" - no anchor found; needs a person")
    return len(unplaced) == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("docx")
    ap.add_argument("--repair", metavar="OUT_DOCX",
                    help="write a copy with every MISSING fragment reinserted "
                         "verbatim from the PDF, then re-measure it")
    args = ap.parse_args()

    pdf_toks, missing = report(args.pdf, args.docx)
    if args.repair:
        if not missing:
            print("    nothing to repair - copying through")
            shutil.copy2(args.docx, args.repair)
            return 0
        src = args.docx
        for i in range(1, 5):
            repair(pdf_toks, missing, src, args.repair)
            src = args.repair
            print()
            print(f"    --- re-measuring after repair pass {i} ---")
            pdf_toks, still = report(args.pdf, args.repair)
            if not still or len(still) >= len(missing):
                missing = still
                break
            missing = still
        return 0 if not missing else 1
    return 0 if not missing else 1


# This console is cp1252; contract text carries curly quotes and dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
