r"""Build the DocuSign draft-envelope payload for a job (CD-10, 13 Oct 2026).

    python docusign_payload.py --job <workdir>/job.json --job-dir "<CONTRACT DOCUMENTATION>"
                               [--region NSW|QLD] [--server docusign-demo]

Reads the job JSON and the driver's routes.txt, picks the DocuSign template by
region x buyer type, maps the buyer-side roles, writes the subject, message and
JobNo custom field, and leaves two files in the workdir:

  docusign_envelope.json  - what Claude passes to createEnvelope (templateId
                            left empty: resolved by name through getTemplates)
  docusign_payload.txt    - the mapping with a source per recipient, the roles
                            left as template defaults, flags, and the list of
                            what staff do in DocuSign before sending

This script never calls DocuSign. The MCP calls are Claude's, per the skill's
references/docusign-draft.md, and the create call is gated by the approval
prompt. Exit codes: 0 payload written (call or no-call stated in the files),
2 a stop condition (reason in docusign_payload.txt and on stderr).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402
import hia_probe  # noqa: E402


class PayloadStop(Exception):
    """A stop condition: nothing is created, the reason is reported."""


# Template map (spec: Rules / Template pick). Names as stored in the account,
# compared after trimming whitespace. buyer_roles are set from the job;
# default_roles are the template's own people and are never passed.
TEMPLATES = {
    ("NSW", "single"):  {"name": "NSW Build _ Single Buyer", "buyer_roles": ["Buyer"],
                         "default_roles": ["Buyer Witness", "Builder", "Builder Witness", "Date Contract"]},
    ("NSW", "two"):     {"name": "NSW Build _ 2 Buyers", "buyer_roles": ["Buyer 1", "Buyer 2"],
                         "default_roles": ["Builder", "Builder Witness", "Signer 1"]},
    ("NSW", "company"): {"name": "NSW Build _ Company", "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder", "Builder Witness", "Date Contract"]},
    ("QLD", "single"):  {"name": "QLD Build _ Single Buyer", "buyer_roles": ["Buyer"],
                         "default_roles": ["Builder"]},
    ("QLD", "two"):     {"name": "QLD Build _ 2 Buyer", "buyer_roles": ["BUYER 1", "Buyer 2"],
                         "default_roles": ["Builder"]},
    ("QLD", "company"): {"name": "QLD Build _ Company", "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder"]},
}

OWNER_KEYS = ("owner_1", "owner_2", "owner_3")


def _s(values, key):
    return str(values.get(key) or "").strip()


def variant_for(values):
    """('single'|'two'|'company', flags). Company wins; three or more owners
    use the 2 Buyers template with the rest flagged (as CD-3.8 fills them)."""
    owners = [_s(values, k) for k in OWNER_KEYS if _s(values, k)]
    if not owners:
        raise PayloadStop("owner_1 is empty - no buyer to address the envelope to")
    if any(dc.is_company_owner(o) for o in owners):
        return "company", []
    if len(owners) == 1:
        return "single", []
    flags = []
    if len(owners) > 2:
        flags.append(f"owner_3 and beyond ({', '.join(owners[2:])}) have no role on the "
                     f"2 Buyers template - staff add them in DocuSign before sending")
    return "two", flags


def pick_template(state, values):
    if state not in ("NSW", "QLD"):
        raise PayloadStop(f"region state {state!r} has no DocuSign template (NSW or QLD only)")
    variant, flags = variant_for(values)
    return TEMPLATES[(state, variant)], flags


def recipients_for(template, values):
    """templateRoles for the buyer-side roles, each with its source field."""
    roles, sources = [], []
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        name, email = _s(values, "guarantor_name"), _s(values, "guarantor_email")
        if not name:
            raise PayloadStop("guarantor_name missing - the Company template signs through the guarantor")
        if not email:
            raise PayloadStop("guarantor_email missing - no address to send the Company template to")
        roles.append({"roleName": "Buyer - Company Guarantor", "name": name, "email": email})
        sources.append("Buyer - Company Guarantor: guarantor_name + guarantor_email")
        return roles, sources
    pairs = (("owner_1", "owner_email"), ("owner_2", "owner_2_email"))
    for role, (nkey, ekey) in zip(template["buyer_roles"], pairs):
        name, email = _s(values, nkey), _s(values, ekey)
        if not name:
            continue  # single-buyer template has one role; a second owner never reaches here
        if not email:
            raise PayloadStop(f"{ekey} missing for {role} ({name}) - every buyer needs an email")
        roles.append({"roleName": role, "name": name, "email": email})
        sources.append(f"{role}: {nkey} + {ekey}")
    if not roles:
        raise PayloadStop("no buyer could be mapped")
    return roles, sources


MESSAGE_BODY = "Please find the building contract for review and signing."
MESSAGE_SIGNOFF = "Thank you\nSales Admin"


def suburb_caps(values):
    """Suburb in capitals without the trailing state word (doc_suffix's rule)."""
    words = _s(values, "suburb").split()
    if words and words[-1].upper() in dc.STATES:
        words = words[:-1]
    return " ".join(words).upper()


def subject_for(values):
    lot, suburb = _s(values, "lot_no"), suburb_caps(values)
    if not (lot and suburb):
        raise PayloadStop(f"lot_no/suburb needed for the subject (got lot={lot!r}, suburb={suburb!r})")
    return f"Complete with DocuSign: BUILD CONTRACT - LOT {lot}, {suburb}"


def first_names(values, template):
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        return [_s(values, "guarantor_name").split()[0]]
    names = []
    for key in OWNER_KEYS[:len(template["buyer_roles"])]:
        n = _s(values, key)
        if n:
            names.append(n.split()[0])
    return names


def message_for(values, template):
    return f"Dear {' & '.join(first_names(values, template))},\n\n{MESSAGE_BODY}\n\n{MESSAGE_SIGNOFF}"


def staff_list(template, flags):
    items = ["Replace the template's placeholder PDFs with the job's PDFs from the job folder "
             "(build contract, inclusions, preliminary agreement where one exists, plans)."]
    if "Buyer Witness" in template["default_roles"]:
        items.append("The Buyer Witness role holds the template's default person - change or remove it.")
    items.append("Check every field and signature tab landed on the job's documents, then send.")
    return items + flags


def build_envelope(state, values, server):
    job_no = _s(values, "job_no")
    if not job_no:
        raise PayloadStop("job_no missing - the JobNo custom field is how a draft is found again")
    template, flags = pick_template(state, values)
    roles, sources = recipients_for(template, values)
    definition = {
        "status": "created",
        "templateId": "",
        "emailSubject": subject_for(values),
        "emailBlurb": message_for(values, template),
        "templateRoles": roles,
        "customFields": {"textCustomFields": [
            {"name": "JobNo", "value": job_no, "show": "false", "required": "false"}]},
    }
    return {
        "server": server,
        "templateName": template["name"],
        "envelopeDefinition": definition,
        "defaultRoles": list(template["default_roles"]),
        "sources": sources,
        "flags": flags,
        "staffBeforeSending": staff_list(template, flags),
    }
