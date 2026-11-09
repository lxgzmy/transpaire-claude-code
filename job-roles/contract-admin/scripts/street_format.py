r"""The site's house number in brackets, the same in every contract document. Stdlib only.

    python street_format.py "3 Sample Road"            -> (3) Sample Road

Feedback sheet 5 Nov 2026 row 7 (job 26011): "in preliminary agreement, build
contract and inclusions, the street number is always in brackets" - the run
had bracketed it in one document and not the others, because CD-2.2 kept the
brackets only when the job folder's name carried them and each document's
job JSON was written on its own. One function now formats the street for
every filler, so the documents cannot disagree.

Only a single leading house number is bracketed: "3", "3A", "12-14". A street
with no number ("Sample Road", "New Road", "Road 28"), one already bracketed,
or a parent address naming two numbers ("29 Sample & 25 Example Street" - an
unregistered lot's development address, which CD-2.4 puts in ESTATE) is left
as it is; the last is reported so a person checks it.

A parent address is not the lot's street (CD-2.4; job 26060, where the team
wrote the street the plans put the lot on). `lot_street_from_plans` reads that
street off the plans' title block, and `draft_contract.py` writes it in every
street and site field when the plans name exactly one - flagged to confirm.
"""
import re
import sys

NUMBER = r"\d+[A-Za-z]?(?:\s*[-–]\s*\d+[A-Za-z]?)?"
LEADING_RE = re.compile(rf"^\s*({NUMBER})\s+(?=[A-Za-z])")
TWO_NUMBERS_RE = re.compile(rf"\b{NUMBER}\b.*(?:&|\band\b|,).*\b{NUMBER}\s+[A-Za-z]", re.I)
# "<lot>, <number> <street>, <SUBURB> ..." - the site address the fillers type
SITE_RE = re.compile(rf"^(\s*(?:Lot\s+)?\d+[A-Za-z]?\s*,\s*)({NUMBER})\s+(?=[A-Za-z])", re.I)


def bracket_street(street):
    """(street with its house number bracketed, note or None)."""
    s = str(street or "")
    if not s.strip() or s.lstrip().startswith("("):
        return s, None
    if TWO_NUMBERS_RE.search(s):
        return s, f"street {s.strip()!r} names more than one number (a parent address?) - left as given; check it"
    m = LEADING_RE.match(s)
    if not m:
        return s, None
    return f"({re.sub(r'\s+', '', m.group(1))}) " + s[m.end():], None


def bracket_site(site):
    """A site address "<lot>, <number> <street>, ..." with its house number bracketed."""
    s = str(site or "")
    if TWO_NUMBERS_RE.search(s.split(",", 1)[-1].split(",")[0] if "," in s else s):
        return s
    m = SITE_RE.match(s)
    if not m:
        return s
    return m.group(1) + f"({re.sub(r'\s+', '', m.group(2))}) " + s[m.end():]


STREET_KEYS = ("street", "land_street")      # a bare street line
SITE_KEYS = ("site_address",)                 # "<lot>, <street>, <SUBURB> ..."
HIA_SITE_KEYS = ("site_hia",)                 # "<street>, <SUBURB> ..." (no lot)


# Where the rule holds: the sheet names the NSW job's three documents
REGIONS = {"NSW"}
FAMILY_REGION = {"sydney": "NSW", "gunnedah": "NSW", "seq": "QLD"}


def applies(region_or_family):
    r = str(region_or_family or "")
    return FAMILY_REGION.get(r.lower(), r.upper()) in REGIONS


def bracket_job(values):
    """A copy of the job values with every site street's house number in brackets,
    and the notes for anything left as given."""
    out, notes = dict(values), []
    for k in STREET_KEYS + HIA_SITE_KEYS:
        if out.get(k):
            out[k], note = bracket_street(out[k])
            if note and note not in notes:
                notes.append(note)
    for k in SITE_KEYS:
        if out.get(k):
            out[k] = bracket_site(out[k])
    return out, notes


