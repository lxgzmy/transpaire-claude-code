r"""Draw a DocuSign template's or draft's tabs onto a job's PDFs, for a person to check.

    python docusign_tab_overlay.py --recipients <recipients.json> --documents <documents.json>
                                   --pdf "BUILD CONTRACT=<file.pdf>" [--pdf "INCLUSIONS=<file.pdf>" ...]
                                   --out <folder under runtime\>

The six templates' tabs are fixed to a page and an x/y position, not anchored
(CD-10.5), so a tab lands where the template's placeholder had its line. This
tool shows where that is on the job's own PDF: one PNG per page that holds a
tab, each tab drawn as a box with its type and role, plus a summary of every
tab that falls past the document's last page (it would be missing in the
draft). Whether each tab sits on its line is a person's call from the images;
the summary only adds the text found under and beside each tab as a hint.

Inputs are DocuSign's own JSON, saved as returned by a read-only call:
  --recipients  recipients with tabs: a draft's (listRecipients with
                include_tabs=true) or a template's (assessTemplatesForDV,
                which holds them under "recipients")
  --documents   the matching documents: a draft's (listEnvelopeDocuments,
                "envelopeDocuments") or a template's (getTemplates with
                include=documents, "documents"), used to tell each
                document's kind by name (never by id or order)
  --template    the template name, when a saved file holds several templates
Only geometry leaves this tool: kind, page, tab type, role, x and y. Names,
emails, labels and values are never written.

Writes only under the checkout's runtime\ folder (git-ignored). Needs
pypdfium2 and Pillow, kept out of every server dependency list; the pure
functions below are covered by test_docusign_tab_overlay.py without them.
Exit codes: 0 written, 2 a refusal or a missing input.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[2] / "runtime"

KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")

# DocuSign places a tab by its top-left corner, in points from the page's top-left.
# The boxes are the rendered sizes at 100% scale, near enough to judge a line.
BOX = {"signHere": (90, 36), "initialHere": (40, 30), "dateSigned": (90, 14),
       "fullName": (120, 14), "text": (120, 14), "checkbox": (12, 12)}
DEFAULT_BOX = (80, 14)
COLOUR = {"signHere": (220, 30, 30), "initialHere": (30, 90, 220), "dateSigned": (20, 150, 60)}
DEFAULT_COLOUR = (120, 120, 120)
SHORT = {"signHere": "SIGN", "initialHere": "INIT", "dateSigned": "DATE", "fullName": "NAME",
         "text": "TEXT", "checkbox": "CHECK"}


class Refusal(Exception):
    """An input or destination this tool will not use."""


def kind_of(name):
    """The one kind whose words appear in a document name, else None (as the server matches)."""
    up = str(name).upper()
    hits = [k for k in KINDS if k in up]
    return hits[0] if len(hits) == 1 else None


def kinds_by_document_id(documents):
    """{documentId: kind} for the content documents; a name that matches no kind is left out."""
    out = {}
    for d in documents:
        if d.get("type", "content") != "content":
            continue
        kind = kind_of(d.get("name", ""))
        if kind:
            out[str(d.get("documentId"))] = kind
    return out


def _holders(obj, keys, kind):
    """Every dict in obj (at any depth) holding one of keys with a value of type kind."""
    found, stack = [], [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if any(isinstance(cur.get(k), kind) for k in keys):
                found.append(cur)
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return found


def _one(holders, template, what):
    if template is not None:
        holders = [h for h in holders if str(h.get("name", "")).strip() == template.strip()]
    seen, unique = set(), []
    for h in holders:  # the hosted reads can repeat a template in their own summary sections
        key = h.get("templateId") or h.get("envelopeId") or id(h)
        if key not in seen:
            seen.add(key)
            unique.append(h)
    holders = unique
    if len(holders) != 1:
        raise Refusal(f"the {what} file holds {len(holders)} matching sets of {what}; save one "
                      "template's or one draft's, or name the template with --template")
    return holders[0]


def _recipients(obj, template=None):
    holders = _holders(obj, ("recipients",), dict)
    if not holders and isinstance(obj, dict):  # a draft's listRecipients is the object itself
        return obj
    return _one(holders, template, "recipients")["recipients"]


def _documents(obj, template=None):
    if isinstance(obj, list):
        return obj
    holder = _one(_holders(obj, ("envelopeDocuments", "documents"), list), template, "documents")
    return holder.get("envelopeDocuments") or holder.get("documents")


def geometry(recipients, documents, template=None):
    """Every tab as {kind, page, type, role, x, y}: geometry only, nothing that names a person."""
    kinds = kinds_by_document_id(_documents(documents, template))
    tabs = []
    for items in (_recipients(recipients, template) or {}).values():
        if not isinstance(items, list):
            continue
        for r in items:
            role = str(r.get("roleName") or "(no role)")
            for list_name, entries in (r.get("tabs") or {}).items():
                if not isinstance(entries, list):
                    continue
                tab_type = list_name[:-4] if list_name.endswith("Tabs") else list_name
                for t in entries:
                    tabs.append({"kind": kinds.get(str(t.get("documentId")), "UNKNOWN"),
                                 "page": int(float(t.get("pageNumber") or 0)),
                                 "type": tab_type, "role": role,
                                 "x": int(float(t.get("xPosition") or 0)),
                                 "y": int(float(t.get("yPosition") or 0))})
    return tabs


def by_document(tabs, page_counts):
    """{kind: {"pages": n or None, "on_page": {page: [tabs]}, "past_end": [tabs]}}."""
    out = {}
    for t in tabs:
        doc = out.setdefault(t["kind"], {"pages": page_counts.get(t["kind"]),
                                         "on_page": defaultdict(list), "past_end": []})
        if doc["pages"] is not None and not 1 <= t["page"] <= doc["pages"]:
            doc["past_end"].append(t)
        else:
            doc["on_page"][t["page"]].append(t)
    return out


def box(tab):
    """(left, top, right, bottom) in points from the page's top-left."""
    w, h = BOX.get(tab["type"], DEFAULT_BOX)
    return tab["x"], tab["y"], tab["x"] + w, tab["y"] + h


