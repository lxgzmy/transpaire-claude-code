r"""Street names on a plan set's site plan: the corner-block prompt for the
inclusions' GARAGE SIDE (CD-2.9 / JD-9.5, issue #59). Stdlib only.

    python site_streets.py <plans.pdf> [--street "<the lot's street>"] [--json]

On a Sydney corner block or a lot with a rear lane, GARAGE SIDE reads
"Via <the street or lane the driveway uses>" (the team's practice in every
such completed job, and the 26032 review). Which street that is shows only
in the drawing, so the run always renders the site-plan page
(pdf_page.ps1) and reads it. This script finds that page and lists the
street names labelled on it, so a second frontage or a lane is not missed
on a quick look:

  CORNER     two or more street names on the site plan
  REAR LANE  a lane label that is not the lot's own street
  SINGLE     one street
  NONE       no street label read (a scanned plan, an unusual font)

Labels are read per text object (one BT..ET block = one label), and the
whole label must be a street name, so a title block's address line, a note
mentioning a road, or the office address never counts; a label the other
sheets print as often as the site plan does (a title block's) is dropped. A
lane drawn but not named (26058) reads SINGLE here: the
verdict is a prompt to look at the picture, never the answer.
"""
import argparse
import json
import re
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pdf_fields import objects  # noqa: E402
from pdf_text import SHOW, decode, printable_ratio, unescape  # noqa: E402

SUFFIX = {"rd": "Road", "st": "Street", "ave": "Avenue", "av": "Avenue", "dr": "Drive", "cl": "Close",
          "cres": "Crescent", "cr": "Crescent", "pde": "Parade", "ln": "Lane", "bvd": "Boulevard",
          "blvd": "Boulevard", "cct": "Circuit", "pl": "Place", "tce": "Terrace", "ct": "Court",
          "gr": "Grove", "hwy": "Highway", "pkwy": "Parkway", "sq": "Square", "esp": "Esplanade"}
TYPES = ("Road|Street|Avenue|Drive|Way|Close|Crescent|Parade|Lane|Laneway|Boulevard|Circuit|Place|"
         "Terrace|Parkway|Court|Grove|Rise|Loop|Row|Mews|Glade|Chase|Esplanade|Highway|Square|Walk|"
         "Promenade|Vista|Link|Crest|Ridge|View|Gardens")
STREET_RE = re.compile(rf"^(?:[A-Z][A-Za-z']*\s+){{0,3}}(?:{TYPES}|{'|'.join(SUFFIX)})\.?$", re.I)
NUMBERED_RE = re.compile(r"^(?:Road|Street|Lane)\s+\d+$", re.I)
LANE_RE = re.compile(r"(?:^|\s)(?:Lane|Laneway)$", re.I)
SITE_RE = re.compile(r"\bsite\s*(?:plan\b|&|and\b)", re.I)


def tidy(label):
    """Title case, abbreviations spelt out: 'SAMPLE RD' -> 'Sample Road'."""
    words = label.replace(".", "").split()
    last = SUFFIX.get(words[-1].lower())
    if last:
        words[-1] = last
    return " ".join(w if w.isdigit() else w[:1].upper() + w[1:].lower() for w in words)


def is_street(label):
    return bool(STREET_RE.match(label) or NUMBERED_RE.match(label)
                or label.lower() in ("lane", "laneway", "rear lane"))


def _stream(body):
    m = re.search(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S)
    if not m:
        return b""
    data = m.group(1)
    if b"/FlateDecode" in body[:m.start()]:
        try:
            return zlib.decompress(data)
        except zlib.error:
            return b""
    return data


def _refs(blob):
    return [int(n) for n in re.findall(rb"(\d+)\s+0\s+R", blob)]


def _labels(content):
    out = []
    for block in re.findall(rb"\bBT\b(.*?)\bET\b", content, re.S):
        parts = []
        for m in SHOW.finditer(block):
            tok = m.group(0)
            if tok[:1] == b"<":
                h = re.sub(rb"\s", b"", tok[1:-1])
                piece = decode(bytes.fromhex((h + b"0" * (len(h) % 2)).decode("ascii")))
            else:
                piece = decode(unescape(tok[1:-1]))
            parts.append(piece)
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        if text and printable_ratio(text) > 0.9:
            out.append(text)
    return out