# The lot's own street, as a plan's title block names it: "Lot 5 Sample Street Sampleville".
# Feedback sheet 5 Nov 2026 (job 26060): the request and the SA gave only the
# parent address "29 Sample & 25 Example Street"; the team's documents and OSC
# read "Lot 5, Example Street" - the street the plans put the lot on (CD-2.4).
STREET_TYPES = ("Street|St|Road|Rd|Avenue|Ave|Close|Crescent|Cres|Drive|Dr|Way|Place|Pl|Lane|"
                "Parade|Pde|Circuit|Cct|Court|Ct|Boulevard|Boulevarde|Terrace|Tce|Loop|Grove|"
                "Rise|Glade|Chase|Mews|Row|Walk|Link|Highway|Hwy|Square|Esplanade|Ridge|Vista|"
                "Retreat|Promenade|Outlook|View|Green|Gardens|Circle|Bend|Track|Trail")
TYPE_NORMAL = {"st": "Street", "rd": "Road", "ave": "Avenue", "cres": "Crescent", "dr": "Drive",
               "pl": "Place", "pde": "Parade", "cct": "Circuit", "ct": "Court", "tce": "Terrace",
               "hwy": "Highway"}


def is_parent_address(street):
    """True for a street line naming more than one house number."""
    return bool(TWO_NUMBERS_RE.search(str(street or "")))


def parent_street_names(parent):
    """The street names a parent address carries: "29 Sample & 25 Example Street" ->
    {"SAMPLE", "EXAMPLE"} (the type word, numbers and joiners dropped)."""
    words = re.findall(r"[A-Za-z']+", str(parent or ""))
    types = {w.upper() for w in STREET_TYPES.split("|")}
    return {w.upper() for w in words if w.upper() not in types and w.lower() not in ("and",)}


def lot_street_from_plan_text(text, lot_no, among=None):
    """The street a plan names for the lot ("Lot 5 Sample Street ..."), or None when the
    plans name none or disagree. Never a numbered street: a parent number is not the lot's.

    `among` - the parent address. Plans alone are not enough: on a sweep of 87 past
    jobs' plans the "Lot <n> <name> <type>" text named a street the job is not on in
    12 (a "New Road" placeholder, a suburb like "<Name> Court", a neighbouring road).
    So the plans only choose between the streets the request itself names; any
    other street they name is ignored."""
    lot = re.escape(str(lot_no or "").strip())
    if not lot:
        return None
    allowed = parent_street_names(among) if among is not None else None
    rx = re.compile(rf"\bLot\s+{lot}\s*,?\s+((?:[A-Z][A-Za-z']+\s+){{1,3}}?)({STREET_TYPES})\b\.?")
    found = set()
    for m in rx.finditer(re.sub(r"\s+", " ", str(text or ""))):
        words = m.group(1).split()
        kind = TYPE_NORMAL.get(m.group(2).lower(), m.group(2).title())
        if allowed is not None and not any(w.upper() in allowed for w in words):
            continue
        found.add(" ".join(w.title() if w.isupper() else w for w in words) + " " + kind)
    return found.pop() if len(found) == 1 else None


def lot_street_from_plans(pdf_paths, lot_no, among=None):
    """(street, source pdf) from the plans that name exactly one street for the lot -
    one of the parent address's streets when `among` is given - or (None, None).
    Plans that disagree with each other give None."""
    import pdf_text
    hits = {}
    for p in pdf_paths:
        try:
            street = lot_street_from_plan_text(" ".join(pdf_text.text_of(p)), lot_no, among)
        except Exception:
            street = None
        if street:
            hits.setdefault(street, p)
    if len(hits) == 1:
        return next(iter(hits.items()))
    return None, None


