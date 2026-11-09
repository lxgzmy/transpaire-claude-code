r"""Build the DocuSign draft payload for a job (CD-11, 13 Oct 2026; issue #77, 6 Nov 2026).

    python docusign_payload.py --job <workdir>/job.json --job-dir "<CONTRACT DOCUMENTATION>"
                               [--region NSW|QLD] [--server docusign-upload|docusign-upload-prod]
                               [--osc-contacts <workdir>/osc_contacts.json]

Reads the job JSON and the driver's routes.txt, picks the DocuSign template by
region x buyer type, maps the buyer-side roles, writes the subject, message and
JobNo, lists the job's PDFs under their CD-7.2 names, and leaves two files in
the workdir:

  docusign_envelope.json  - draftArgs: the exact arguments for the docusign-upload
                            server's docusign_draft_preview and docusign_create_draft
                            (the server resolves the template by name)
  docusign_payload.txt    - the mapping with a source per recipient, the roles
                            left as template defaults, the documents, flags, and
                            what staff do in DocuSign before and after sending

The buyers' names and emails come from OSC when --osc-contacts names the job
client's contact list (GET /api/Clients/{ClientID}/Contacts, saved as returned):
Buyer 1 is the principal buyer recorded there (issue #77, step 3). Without it
they come from the job JSON and the report says to check them against OSC.

The server comes from where the job folder is: a synthetic job under the
checkout's runtime\docusign-sandbox goes to the sandbox server (docusign-upload),
and every other job folder, a real job's, to the production server
(docusign-upload-prod). The template name follows the server: the two accounts
name the same templates differently.

This script never calls DocuSign or OSC. The MCP calls are Claude's, per the
skill's references/docusign-draft.md, and the create call is gated by the
approval prompt. Exit codes: 0 payload written (call or no-call stated in the
files), 2 a stop condition (reason in docusign_payload.txt and on stderr).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402
import hia_probe  # noqa: E402


class PayloadStop(Exception):
    """A stop condition: nothing is created, the reason is reported."""


# Template map (CD-11.2). `name` is the sandbox account's (checked read-only
# 13 Oct 2026); `production_name` the production account's, as issue #77's
# workflow screenshot lists them (22 Oct 2026). None = that list does not show
# the template, so a production run stops for it instead of guessing a name
# (open question 10). Both are compared after trimming whitespace, capitals
# included. buyer_roles are set from the job; default_roles are the template's
# own people and are never passed.
TEMPLATES = {
    ("NSW", "single"):  {"name": "NSW Build _ Single Buyer",
                         "production_name": "NSW BUILD CONTRACT _ Single Buyer",
                         "buyer_roles": ["Buyer"],
                         "default_roles": ["Buyer Witness", "Builder", "Builder Witness", "Date Contract"]},
    ("NSW", "two"):     {"name": "NSW Build _ 2 Buyers",
                         "production_name": "NSW Build Contract _ Multi Buyers",
                         "buyer_roles": ["Buyer 1", "Buyer 2"],
                         "default_roles": ["Builder", "Builder Witness", "Signer 1"]},
    ("NSW", "company"): {"name": "NSW Build _ Company", "production_name": None,
                         "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder", "Builder Witness", "Date Contract"]},
    ("QLD", "single"):  {"name": "QLD Build _ Single Buyer", "production_name": None,
                         "buyer_roles": ["Buyer"],
                         "default_roles": ["Builder"]},
    ("QLD", "two"):     {"name": "QLD Build _ 2 Buyer",
                         "production_name": "Build Contract _2 Buyer QLD",
                         "buyer_roles": ["BUYER 1", "Buyer 2"],
                         "default_roles": ["Builder"]},
    ("QLD", "company"): {"name": "QLD Build _ Company", "production_name": None,
                         "buyer_roles": ["Buyer - Company Guarantor"],
                         "default_roles": ["Builder"]},
}

OWNER_KEYS = ("owner_1", "owner_2", "owner_3")

# The kinds the docusign-upload server takes, in envelope order (CD-7.2 names).
UPLOAD_KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")

# The two docusign-upload servers (CD-11.1). The sandbox one reads documents only from
# the checkout's runtime/docusign-sandbox, so it only ever gets synthetic jobs; a real
# job's folder needs the production one, registered at Go-Live.
SANDBOX_SERVER = "docusign-upload"
PRODUCTION_SERVER = "docusign-upload-prod"
SANDBOX_DIR = HERE.parents[2] / "runtime" / "docusign-sandbox"

# OSC client-contact relationships that are staff links, not buyers (osc-new-contract.md:
# purchasers "Client Contact", sales "SALES", marketer "MARKETER_CC IN ALL EMAILS").
STAFF_RELATIONSHIPS = ("SALES", "MARKETER")


def _inside(path, root):
    """True when path is root or sits under it, both fully resolved (a link out counts as out)."""
    try:
        p, r = (os.path.normcase(os.path.realpath(x)) for x in (path, root))
    except OSError:
        return False
    return p == r or p.startswith(r.rstrip("\\/") + os.sep)


def server_for(job_dir):
    """The docusign-upload server this job's PDFs can go to."""
    if job_dir and _inside(job_dir, SANDBOX_DIR):
        return SANDBOX_SERVER
    return PRODUCTION_SERVER


