r"""Fill the NSW/HIA build contract Word template from a job JSON. Stdlib only.

    python fill_hia.py --template <blank.docx> --job <job.json> --out <filled.docx>
    python fill_hia.py --template <blank.docx> --job <job.json> --check

STATUS: EXPERIMENTAL - commissioning tests only (CD-5.2b). The only Word
build-contract blanks that exist are the repaired conversions in
runtime\contract-admin\outputs\_hia-word-templates\, and they are UNAPPROVED
until a person finishes the layout review and MCR approves. A fill from this
script goes to the template-testing folder and nowhere else; nothing it
produces is issuable. Once an approved blank lands in the CONTRACT template
folder, this script gets regression-verified against it and against completed
contracts before the driver ever calls it.

What it fills (label-anchored, value typed after the printed label - the same
technique as fill_inclusions.py / fill_prelim.py):

  cover        OWNERS: / JOB: / LOT: / SITE:
  Schedule 1   item 3 Owners: NAME, ADDRESS, SUBURB, STATE, POSTCODE,
               MOBILE, EMAIL  (ABN/ACN, WORK, HOME left blank)
  The Land     LOT, DP NO, STREET ADDRESS:, SUBURB POSTCODE
  item 11      liquidated damages, typed before "per working day"

What it NEVER fills (CD-5.4): date, contract price / GST / total, deposit,
interest %, builder's margin %, progress payments - FROM DATABUILD or keyed
by a person. The building period and initial period carry the template's own
prefills and are left untouched for the reviewer.

Anchor discipline as everywhere else: --check first; a missing anchor is a
revised template and stops the fill.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

T_RE = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
P_RE = re.compile(r"<w:p\b[^>]*>(?:(?!</w:p>|<w:p\b).)*?</w:p>", re.S)


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def para_text(p_xml):
    return " ".join(html.unescape(m.group(1)) for m in T_RE.finditer(p_xml))


# (field, label, mode) per scope. Scope None = whole document, first hit.
# mode "after"  : value typed after the label text, same text node
# mode "before" : value typed before the label text (liquidated damages)
COVER = [
    ("owners",   "OWNERS:", "after"),
    ("job_no",   "JOB:",    "after"),
    ("lot_no",   "LOT:",    "after"),
    ("site_hia", "SITE:",   "after"),
]
OWNERS_SCOPE = ("3. Owners", "4. Builder")
OWNERS = [
    ("owner_1",       "NAME",     "after"),
    ("owner_address", "ADDRESS",  "after"),
    ("owner_suburb",  "SUBURB",   "after"),
    ("owner_state",   "STATE",    "after"),
    ("owner_postcode", "POSTCODE", "after"),
    ("owner_mobile",  "MOBILE",   "after"),
    ("owner_email",   "EMAIL",    "after"),
]
LAND_SCOPE = ("THE LAND IS:", "must reach the stage")
LAND = [
    ("lot_no",        "LOT",             "after"),
    ("dp_no",         "DP NO",           "after"),
    ("land_street",   "STREET ADDRESS:", "after"),
    ("land_suburb_pc", "SUBURB POSTCODE", "after"),
]
# item 11 carries the template's own prefill ("$25.00 per working day") -
# a job whose sourced LD differs REPLACES the figure, and the report flags it
LIQ = ("liq_damages", "per working day", "replace_amount")
AMOUNT_RE = re.compile(r"\$[\d,]+\.\d{2}")


def fill_para(p_xml, label, value, mode):
    """Type value beside the first occurrence of label in this paragraph."""
    esc = xml_escape(value)
    done = [False]

    def sub(m):
        if done[0]:
            return m.group(0)
        text = m.group(1)
        plain = html.unescape(text)
        if mode == "replace_amount":
            if not AMOUNT_RE.search(plain):
                return m.group(0)
        elif label not in plain:
            return m.group(0)
        done[0] = True
        if mode == "after":
            new = plain.replace(label, f"{label}  {value}", 1)
        elif mode == "replace_amount":
            if not AMOUNT_RE.search(plain):
                done[0] = False
                return m.group(0)
            new = AMOUNT_RE.sub(value, plain, count=1)
        else:
            new = plain.replace(label, f"{value} {label}", 1)
        return m.group(0).replace(m.group(1), xml_escape(new), 1)

    out = T_RE.sub(sub, p_xml)
    return (out, True) if done[0] else (p_xml, False)


def run(template, job, out_path, check_only):
    values = json.loads(Path(job).read_text(encoding="utf-8"))
    xml = __import__("zipfile").ZipFile(template).read("word/document.xml").decode("utf-8")
    paras = [(m.start(), m.end(), m.group(0)) for m in P_RE.finditer(xml)]

    # resolve each field to (paragraph index, label, value, mode)
    plan, missing_anchor, blank_fields = [], [], []

    def texts():
        return [para_text(p) for _, _, p in paras]

    ptexts = texts()

    def first_hit(label, lo=0, hi=None):
        for i in range(lo, hi if hi is not None else len(ptexts)):
            if label in ptexts[i]:
                return i
        return None

    def scope_bounds(scope):
        if scope is None:
            return 0, len(ptexts)
        lo = first_hit(scope[0])
        if lo is None:
            return None, None
        hi = first_hit(scope[1], lo + 1)
        return lo, (hi if hi is not None else len(ptexts))

    groups = [(None, COVER), (OWNERS_SCOPE, OWNERS), (LAND_SCOPE, LAND)]
    for scope, fields in groups:
        lo, hi = scope_bounds(scope)
        if lo is None:
            missing_anchor.append(f"scope {scope[0]!r} not found")
            continue
        for key, label, mode in fields:
            val = str(values.get(key, "") or "").strip()
            idx = None
            for i in range(lo, hi):
                if re.search(rf"(^|\s){re.escape(label)}", ptexts[i]):
                    idx = i
                    break
            if idx is None:
                missing_anchor.append(f"{key}: label {label!r} not in scope {scope and scope[0]}")
                continue
            if not val:
                blank_fields.append((key, label))
                continue
            plan.append((idx, key, label, val, mode))

    # liquidated damages: the paragraph with both halves of the item
    key, label, mode = LIQ
    val = str(values.get(key, "") or "").strip()
    idx = next((i for i, t in enumerate(ptexts)
                if label in re.sub(" +", " ", t) and AMOUNT_RE.search(t)), None)
    if idx is None:
        missing_anchor.append(f"{key}: liquidated-damages paragraph not found")
    elif val:
        plan.append((idx, key, label, val, mode))
    else:
        blank_fields.append((key, label))

    print(f"template : {Path(template).name}")
    print(f"job      : {Path(job).name}")
    print(f"STATUS   : EXPERIMENTAL (CD-5.2b) - template-testing only, never issuable")
    print()
    print(f"{'field':<16} {'para':>5}  {'label':<18} value")
    print("-" * 78)
    for idx, key, label, val, mode in sorted(plan):
        print(f"{key:<16} {idx:>5}  {label:<18} {val[:40]}")
    for key, label in blank_fields:
        print(f"{key:<16} {'-':>5}  {label:<18} (no value - left blank)")
    if missing_anchor:
        print()
        for msg in missing_anchor:
            print(f"ANCHOR MISSING: {msg}")
        print("The template has been revised (or is not the expected blank) - stopping.")
        return 1
    if check_only:
        print("\n(--check: nothing written)")
        return 0

    # apply, back-to-front so offsets stay valid; all fills for one
    # paragraph compose on the same XML before it is spliced back once
    by_para = {}
    for idx, key, label, val, mode in plan:
        by_para.setdefault(idx, []).append((key, label, val, mode))
    for idx in sorted(by_para, reverse=True):
        start, end, p_xml = paras[idx]
        for key, label, val, mode in by_para[idx]:
            p_xml, ok = fill_para(p_xml, label, val, mode)
            if not ok:
                print(f"FILL FAILED at paragraph {idx} for {key} - stopping, nothing written")
                return 1
        xml = xml[:start] + p_xml + xml[end:]

    import shutil
    import zipfile
    shutil.copy2(template, out_path)
    tmp = Path(str(out_path) + ".tmp")
    with zipfile.ZipFile(out_path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = (xml.encode("utf-8") if item.filename == "word/document.xml"
                    else zin.read(item.filename))
            zout.writestr(item, data)
    tmp.replace(out_path)
    print(f"\nwritten  : {out_path}")
    print("TEST ARTIFACT from an UNAPPROVED template - a person must review it "
          "against the licensed PDF; it is not issuable.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not args.check and not args.out:
        sys.exit("ERROR: give --out or --check")
    return run(args.template, args.job, args.out, args.check)


# This console is cp1252; contract text carries curly quotes and dashes.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