def use_lot_street(values, street, source):
    """A copy of the job values with a parent address replaced by the lot's own street in
    every street and site key, and the note saying so. The parent address is kept in the
    note only: where it goes beyond STREET (ESTATE or nowhere) the team has done both
    (CD-2.4), so the job's own ESTATE value is left as it is."""
    out = dict(values)
    parent = str(values.get("street") or values.get("land_street") or "").strip()
    if not parent or not is_parent_address(parent):
        return out, None
    for k in STREET_KEYS:
        if out.get(k) and str(out[k]).strip() == parent:
            out[k] = street
    for k in SITE_KEYS + HIA_SITE_KEYS:
        if out.get(k) and parent in str(out[k]):
            out[k] = str(out[k]).replace(parent, street, 1)
    note = (f"street: the request gives the parent address {parent!r}; the plans "
            f"({source}) put the lot on {street!r}, written instead (CD-2.4) - confirm")
    return out, note


# The estate after the street (job 26061 feedback sheet, 9 Nov 2026, rows 7-10).
# Wherever a street line runs on into the address, the team writes the job's
# estate straight after the street - "(26) Sample Street, (Sample Estate)" - in
# NSW and QLD alike: the inclusions' signature-page STREET: and the "located
# at;" site box, the build contract's cover SITE and The Land's STREET ADDRESS.
# Seen on the three latest NSW estate jobs (26042, 26055, 26057) and the SEQ
# estate jobs (26050, 26051, the team's copy of 26059). The page-1 STREET :
# stays bare: the estate has its own ESTATE : there.
def estate_name(estate):
    """The job's estate as a plain name ("Sample Estate"), or "" when ESTATE is
    blank or holds a pre-registration parent address ("37 Sample Road, (Sample
    Estate)", CD-2.4) - that one stays where the job puts it and nowhere else."""
    e = str(estate or "").strip()
    if not e or re.search(r"\d", e) or "," in e:
        return ""
    return e.strip("()").strip()


def with_estate(street, estate):
    """"<street>, (<Estate>)" - the estate once, after the street, whether the
    street comes bare or with the estate already bracketed (with or without the
    comma). A street that names the estate some other way is left as given."""
    s, e = str(street or "").strip(), estate_name(estate)
    if not s or not e:
        return s
    typed = re.fullmatch(r"(.+?)[\s,]*\(\s*" + re.escape(e) + r"\s*\)", s, re.I)
    if typed:
        return f"{typed.group(1).strip()}, ({e})"
    if e.lower() in s.lower():
        return s
    return f"{s}, ({e})"


def site_with_estate(site, street, estate):
    """A "<lot>, <street>, <SUBURB> <STATE> <postcode>" site address with the
    estate after the street when it does not name the estate yet. One that
    already does (SEQ writes "<street> (<Estate>)", CD-2.4) is left as it is."""
    s, st, e = str(site or ""), str(street or "").strip(), estate_name(estate)
    if not s.strip() or not st or not e or e.lower() in s.lower():
        return s
    i = s.lower().find(st.lower())
    if i < 0:
        return s
    return s[:i] + with_estate(s[i:i + len(st)], e) + s[i + len(st):]


def estate_job(values):
    """A copy of the job values with the estate after the street where the team
    writes it in the inclusions - `street_estate` (the signature pages'
    STREET:) and `site_address` - and the notes for anything it could not place."""
    out, notes = dict(values), []
    e = estate_name(values.get("estate"))
    street = str(values.get("street") or "")
    out["street_estate"] = with_estate(street, e) if e else street
    site = str(values.get("site_address") or "")
    if e and site.strip():
        out["site_address"] = site_with_estate(site, street, e)
        if e.lower() not in out["site_address"].lower():
            notes.append(f"estate {e!r} not added to the site address {site!r}: the street {street!r} "
                         f"is not in it - check the address under 'located at;'")
    elif str(values.get("estate") or "").strip() and not e:
        notes.append(f"ESTATE {str(values.get('estate')).strip()!r} is a parent address, not an estate "
                     f"name (CD-2.4) - written in ESTATE only, not after the street")
    return out, notes


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(bracket_street(a)[0], "|", bracket_site(a))