def documents_for(job_dir, values):
    """([{kind, path}], [missing kinds]) for the job's PDFs under their CD-7.2 names.

    Only the exact `<KIND>_<suffix>.pdf` counts, so plans saved under any other
    name stay out and are reported as missing rather than guessed at."""
    suffix = dc.doc_suffix(values)
    found, missing = [], []
    for kind in UPLOAD_KINDS:
        path = Path(job_dir) / f"{kind}_{suffix}.pdf"
        if path.is_file():
            found.append({"kind": kind, "path": str(path)})
        else:
            missing.append(kind)
    return found, missing


def _s(values, key):
    return str(values.get(key) or "").strip()


def _words(text):
    return " ".join(str(text or "").split())


def is_company_or_trust(name):
    """A company, or any trust (CD-3.9, CD-11.2). dc.is_company_owner decides the filename
    token, so it drops an `ATF <trust>` clause before testing; here a person who holds the
    land as trustee (`<name> ATF <trust>`) is a trust buyer too, and takes the Company
    template rather than slipping through as a single buyer."""
    up = " " + _words(str(name).upper().replace(".", "")) + " "
    return (dc.is_company_owner(name) or " ATF " in up or " AS TRUSTEE FOR " in up
            or up.rstrip().endswith(" TRUST"))


def variant_for(values):
    """('single'|'two'|'company', flags). Company (a company/trust owner or a
    sourced company_signatory) wins; three or more owners
    use the 2 Buyers template with the rest flagged (as CD-3.8 fills them)."""
    owners = [_s(values, k) for k in OWNER_KEYS if _s(values, k)]
    if not _s(values, "owner_1"):
        raise PayloadStop("owner_1 is empty - no buyer to address the envelope to")
    if not _s(values, "owner_2") and _s(values, "owner_3"):
        raise PayloadStop("owner_2 is blank but owner_3 is set - fix the job JSON before the draft")
    if any(is_company_or_trust(o) for o in owners) or _s(values, "company_signatory"):
        return "company", []
    if len(owners) == 1:
        return "single", []
    flags = []
    if len(owners) > 2:
        flags.append(f"owner_3 and beyond ({', '.join(owners[2:])}) have no role on the "
                     f"2 Buyers template - staff add them in DocuSign before sending")
    return "two", flags


def template_name(template, server):
    """The template's name in the account the server signs in to (CD-11.2)."""
    if server != PRODUCTION_SERVER:
        return template["name"]
    name = template.get("production_name")
    if not name:
        raise PayloadStop(f"the production DocuSign account's name for the template the "
                          f"sandbox calls {template['name']!r} is not confirmed yet - add it to "
                          f"TEMPLATES in docusign_payload.py (contract-docs.md open question 10)")
    return name


