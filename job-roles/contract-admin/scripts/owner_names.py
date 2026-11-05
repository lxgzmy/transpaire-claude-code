r"""A company or trust owner, as every contract document names it. Stdlib only.

A company job keys `owner_1` as the entity exactly as the signed land contract
writes it and `owners` as the entity plus its ACN (or ABN), with no second
owner (CD-3.9). The team's review of job 26039 (feedback sheet 5 Nov 2026,
rows 8-10, 12, 13, 16) asked for that full name, ACN included, wherever the
owner is named, and for the person who signs for the company on a line of its
own under it: "<guarantor> on behalf of <company> ACN: ...". The signer is the
job's `company_signatory`, sourced from the land contract (its guarantee page
names the guarantor) - never derived here.
"""
import re

# " ACN: 600 000 000" / ", ABN 12 345 678 901" at the end of `owners`
COMPANY_TAIL_RE = re.compile(r"\s*,?\s*\b(?:ACN|ABN)\b\s*:?\s*\d[\d ]{7,13}\d\s*", re.I)


def company_name(values):
    """The company or trust owner's full name with its ACN/ABN, or None."""
    o1 = str(values.get("owner_1") or "").strip()
    owners = str(values.get("owners") or "").strip()
    if not o1 or str(values.get("owner_2") or "").strip() or not owners.startswith(o1):
        return None
    return owners if COMPANY_TAIL_RE.fullmatch(owners[len(o1):]) else None


def signer_line(values, company=None):
    """'<signatory> on behalf of <company incl. ACN>', or None without a signatory."""
    company = company or company_name(values)
    signer = str(values.get("company_signatory") or "").strip()
    return f"{signer} on behalf of {company}" if company and signer else None
