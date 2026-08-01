"""Extract new-job data from an EOI / contract request email.

Implements the JD-* rules in ../rules/job-details.md. Input is the plain text
of the request email; output is a job-data JSON draft sheet plus a list of
flags that need human attention or web verification. This script never touches
OSC — it produces the draft for review (Phase 1 steps 3/5/9 of
../workflows/new-job.md).

Usage:
    python extract_eoi.py <email.txt|email.md> [-o out.json]
"""

import argparse
import json
import re
import sys

STATE_REGION = {"QLD": "SEQ1", "NSW": "SYDNEY01"}  # JD-1.1 (confirm per EOI)
RELATIONSHIP_SALES = "SALES"  # JD-7.4
RELATIONSHIP_MARKETER = "MARKETER_ cc in all emails"  # JD-7.5
INITIAL_TEMPLATE = "Pre Sales Investor v1"  # JD-1.3


def _unwrap(text):
    """Join hard-wrapped continuation lines so 'Key: value' pairs stay whole."""
    lines, out = text.splitlines(), []
    for line in lines:
        stripped = line.strip()
        if out and stripped and not re.match(r"^[-*\d]|^[A-Z][\w ]{0,30}:", stripped):
            out[-1] += " " + stripped
        else:
            out.append(stripped)
    return out


def _field(lines, *keys):
    """Return the value of the first 'Key: value' line matching any key."""
    for line in lines:
        cleaned = re.sub(r"^[-*]\s*", "", line)
        for key in keys:
            m = re.match(rf"{key}\s*[:：]\s*(.+)", cleaned, re.I)
            if m:
                return m.group(1).strip()
    return None


def _fallbacks(text, data, flags):
    """Fill still-null fields from free-form email patterns (forwarded
    chains, subject lines) seen in real Transpire contract-order emails.
    Only ever fills nulls - labelled 'Key: value' data always wins."""
    subject = _field(text.splitlines(), "Subject") or ""

    # Subject: "... Lot 8 Yarandoo Close, Gunnedah [NSW 2380]"
    if data["lot"] is None or data["suburb"] is None:
        m = re.search(r"Lot\s+(\w+)\s*(?:\(\d+\))?\s*[,_-]?\s*(.*)", subject, re.I)
        if m:
            data["lot"] = data["lot"] or m.group(1)
            rest = re.sub(r"[_|]+", ",", m.group(2))
            parts = [p.strip(" ,.-") for p in rest.split(",") if p.strip(" ,.-")]
            if parts:
                tail = parts[-1]
                tm = re.match(r"(.+?)\s+(QLD|NSW)\s*(\d{4})?$", tail, re.I)
                if tm:
                    tail = tm.group(1)
                    data["state"] = data["state"] or tm.group(2).upper()
                if data["suburb"] is None and not re.search(r"\d", tail):
                    data["suburb"] = tail.upper()  # JD-2.4 CAPS
                if len(parts) > 1:
                    data.setdefault("street_hint", parts[0])
            flags.append("Lot/suburb parsed from the subject line - confirm "
                         "against the attached EOI")

    # Body: "in <Suburb> NSW/QLD"
    if data["state"] is None and data["suburb"]:
        m = re.search(rf"{re.escape(data['suburb'])}\s+(QLD|NSW)", text, re.I)
        if m:
            data["state"] = m.group(1).upper()

    # "site a Forrest 200 with a Lindeman façade"
    if data["design_name"] is None:
        m = re.search(r"site\s+an?\s+(.+?)\s+with\s+an?\s+(\w+)\s+fa[cç]ade",
                      text, re.I)
        if m:
            data["design_name"], data["facade"] = m.group(1), m.group(2)

    # Any "$519,300" style amount
    if data["contract_price"] is None:
        m = re.search(r"\$\s*([\d,]{4,}(?:\.\d{2})?)", text)
        if m:
            data["contract_price"] = m.group(1).replace(",", "")
            if not re.search(r"incl\.?\s*GST", text, re.I):
                flags.append("GST treatment of the price not stated - confirm")

    # Adobe Sign: "... has been signed by David Borradaile (email)"
    if data["client_name"] is None:
        m = re.search(r"signed by\s+([A-Z][\w' .-]+?)\s*\(([\w.+-]+@[\w.-]+)\)",
                      text)
        if m:
            data["client_name"] = m.group(1).strip()
            data["client_email"] = data["client_email"] or m.group(2)
            flags.append("Client taken from e-sign notification - confirm the "
                         "name matches the attached ID (JD-1.4)")
        m = re.search(r"waiting for\s+([\w.+-]+@[\w.-]+)\s+to sign", text, re.I)
        if m:
            flags.append(f"EOI NOT fully signed - waiting on {m.group(1)}; "
                         "likely a second purchaser (JD-7.3 slots)")
            data["purchaser_slot"] = None

    # Labelled-parse "fill manually" flags are stale once a fallback filled it
    if data["suburb"]:
        flags[:] = [f for f in flags
                    if not f.startswith("Suburb/state not parsed")]

    # Estate from a Z:\ESTATES INFORMATION path in the body (JD-3.1 source)
    if data["estate"] is None:
        m = re.search(r"Z:\\ESTATES INFORMATION\\\w+\\[\w ]+\\([\w ]+)", text)
        if m:
            data["estate"] = m.group(1).strip().title()
            flags.append("Estate taken from the Z:\\ESTATES INFORMATION path "
                         "in the email - confirm stage there (JD-3.1)")