def pick_template(state, values):
    if state not in ("NSW", "QLD"):
        raise PayloadStop(f"region state {state!r} has no DocuSign template (NSW or QLD only)")
    variant, flags = variant_for(values)
    return TEMPLATES[(state, variant)], flags


def _contact_list(raw):
    """The contact dicts in an OSC client-contacts read: the list itself, or osc_get's
    {status, ok, data} with the list (or one paging wrapper holding it) under data."""
    if isinstance(raw, dict):
        if raw.get("ok") is False:
            raise PayloadStop("the OSC client-contacts read failed (ok: false) - read it again")
        raw = raw.get("data", raw)
        if isinstance(raw, dict):
            lists = [v for v in raw.values() if isinstance(v, list)]
            raw = lists[0] if len(lists) == 1 else None
    if not isinstance(raw, list) or not all(isinstance(c, dict) for c in raw):
        raise PayloadStop("the OSC contacts file holds no list of client contacts "
                          "(save GET /api/Clients/{ClientID}/Contacts as returned)")
    return raw


def _is_staff_link(contact):
    rel = str(contact.get("relationship") or "").strip().upper()
    return any(rel.startswith(s) for s in STAFF_RELATIONSHIPS)


def osc_people(raw):
    """(purchasers in OSC's order, sales contacts) from the job client's contact list."""
    contacts = _contact_list(raw)
    buyers = [c for c in contacts if not _is_staff_link(c)]
    sales = [c for c in contacts
             if str(c.get("relationship") or "").strip().upper().startswith("SALES")]
    return buyers, sales


def osc_buyer_order(buyers, values):
    """(OSC purchasers with the principal first, flags). Issue #77: Buyer 1 is always the
    principal buyer recorded in OSC. One purchaser marked primary is that principal. When
    OSC marks several (the intake may mark every purchaser primary) or none, Buyer 1 is the
    purchaser whose email is the request's owner 1's, flagged for a person to confirm."""
    if not buyers:
        raise PayloadStop("the job's OSC client has no purchaser contact - set the client "
                          "contacts in OSC before the draft")
    primary = [c for c in buyers if c.get("isPrimaryContact") is True]
    if len(primary) == 1:
        principal = primary[0]
        flags = []
    else:
        email_1 = _s(values, "owner_email").lower()
        match = [c for c in buyers if str(c.get("email") or "").strip().lower() == email_1]
        if not email_1 or len(match) != 1:
            raise PayloadStop(f"OSC marks {len(primary)} purchasers as the primary contact and "
                              f"none matches owner 1's email - a person names the principal "
                              f"buyer in OSC before the draft")
        principal = match[0]
        flags = [f"OSC marks {len(primary)} purchasers as the primary contact, so Buyer 1 "
                 f"follows the request's owner 1 ({_words(principal.get('fullName'))}) - "
                 f"confirm the principal buyer in OSC before sending"]
    return [principal] + [c for c in buyers if c is not principal], flags


