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


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(bracket_street(a)[0], "|", bracket_site(a))