def extract(text):
    # Outlook text export wraps addresses/links as "x<mailto:x>" / "x<http…>"
    text = re.sub(r"<(?:mailto|https?):[^>]*>", "", text)
    lines = _unwrap(text)
    data, flags = {}, []

    # --- Lot / stage / estate / registration (JD-2, JD-3.1) ---
    lot_line = _field(lines, "Lot") or ""
    m = re.match(r"(\w+)", lot_line)
    data["lot"] = m.group(1) if m else None
    m = re.search(r"stage\s*(\w+)", lot_line, re.I)
    data["stage"] = m.group(1) if m else None
    m = re.search(r"stage\s*\w+\s*,\s*([^(,]+)", lot_line, re.I)
    data["estate"] = m.group(1).strip() if m else None
    if re.search(r"not (?:yet )?registered", text, re.I):
        data["land_registered"] = False
    elif re.search(r"registered", text, re.I):
        data["land_registered"] = True
    else:
        data["land_registered"] = None
        flags.append("Land registration status not stated - confirm "
                     "(DP&88B / PLAN) before setting the address (JD-2.1/2.2)")
    if data["stage"] is None:
        flags.append("Stage missing - check Z:\\ESTATES INFORMATION (JD-3.1)")

    # --- Suburb / state (JD-2.4, JD-2.5) ---
    suburb_line = _field(lines, "Suburb") or ""
    m = re.match(r"([^,]+),\s*(QLD|NSW)", suburb_line, re.I)
    if m:
        data["suburb"] = m.group(1).strip().upper()  # JD-2.4 CAPS
        data["state"] = m.group(2).upper()
    else:
        data["suburb"], data["state"] = None, None
        flags.append("Suburb/state not parsed - fill manually (JD-2.4/2.5)")
    data["postcode"] = None  # never asserted from memory - JD-2.6
    data["contract_no"] = "GENERATE_IN_OSC"  # JD-1.2
    data["initial_template"] = INITIAL_TEMPLATE

    # --- Design (JD-3.2/3.3) ---
    design_line = _field(lines, "Design") or ""
    m = re.match(r"(.+?)\s*[-–]\s*(.+?)\s*fa[cç]ade", design_line, re.I)
    if m:
        data["design_name"], data["facade"] = m.group(1).strip(), m.group(2).strip()
    else:
        data["design_name"], data["facade"] = design_line or None, None
    granny = bool(re.search(r"granny flat", text, re.I))
    data["design_type"] = "Auxiliary Dwelling" if granny else "Standard"  # JD-3.2

    # --- Purpose (JD-3.4) ---
    purpose = _field(lines, "Purpose")
    if purpose is None and not re.search(r"invest|owner[- ]occ", text, re.I):
        data["investment"] = None
        flags.append("Investment vs owner-occupier not stated - confirm (JD-3.4)")
    else:
        data["investment"] = bool(re.search(r"invest", purpose or text, re.I))

    # --- Price (JD-6) ---
    price_line = _field(lines, "Contract price", "Price") or ""
    m = re.search(r"\$?([\d,]+(?:\.\d{2})?)", price_line)
    data["contract_price"] = m.group(1).replace(",", "") if m else None
    data["price_gst"] = bool(re.search(r"incl\.?\s*GST", price_line, re.I))

    # --- Client (JD-1.4, JD-7) ---
    client_line = _field(lines, "Client") or ""
    m = re.match(r"([^(,]+)", client_line)
    data["client_name"] = m.group(1).strip() if m else None  # name as on ID
    individual = bool(re.search(r"individual", client_line, re.I))
    data["purchaser_slot"] = "Primary" if individual else None
    if not individual:
        flags.append("Multiple purchasers - assign Primary/Secondary slots "
                     "per JD-7.3 and confirm with the business")
    if not re.search(r"\bID\b", client_line, re.I):
        flags.append("Client ID not confirmed attached - request it (JD-0.1)")

    addr = _field(lines, "Client current address")
    data["client_address"] = None
    if addr:
        m = re.match(r"(.+?),\s*([A-Za-z ]+?)\s+(QLD|NSW)\s*(\d{4})?", addr)
        if m:
            data["client_address"] = {
                "address1": m.group(1).strip(),        # JD-7.1: address1 only
                "suburb": m.group(2).strip().upper(),  # JD-7.1: CAPS
                "state": m.group(3).upper(),
                "postcode": m.group(4),
            }
    contact_line = _field(lines, "Client mobile", "Mobile") or ""
    m = re.search(r"(04\d{2}[\s\d]{6,10})", contact_line)
    data["client_mobile"] = m.group(1).strip() if m else None
    m = re.search(r"[\w.+-]+@[\w.-]+", contact_line)
    data["client_email"] = m.group(0) if m else None
    data["primary_comm"] = "Email"  # JD-7.2

    # --- Sales / marketer (JD-3.9, JD-7.4/7.5) ---
    data["sales_consultant"] = _field(lines, "Sales consultant", "Sales")
    data["sales_relationship"] = RELATIONSHIP_SALES
    marketer_line = _field(lines, "Marketer") or ""
    m = re.match(r"([^,]+)", marketer_line)
    data["marketer_company"] = m.group(1).strip().upper() if m else None  # JD-3.9
    m = re.search(r"contact\s+([^,]+)", marketer_line, re.I)
    data["marketer_contact"] = m.group(1).strip() if m else None
    m = re.search(r"[\w.+-]+@[\w.-]+", marketer_line)
    data["marketer_email"] = m.group(0) if m else None
    data["marketer_relationship"] = RELATIONSHIP_MARKETER

    # --- Free-form fallbacks (fill remaining nulls) ---
    _fallbacks(text, data, flags)

    # --- Derived fields (need suburb/state/registration settled) ---
    data["region"] = STATE_REGION.get(data["state"] or "")  # JD-1.1
    if data["region"] is None:
        flags.append("State/region not determined - set Region manually (JD-1.1)")

    if data["land_registered"] is False:
        data["address1"] = "New Road"  # JD-2.1
        flags.append("Unregistered land - update address after PLAN (JD-2.1, JD-8)")
    else:
        data["address1"] = None
        if data["land_registered"]:
            flags.append("Registered land - take street no/name from DP&88B (JD-2.2)")
    data["address2"] = f"({data['estate']})" if data["estate"] else None  # JD-2.3

    if data["lot"] and data["suburb"]:  # JD-2.7
        street = data["address1"] or data.get("street_hint") or "<street>"
        data["job_name"] = (f"LOT {data['lot']}.({street})."
                            f"{data['suburb']} <postcode>")
        flags.append("Insert verified postcode into job name (JD-2.7)")

    if data["suburb"]:
        flags.append(f"Verify suburb spelling + postcode by web search: "
                     f"'{data['suburb']} {data['state']}' (JD-2.4, JD-2.6)")
        flags.append(f"Council: web-search '{data['suburb'].lower()} "
                     f"{data['state']} Local Council' (JD-3.7)")
    data["local_council"] = None
    data["private_certifier"] = "Buildable" if data["state"] == "QLD" else None
    if data["state"] == "NSW":
        flags.append("NSW certifier rule not in manual - confirm (JD-3.6)")

    data.pop("street_hint", None)

    # --- Constant checklist items (JD-4, JD-5) ---
    data["activities_to_complete"] = [1, 2, 6]
    data["attachment_subject"] = "NEW JOB"  # JD-5, uppercase

    return {"job": data, "flags": flags}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("email", help="path to the request-email text")
    ap.add_argument("-o", "--out", help="write JSON here instead of stdout")
    args = ap.parse_args()

    with open(args.email, encoding="utf-8") as f:
        result = extract(f.read())

    js = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(js + "\n")
        print(f"wrote {args.out} ({len(result['flags'])} flags)")
    else:
        print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