def recipients_for(template, values, osc_buyers=None):
    """The buyer-side roles as the docusign-upload tools take them, each with its source.

    With osc_buyers (principal first), names and emails are OSC's and the job JSON only
    cross-checks them; without, they come from the job JSON."""
    roles, sources, flags = [], [], []
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        name, email = _s(values, "guarantor_name"), _s(values, "guarantor_email")
        if not name:
            raise PayloadStop("guarantor_name missing - the Company template signs through "
                              "the guarantor (a trust buyer too: name its guarantor or "
                              "trustee signer from the land contract)")
        if not email:
            raise PayloadStop("guarantor_email missing - no address to send the Company template to")
        roles.append({"role": "Buyer - Company Guarantor", "name": name, "email": email})
        sources.append("Buyer - Company Guarantor: guarantor_name + guarantor_email "
                       "(land contract guarantee page, CD-3.9)")
        if osc_buyers is not None:
            emails = {str(c.get("email") or "").strip().lower() for c in osc_buyers}
            if email.lower() not in emails:
                flags.append("the guarantor's email is not on any OSC purchaser contact - "
                             "check the guarantor against OSC before sending")
        return roles, sources, flags
    pairs = (("owner_1", "owner_email"), ("owner_2", "owner_2_email"))
    owners = [_s(values, k) for k in OWNER_KEYS if _s(values, k)]
    if osc_buyers is not None and len(osc_buyers) != len(owners):
        raise PayloadStop(f"OSC has {len(osc_buyers)} purchaser contact(s) on the job's client "
                          f"and the job JSON {len(owners)} owner(s) - a person reconciles them "
                          f"before the draft")
    for i, (role, (nkey, ekey)) in enumerate(zip(template["buyer_roles"], pairs)):
        jname, jemail = _s(values, nkey), _s(values, ekey)
        if not jname:
            continue  # single-buyer template has one role; a second owner never reaches here
        if osc_buyers is None:
            if not jemail:
                raise PayloadStop(f"{ekey} missing for {role} ({jname}) - every buyer needs an email")
            roles.append({"role": role, "name": jname, "email": jemail})
            sources.append(f"{role}: {nkey} + {ekey} (job JSON, not checked against OSC)")
            continue
        contact = osc_buyers[i]
        name, email = _words(contact.get("fullName")), str(contact.get("email") or "").strip()
        if not name:
            raise PayloadStop(f"OSC purchaser {i + 1} has no full name - fix the contact in OSC")
        if not email:
            raise PayloadStop(f"OSC has no email for {name} ({role}) - every buyer needs one")
        roles.append({"role": role, "name": name, "email": email})
        sources.append(f"{role}: OSC client contact {i + 1}"
                       + (" (principal buyer)" if i == 0 else ""))
        if jemail and jemail.lower() != email.lower():
            flags.append(f"{role} email: OSC has {email}, the request {jemail} - OSC's is in the "
                         f"draft; confirm it before sending")
        if _words(jname).upper() != name.upper():
            flags.append(f"{role} name: OSC has {name!r}, the request {jname!r} - OSC's is in "
                         f"the draft; confirm the full legal name before sending")
    if not roles:
        raise PayloadStop("no buyer could be mapped")
    return roles, sources, flags


# Subject and message as issue #77's workflow shows them (step 4).
MESSAGE_BODY = "Please find the build contract for you to review and sign."
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
    return f"Complete with Docusign: BUILD CONTRACT_LOT{lot} {suburb}"


def message_for(recipients):
    """`Hi <full name> & <full name>,` - the names exactly as the draft's recipients carry them."""
    names = " & ".join(r["name"] for r in recipients)
    return f"Hi {names},\n\n{MESSAGE_BODY}\n\n{MESSAGE_SIGNOFF}"


def staff_list(template, flags, missing=()):
    """What staff do in DocuSign before sending. The draft holds the job's own PDFs, so there
    is nothing to replace; `missing` is the kinds the template has a place for that the job
    folder does not hold under the CD-7.2 name."""
    items = ["Check the recipients and the signing order against OSC: Buyer 1 is the principal "
             "buyer recorded in OSC, every name is the full legal name and every email is OSC's; "
             "check the copy recipients, witnesses and guarantor the template sets."]
    if "Buyer Witness" in template["default_roles"]:
        items.append("The Buyer Witness role holds the template's default person - change or remove it.")
    if missing:
        items.append(f"Not in the draft, because the job folder has no PDF under its CD-7.2 name: "
                     f"{', '.join(missing)}. Add any the job needs and place their tabs.")
    items.append("Place the tabs on any document the draft report flags (it went in without tabs), "
                 "then go through each recipient's required fields on every page and check every "
                 "tab sits on its line before sending.")
    return items + flags