def check_out_dir(out):
    """The output folder, which must sit under the checkout's runtime\\ folder."""
    out = Path(out).resolve()
    runtime = RUNTIME.resolve()
    if out != runtime and runtime not in out.parents:
        raise Refusal(f"--out must be under the checkout's runtime folder ({runtime}); "
                      "evidence never goes into the repo")
    return out


def parse_pdf_args(items):
    pdfs = {}
    for item in items:
        kind, sep, path = item.partition("=")
        kind = kind.strip().upper()
        if not sep or kind not in KINDS:
            raise Refusal(f"--pdf takes KIND=path with KIND one of {', '.join(KINDS)}; got {item!r}")
        if kind in pdfs:
            raise Refusal(f"--pdf names {kind} twice")
        pdfs[kind] = Path(path.strip())
    return pdfs


def summary_lines(docs, hints):
    lines = []
    for kind in KINDS + ("UNKNOWN",):
        doc = docs.get(kind)
        if not doc:
            continue
        pages = doc["pages"]
        total = sum(len(v) for v in doc["on_page"].values()) + len(doc["past_end"])
        lines.append(f"{kind}: {total} tabs, PDF pages: {pages if pages is not None else 'no PDF given'}")
        for page in sorted(doc["on_page"]):
            for t in doc["on_page"][page]:
                hint = hints.get(id(t), "")
                lines.append(f"    p{page:>2} {SHORT.get(t['type'], t['type']):<5} {t['role']:<26} "
                             f"x={t['x']:<4} y={t['y']:<4} {hint}")
        for t in doc["past_end"]:
            lines.append(f"    MISSING p{t['page']} (past the last page) {t['type']} {t['role']}")
    return lines


