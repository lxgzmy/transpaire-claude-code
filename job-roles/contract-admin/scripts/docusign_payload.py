r"""Build the DocuSign draft payload for a job (CD-11, 13 Oct 2026).

    python docusign_payload.py --job <workdir>/job.json --job-dir "<CONTRACT DOCUMENTATION>"
                               [--region NSW|QLD] [--server docusign-upload|docusign-upload-prod]

Reads the job JSON and the driver's routes.txt, picks the DocuSign template by
region x buyer type, maps the buyer-side roles, writes the subject, message and
JobNo, lists the job's PDFs under their CD-7.2 names, and leaves two files in
the workdir:

  docusign_envelope.json  - draftArgs: the exact arguments for the docusign-upload
                            server's docusign_draft_preview and docusign_create_draft
                            (the server resolves the template by name)
  docusign_payload.txt    - the mapping with a source per recipient, the roles
                            left as template defaults, the documents, flags, and
                            the list of what staff do in DocuSign before sending

The server comes from where the job folder is: a synthetic job under the
checkout's runtime\docusign-sandbox goes to the sandbox server (docusign-upload),
and every other job folder, a real job's, to the production server
(docusign-upload-prod).

This script never calls DocuSign. The MCP calls are Claude's, per the skill's
references/docusign-draft.md, and the create call is gated by the approval
prompt. Exit codes: 0 payload written (call or no-call stated in the files),
2 a stop condition (reason in docusign_payload.txt and on stderr).
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

# The kinds the docusign-upload server takes, in envelope order (CD-7.2 names).
UPLOAD_KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")

# The two docusign-upload servers (CD-11.1). The sandbox one reads documents only from
# the checkout's runtime/docusign-sandbox, so it only ever gets synthetic jobs; a real
# job's folder needs the production one, registered at Go-Live.
SANDBOX_SERVER = "docusign-upload"
PRODUCTION_SERVER = "docusign-upload-prod"
SANDBOX_DIR = HERE.parents[2] / "runtime" / "docusign-sandbox"


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


def variant_for(values):
    """('single'|'two'|'company', flags). Company (a company/trust owner or a
    sourced company_signatory) wins; three or more owners
    use the 2 Buyers template with the rest flagged (as CD-3.8 fills them)."""
    owners = [_s(values, k) for k in OWNER_KEYS if _s(values, k)]
    if not _s(values, "owner_1"):
        raise PayloadStop("owner_1 is empty - no buyer to address the envelope to")
    if not _s(values, "owner_2") and _s(values, "owner_3"):
        raise PayloadStop("owner_2 is blank but owner_3 is set - fix the job JSON before the draft")
    if any(dc.is_company_owner(o) for o in owners) or _s(values, "company_signatory"):
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
    """The buyer-side roles as the docusign-upload tools take them, each with its source field."""
    roles, sources = [], []
    if template["buyer_roles"] == ["Buyer - Company Guarantor"]:
        name, email = _s(values, "guarantor_name"), _s(values, "guarantor_email")
        if not name:
            raise PayloadStop("guarantor_name missing - the Company template signs through the guarantor")
        if not email:
            raise PayloadStop("guarantor_email missing - no address to send the Company template to")
        roles.append({"role": "Buyer - Company Guarantor", "name": name, "email": email})
        sources.append("Buyer - Company Guarantor: guarantor_name + guarantor_email")
        return roles, sources
    pairs = (("owner_1", "owner_email"), ("owner_2", "owner_2_email"))
    for role, (nkey, ekey) in zip(template["buyer_roles"], pairs):
        name, email = _s(values, nkey), _s(values, ekey)
        if not name:
            continue  # single-buyer template has one role; a second owner never reaches here
        if not email:
            raise PayloadStop(f"{ekey} missing for {role} ({name}) - every buyer needs an email")
        roles.append({"role": role, "name": name, "email": email})
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


def staff_list(template, flags, missing=()):
    """What staff do in DocuSign before sending. The draft holds the job's own PDFs, so there
    is nothing to replace; `missing` is the kinds the template has a place for that the job
    folder does not hold under the CD-7.2 name."""
    items = []
    if "Buyer Witness" in template["default_roles"]:
        items.append("The Buyer Witness role holds the template's default person - change or remove it.")
    if missing:
        items.append(f"Not in the draft, because the job folder has no PDF under its CD-7.2 name: "
                     f"{', '.join(missing)}. Add any the job needs and place their tabs.")
    items.append("Place the tabs on any document the draft report flags (it went in without tabs), "
                 "check every tab sits on its line, then send.")
    return items + flags


def missing_for_template(state, missing):
    """The missing kinds the region's templates have a place for (QLD has no preliminary agreement)."""
    return [k for k in missing if not (state == "QLD" and k == "PRELIMINARY AGREEMENT")]


def build_envelope(state, values, server):
    job_no = _s(values, "job_no")
    if not job_no:
        raise PayloadStop("job_no missing - the JobNo custom field is how a draft is found again")
    template, flags = pick_template(state, values)
    recipients, sources = recipients_for(template, values)
    # Exactly the docusign-upload tools' arguments, so the preview and the create get the same
    # values. The status is not here: "created" is a constant in the server.
    draft_args = {
        "template_name": template["name"],
        "recipients": recipients,
        "email_subject": subject_for(values),
        "email_blurb": message_for(values, template),
        "job_no": job_no,
        "documents": [],
    }
    return {
        "server": server,
        "templateName": template["name"],
        "draftArgs": draft_args,
        "defaultRoles": list(template["default_roles"]),
        "sources": sources,
        "flags": flags,
        "staffBeforeSending": staff_list(template, flags),
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
    lines = [f"DOCUSIGN DRAFT PAYLOAD ({stamp})",
             f"CALL: {'yes' if call else 'no'}"
             + ("" if call else "  (build contract routed TEST - payload for inspection only)"),
             f"server        : {env['server']}  ({where})",
             f"template      : {env['templateName']}  (resolved by exact trimmed name on the server)",
             "status        : created  (fixed in the server, which cannot send)",
             f"subject       : {a['email_subject']}",
             "message       :", *("    " + l for l in a["email_blurb"].splitlines()),
             "recipients set:", *(f"    {s}" for s in env["sources"]),
             "template defaults left as they are: " + ", ".join(env["defaultRoles"]),
             f"custom field  : JobNo={a['job_no']}"]
    if "documents" in env:
        found = [f"    {d['kind']}: {Path(d['path']).name}" for d in env["documents"]]
        lines += ["documents     :", *(found or ["    none listed (no --job-dir)"])]
        if env.get("documentsMissing"):
            lines.append("not in the job folder under the CD-7.2 name: "
                         + ", ".join(env["documentsMissing"]))
    if env["flags"]:
        lines += ["flags:", *(f"    {f}" for f in env["flags"])]
    lines += ["staff before sending:", *(f"    - {s}" for s in env["staffBeforeSending"])]
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
        route = read_build_contract_route(workdir)
        state = state_for(args.job_dir, args.region)
        env = build_envelope(state, values, args.server or server_for(args.job_dir))
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