def after_sending(sales=()):
    """Issue #77 step 6: what a person does once they have sent the envelope themselves."""
    who = "; ".join(f"{_words(c.get('fullName'))} <{str(c.get('email') or '').strip()}>"
                    for c in sales if _words(c.get("fullName")))
    return ["Open the Sent folder and take a screenshot of the envelope's signing order.",
            "Email the sales agent that the contract has gone for signing, with that screenshot"
            + (f" (OSC sales contact: {who})" if who else " (the job's SALES contact in OSC)")
            + ". The run drafts nothing and sends nothing here."]


def missing_for_template(state, missing):
    """The missing kinds the region's templates have a place for (QLD has no preliminary agreement)."""
    return [k for k in missing if not (state == "QLD" and k == "PRELIMINARY AGREEMENT")]


def build_envelope(state, values, server, osc_contacts=None):
    job_no = _s(values, "job_no")
    if not job_no:
        raise PayloadStop("job_no missing - the JobNo custom field is how a draft is found again")
    template, flags = pick_template(state, values)
    name = template_name(template, server)
    if osc_contacts is None:
        buyers, sales = None, []
        flags = flags + ["The buyers' names and emails came from the job JSON: OSC's client "
                         "contacts were not read for this run."]
    else:
        buyers, sales = osc_people(osc_contacts)
        if template["buyer_roles"] != ["Buyer - Company Guarantor"]:
            buyers, order_flags = osc_buyer_order(buyers, values)
            flags = flags + order_flags
    recipients, sources, rflags = recipients_for(template, values, buyers)
    flags = flags + rflags
    # Exactly the docusign-upload tools' arguments, so the preview and the create get the same
    # values. The status is not here: "created" is a constant in the server.
    draft_args = {
        "template_name": name,
        "recipients": recipients,
        "email_subject": subject_for(values),
        "email_blurb": message_for(recipients),
        "job_no": job_no,
        "documents": [],
    }
    return {
        "server": server,
        "templateName": name,
        "draftArgs": draft_args,
        "defaultRoles": list(template["default_roles"]),
        "sources": sources,
        "flags": flags,
        "staffBeforeSending": staff_list(template, flags),
        "staffAfterSending": after_sending(sales),
    }


def state_for(job_dir, region):
    """'NSW' or 'QLD' from --region, else from the job folder's region segment."""
    if region:
        return region.upper()
    parts = [p.upper() for p in str(job_dir or "").replace("\\", "/").split("/") if p]
    if "PROJECTS" in parts:
        idx = parts.index("PROJECTS")
        if idx + 1 < len(parts) and parts[idx + 1] in hia_probe.REGION_TO_FOLDER:
            return hia_probe.REGION_TO_FOLDER[parts[idx + 1]][0]
    raise PayloadStop(f"region not recognised from {job_dir!r} - pass --region NSW|QLD")


def read_build_contract_route(workdir):
    path = Path(workdir) / "routes.txt"
    if not path.is_file():
        raise PayloadStop("routes.txt not in the workdir - run draft_contract.py --job-dir first "
                          "(the route decides whether a draft is created)")
    for line in path.read_text(encoding="utf-8").splitlines():
        kind, _, rest = line.partition("\t")
        if kind == "BUILD CONTRACT":
            return rest.split("\t")[0]
    raise PayloadStop("routes.txt has no BUILD CONTRACT line - no build contract was routed, "
                      "so there is nothing to put in DocuSign")