def render(pdfs, docs, out, scale):  # pragma: no cover - needs pypdfium2 and Pillow
    import pypdfium2 as pdfium
    from PIL import ImageDraw, ImageFont

    try:
        font = ImageFont.load_default(size=int(9 * scale))
    except TypeError:  # Pillow before 10.1 has one fixed-size default font
        font = ImageFont.load_default()
    hints = {}
    for kind, path in pdfs.items():
        doc = docs.get(kind)
        if not doc:
            continue
        pdf = pdfium.PdfDocument(str(path))
        for page_no, tabs in sorted(doc["on_page"].items()):
            page = pdf[page_no - 1]
            width, height = page.get_size()
            text = page.get_textpage()
            for t in tabs:
                left, top, right, bottom = box(t)
                # around the tab, in PDF space (origin bottom-left); words cut at the edge are a hint only
                found = text.get_text_bounded(left=max(0, left - 120), right=min(width, right + 160),
                                              bottom=max(0, height - bottom - 18),
                                              top=min(height, height - top + 18))
                hints[id(t)] = "text near: " + (" ".join(found.split())[:90] or "(none)")
            image = page.render(scale=scale).to_pil().convert("RGB")
            draw = ImageDraw.Draw(image)
            for t in tabs:
                left, top, right, bottom = (v * scale for v in box(t))
                colour = COLOUR.get(t["type"], DEFAULT_COLOUR)
                draw.rectangle([left, top, right, bottom], outline=colour, width=3)
                draw.ellipse([left - 4, top - 4, left + 4, top + 4], fill=colour)
                draw.text((left + 3, max(0, top - 11 * scale)), f"{SHORT.get(t['type'], t['type'])} {t['role']}",
                          fill=colour, font=font)
            draw.text((8, 8), f"{kind} page {page_no} of {len(pdf)}", fill=(0, 0, 0), font=font)
            name = f"{kind.replace(' ', '_')}_p{page_no:02d}.png"
            image.save(out / name)
            text.close()
            page.close()
        pdf.close()
    return hints


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipients", required=True)
    ap.add_argument("--documents", required=True)
    ap.add_argument("--pdf", action="append", default=[], help='KIND=path, e.g. "INCLUSIONS=C:/x.pdf"')
    ap.add_argument("--out", required=True, help="folder under the checkout's runtime\\ folder")
    ap.add_argument("--template", help="template name, when the saved JSON holds several templates")
    ap.add_argument("--scale", type=float, default=2.0, help="render scale (2 = 144 dpi)")
    args = ap.parse_args(argv)
    try:
        out = check_out_dir(args.out)
        pdfs = parse_pdf_args(args.pdf)
        for kind, path in pdfs.items():
            if not path.is_file():
                raise Refusal(f"{kind}: no file at {path}")
        try:
            recipients = json.loads(Path(args.recipients).read_text(encoding="utf-8"))
            documents = json.loads(Path(args.documents).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise Refusal(f"input JSON not readable: {e}")
    except Refusal as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print("REFUSED: pypdfium2 and Pillow are needed to draw the pages "
              "(a verification-only install, never a server dependency)", file=sys.stderr)
        return 2
    try:
        tabs = geometry(recipients, documents, args.template)
    except Refusal as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    page_counts = {}
    for kind, path in pdfs.items():
        pdf = pdfium.PdfDocument(str(path))
        page_counts[kind] = len(pdf)
        pdf.close()
    docs = by_document([t for t in tabs if t["kind"] in pdfs], page_counts)
    out.mkdir(parents=True, exist_ok=True)
    hints = render(pdfs, docs, out, args.scale)
    lines = summary_lines(docs, hints)
    left_out = sorted({t["kind"] for t in tabs} - set(pdfs))
    if left_out:
        lines.append("no PDF given for: " + ", ".join(left_out))
    (out / "tabs.json").write_text(json.dumps([t for t in tabs if t["kind"] in pdfs], indent=1) + "\n",
                                   encoding="utf-8")
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