def pages(data):
    """[[label, ...] per page] in page order (last definition of each object wins)."""
    objs = {}
    for num, body, _ in objects(data):
        objs[num] = body
    root = next((b for b in objs.values() if re.search(rb"/Type\s*/Catalog", b)), None)
    top = re.search(rb"/Pages\s+(\d+)\s+0\s+R", root or b"")
    if not top:
        return []

    def contents(body, depth=0):
        streams = []
        c = re.search(rb"/Contents\s*(\[[^\]]*\]|\d+\s+0\s+R)", body)
        for ref in _refs(c.group(1)) if c else []:
            target = objs.get(ref, b"")
            # an indirect array of content streams
            if target.lstrip().startswith(b"[") and b"stream" not in target:
                streams += [_stream(objs.get(r, b"")) for r in _refs(target)]
            else:
                streams.append(_stream(target))
        # drawings placed as Form XObjects (the site plan often is one)
        res = re.search(rb"/Resources\s*(\d+)\s+0\s+R", body)
        res_body = objs.get(int(res.group(1)), b"") if res else body
        xo = re.search(rb"/XObject\s*(<<.*?>>|\d+\s+0\s+R)", res_body, re.S)
        if xo and depth < 3:
            xo_body = xo.group(1)
            if not xo_body.startswith(b"<<"):
                xo_body = objs.get(_refs(xo_body)[0], b"")
            for ref in _refs(xo_body):
                form = objs.get(ref, b"")
                if re.search(rb"/Subtype\s*/Form", form):
                    streams.append(_stream(form))
                    streams += contents(form, depth + 1)   # forms inside the form
        return streams

    out, seen = [], set()

    def walk(num):
        if num in seen:
            return
        seen.add(num)
        body = objs.get(num, b"")
        if re.search(rb"/Type\s*/Pages\b", body):
            kids = re.search(rb"/Kids\s*\[([^\]]*)\]", body)
            for ref in _refs(kids.group(1)) if kids else []:
                walk(ref)
        elif re.search(rb"/Type\s*/Page\b", body):
            labels = []
            for s in contents(body):
                if b"Tj" in s or b"TJ" in s:
                    labels += _labels(s)
            out.append(labels)

    walk(int(top.group(1)))
    return out


def same_street(a, b):
    def key(s):
        return re.sub(r"[^a-z]", "", tidy(re.sub(r"[\d()]", " ", s).strip() or "x").lower())
    return bool(a and b) and key(a) == key(b)


def analyse(pdf, street=""):
    labels = pages(Path(pdf).read_bytes())
    if not labels:
        return {"pages": 0, "site_page": None, "streets": [], "verdict": "NONE",
                "why": "no page tree or no text could be read"}
    site = next((i for i, ls in enumerate(labels) if any(SITE_RE.search(l) for l in ls)), 0)
    # a title block repeats its labels on every sheet: a label counts only
    # when the site plan carries it more often than every other sheet does
    others = [ls for i, ls in enumerate(labels) if i != site]
    streets = []
    for label in labels[site]:
        extra = labels[site].count(label) > min((ls.count(label) for ls in others), default=0)
        if extra and is_street(label) and tidy(label) not in streets:
            streets.append(tidy(label))
    lanes = [s for s in streets if LANE_RE.search(s) and not same_street(s, street)]
    others = [s for s in streets if s not in lanes]
    if lanes:
        verdict, why = "REAR LANE", "a lane is labelled on the site plan besides the lot's street"
    elif len(others) >= 2:
        verdict, why = "CORNER", "two or more streets are labelled on the site plan"
    elif others:
        verdict, why = "SINGLE", "one street is labelled on the site plan"
    else:
        verdict, why = "NONE", "no street label on the site plan"
    return {"pages": len(labels), "site_page": site + 1, "streets": streets, "verdict": verdict, "why": why}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--street", default="", help="the lot's own street, so its name is not taken for a lane")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = analyse(args.pdf, args.street)
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    print(f"site plan : page {r['site_page']} of {r['pages']}")
    print(f"streets   : {', '.join(r['streets']) or '(none read)'}")
    print(f"verdict   : {r['verdict']} - {r['why']}")
    if r["verdict"] in ("CORNER", "REAR LANE"):
        print("garage    : read the rendered site plan for the street or lane the driveway crosses;"
              " GARAGE SIDE = \"Via <that name>\" (CD-2.9). Unclear -> leave it blank and flag the streets above.")
    else:
        print("garage    : read the rendered site plan - Left / Right Hand Side facing the house, or \"Via <lane>\""
              " if a lane the text does not name shows in the drawing (CD-2.9).")
    print(f"render    : powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"{HERE / 'pdf_page.ps1'}\""
          f" -Pdf \"<plans.pdf>\" -Pages {r['site_page'] or 1} -OutDir \"<workdir>\\plans\"")
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    sys.exit(main())