def write_payload(workdir, env, call, stop=None):
    workdir = Path(workdir)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if stop:
        (workdir / "docusign_envelope.json").unlink(missing_ok=True)  # never leave a stale envelope
        txt = f"DOCUSIGN DRAFT - STOPPED ({stamp})\nCALL: no\nREASON: {stop}\n"
        (workdir / "docusign_payload.txt").write_text(txt, encoding="utf-8")
        return None, workdir / "docusign_payload.txt"
    env = dict(env, call=call, generated=stamp)
    jpath = workdir / "docusign_envelope.json"
    jpath.write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    a = env["draftArgs"]
    where = ("SANDBOX, synthetic jobs only" if env["server"] == SANDBOX_SERVER
             else "PRODUCTION, connected at Go-Live")
    found = [f"    {d['kind']}: {Path(d['path']).name}" for d in env["documents"]]
    lines = [f"DOCUSIGN DRAFT PAYLOAD ({stamp})",
             f"CALL: {'yes' if call else 'no'}"
             + ("" if call else "  (build contract is not a first version - a revision, or an older "
                                "TEST route - payload for inspection only)"),
             f"server        : {env['server']}  ({where})",
             f"template      : {env['templateName']}  (resolved by exact trimmed name on the server)",
             "status        : created  (fixed in the server, which cannot send)",
             f"subject       : {a['email_subject']}",
             "message       :", *("    " + l for l in a["email_blurb"].splitlines()),
             "recipients set:", *(f"    {s}" for s in env["sources"]),
             "template defaults left as they are: " + ", ".join(env["defaultRoles"]),
             f"custom field  : JobNo={a['job_no']}",
             "documents     :", *(found or ["    none listed (no --job-dir)"])]
    if env["documentsMissing"]:
        lines.append("not in the job folder under the CD-7.2 name: " + ", ".join(env["documentsMissing"]))
    if env["flags"]:
        lines += ["flags:", *(f"    {f}" for f in env["flags"])]
    lines += ["staff before sending:", *(f"    - {s}" for s in env["staffBeforeSending"])]
    lines += ["staff after sending:", *(f"    - {s}" for s in env["staffAfterSending"])]
    tpath = workdir / "docusign_payload.txt"
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jpath, tpath


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job", required=True, help="job JSON (its folder is the workdir)")
    ap.add_argument("--job-dir", help="the job's CONTRACT DOCUMENTATION folder (region comes from it)")
    ap.add_argument("--region", help="NSW or QLD, when --job-dir is not given")
    ap.add_argument("--server", choices=(SANDBOX_SERVER, PRODUCTION_SERVER),
                    help="docusign-upload server for the draft (default: from --job-dir, "
                         "the sandbox one only for a job under runtime/docusign-sandbox)")
    ap.add_argument("--osc-contacts",
                    help="the job client's OSC contact list (GET /api/Clients/{ClientID}/Contacts "
                         "as returned): the buyers' names and emails come from it")
    args = ap.parse_args(argv)
    job = Path(args.job)
    workdir = job.parent
    if not workdir.is_dir():
        print(f"DOCUSIGN DRAFT STOPPED: workdir not found: {workdir}", file=sys.stderr)
        return 2
    try:
        try:
            values = json.loads(job.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise PayloadStop(f"job JSON not readable: {job} - {e}")
        osc_contacts = None
        if args.osc_contacts:
            try:
                osc_contacts = json.loads(Path(args.osc_contacts).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise PayloadStop(f"OSC contacts file not readable: {args.osc_contacts} - {e}")
        route = read_build_contract_route(workdir)
        state = state_for(args.job_dir, args.region)
        env = build_envelope(state, values, args.server or server_for(args.job_dir), osc_contacts)
        if args.job_dir:
            pdf = f"BUILD CONTRACT_{dc.doc_suffix(values)}.pdf"
            if not (Path(args.job_dir) / pdf).is_file():
                raise PayloadStop(f"build contract PDF not found in the job folder ({pdf}) "
                                  f"- the draft needs a saved contract")
            env["documents"], env["documentsMissing"] = documents_for(args.job_dir, values)
        else:
            env["documents"], env["documentsMissing"] = [], []
        env["draftArgs"]["documents"] = [dict(d) for d in env["documents"]]
        template, _ = pick_template(state, values)
        env["staffBeforeSending"] = staff_list(
            template, env["flags"], missing_for_template(state, env["documentsMissing"]))
    except PayloadStop as e:
        write_payload(workdir, None, False, stop=str(e))
        print(f"DOCUSIGN DRAFT STOPPED: {e}", file=sys.stderr)
        return 2
    call = route == "PRODUCTION"
    jpath, tpath = write_payload(workdir, env, call)
    print(tpath.read_text(encoding="utf-8"))
    print(f"written: {jpath.name}, {tpath.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
