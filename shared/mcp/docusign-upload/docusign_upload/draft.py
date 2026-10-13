"""From the tool's arguments and the template to the request, and back.

Plain functions, no network. Argument checks, template parsing, recipient
checks, the carry-or-flag plan, the size and duplicate checks and the request
body are here; the read-back findings follow at the end of the module.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pdfcheck import PdfFile

DRAFT_STATUS = "created"  # the only status this server ever sends
KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")  # envelope order
MAX_BODY_BYTES = 30 * 1024 * 1024
BODY_OVERHEAD_BYTES = 64 * 1024
SUBJECT_MAX = 100
BLURB_MAX = 10000
JOB_NO_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEAD_STATUSES = {"voided", "declined", "deleted"}
FRESH_ID_START = 9001


class Stop(Exception):
    """A stop condition: nothing is created, and the message says why."""


@dataclass(frozen=True)
class TemplateDoc:
    document_id: str
    kind: str
    pages: int


@dataclass(frozen=True)
class TemplateRole:
    role: str
    recipient_id: str
    routing_order: str
    recipient_type: str


@dataclass(frozen=True)
class Template:
    template_id: str
    name: str
    documents: tuple[TemplateDoc, ...]
    roles: tuple[TemplateRole, ...]


@dataclass(frozen=True)
class Recipient:
    role: str
    name: str
    email: str


@dataclass(frozen=True)
class PlannedDoc:
    kind: str
    file: PdfFile
    carry: bool
    template_document_id: str | None
    reason: str


@dataclass(frozen=True)
class Plan:
    template: Template
    recipients: tuple[tuple[Recipient, TemplateRole], ...]
    documents: tuple[PlannedDoc, ...]
    email_subject: str
    email_blurb: str
    job_no: str


def check_text_args(job_no: str, email_subject: str, email_blurb: str) -> None:
    if not JOB_NO_RE.match(str(job_no)):
        raise Stop("job_no must be 1 to 20 letters, digits or hyphens; it is used in the "
                   "duplicate search")
    if not str(email_subject).strip():
        raise Stop("email_subject is empty")
    if len(email_subject) > SUBJECT_MAX:
        raise Stop(f"email_subject has {len(email_subject)} characters; DocuSign allows {SUBJECT_MAX}")
    if len(email_blurb) > BLURB_MAX:
        raise Stop(f"email_blurb has {len(email_blurb)} characters; DocuSign allows {BLURB_MAX}")


def check_kinds(kinds: list[str]) -> list[str]:
    """The kinds normalised to capitals, in the order given. Stops on unknown or repeated kinds."""
    norm = [str(k).strip().upper() for k in kinds]
    unknown = sorted({k for k in norm if k not in KINDS})
    if unknown:
        raise Stop(f"unknown document kind: {', '.join(unknown)}. Use {', '.join(KINDS)}")
    twice = sorted({k for k in norm if norm.count(k) > 1})
    if twice:
        raise Stop(f"document kind given twice: {', '.join(twice)}")
    if "BUILD CONTRACT" not in norm:
        raise Stop("no BUILD CONTRACT document; the draft needs the job's build contract")
    return norm


def kind_of(document_name: str) -> str | None:
    """The one kind whose words appear in a template document's name, else None."""
    up = str(document_name).upper()
    hits = [k for k in KINDS if k in up]
    return hits[0] if len(hits) == 1 else None


def pick_template(candidates: list[dict[str, Any]], wanted: str) -> dict[str, Any]:
    """The one template whose name, trimmed, equals the wanted name, trimmed."""
    target = wanted.strip()
    hits = [t for t in candidates if str(t.get("name", "")).strip() == target]
    if len(hits) != 1:
        names = sorted({str(t.get("name", "")).strip() for t in candidates})
        raise Stop(f"template {target!r} matched {len(hits)} templates; the search returned: "
                   f"{', '.join(names) if names else 'nothing'}")
    return hits[0]


def parse_template(raw: dict[str, Any]) -> Template:
    """Documents by kind (name match, never id or order) and roles. Never echoes a document name."""
    documents = []
    for d in raw.get("documents") or []:
        kind = kind_of(d.get("name", ""))
        if kind is None:
            raise Stop(f"template document {d.get('documentId')} is not one of {', '.join(KINDS)}; "
                       "the template has changed and a person needs to look")
        documents.append(TemplateDoc(str(d.get("documentId")), kind, int(d.get("pages") or 0)))
    kinds = [d.kind for d in documents]
    twice = sorted({k for k in kinds if kinds.count(k) > 1})
    if twice:
        raise Stop(f"the template holds more than one {', '.join(twice)} document; a person needs to look")
    roles = []
    for recipient_type, items in (raw.get("recipients") or {}).items():
        if not isinstance(items, list):
            continue
        for r in items:
            if r.get("roleName"):
                roles.append(TemplateRole(str(r["roleName"]), str(r.get("recipientId", "")),
                                          str(r.get("routingOrder", "")), recipient_type))
    return Template(str(raw.get("templateId", "")), str(raw.get("name", "")).strip(),
                    tuple(documents), tuple(roles))


def check_recipients(raw: list[dict[str, str]],
                     template: Template) -> tuple[tuple[Recipient, TemplateRole], ...]:
    """Each buyer role must be a signer role on the template, named exactly (capitals included)."""
    if not raw:
        raise Stop("no recipients given; the draft needs at least one buyer role")
    by_role = {r.role: r for r in template.roles}
    seen: set[str] = set()
    out = []
    for item in raw:
        role = str(item.get("role", ""))
        name = str(item.get("name", "")).strip()
        email = str(item.get("email", "")).strip()
        if role in seen:
            raise Stop(f"role {role!r} is given twice")
        seen.add(role)
        trole = by_role.get(role)
        if trole is None:
            raise Stop(f"role {role!r} is not on template {template.name!r}; its roles are: "
                       f"{', '.join(sorted(by_role))}. Role names match exactly, capitals included")
        if trole.recipient_type != "signers":
            raise Stop(f"role {role!r} is not a signer on the template")
        if not name:
            raise Stop(f"role {role!r} has no name")
        if not EMAIL_RE.match(email):
            raise Stop(f"role {role!r} has a malformed email address")
        out.append((Recipient(role, name, email), trole))
    return tuple(out)


def plan_documents(files: list[tuple[str, PdfFile]], template: Template) -> tuple[PlannedDoc, ...]:
    """Carry or flag each job document, in envelope order. The build contract must carry."""
    by_kind = {d.kind: d for d in template.documents}
    given = dict(files)
    planned = []
    for kind in KINDS:
        f = given.get(kind)
        if f is None:
            continue
        tdoc = by_kind.get(kind)
        if tdoc is None:
            planned.append(PlannedDoc(kind, f, False, None, f"the template has no {kind} document"))
        elif tdoc.pages != f.pages:
            planned.append(PlannedDoc(kind, f, False, tdoc.document_id,
                                      f"{f.pages} pages, the template's has {tdoc.pages}"))
        else:
            planned.append(PlannedDoc(kind, f, True, tdoc.document_id, ""))
    if not planned or planned[0].kind != "BUILD CONTRACT":
        raise Stop("no BUILD CONTRACT document; the draft needs the job's build contract")
    if not planned[0].carry:
        raise Stop(f"BUILD CONTRACT: {planned[0].reason}. The contract is a fixed form, so a "
                   "different page count means its layout changed; a person checks the fill")
    return tuple(planned)


def estimated_body_bytes(documents: tuple[PlannedDoc, ...]) -> int:
    return BODY_OVERHEAD_BYTES + sum(4 * ((d.file.bytes + 2) // 3) for d in documents)


def check_size(documents: tuple[PlannedDoc, ...]) -> None:
    estimate = estimated_body_bytes(documents)
    if estimate > MAX_BODY_BYTES:
        biggest = max(documents, key=lambda d: d.file.bytes)
        raise Stop(f"the request would be about {estimate / 1048576:.1f} MiB, over the "
                   f"{MAX_BODY_BYTES / 1048576:.0f} MiB limit (largest: {biggest.kind}, "
                   f"{biggest.file.bytes / 1048576:.1f} MB)")


def find_duplicate(envelopes: list[dict[str, Any]], job_no: str) -> dict[str, Any] | None:
    """The first live envelope carrying this JobNo. One whose custom fields did not come back
    counts as a match: the search already filtered on JobNo, and missing a duplicate is worse."""
    for env in envelopes:
        if str(env.get("status", "")).lower() in DEAD_STATUSES:
            continue
        fields = (env.get("customFields") or {}).get("textCustomFields")
        if fields is None or any(f.get("name") == "JobNo" and str(f.get("value", "")).strip() == job_no
                                 for f in fields):
            return env
    return None


def _fresh_ids(template: Template, count: int) -> list[str]:
    used = {d.document_id for d in template.documents}
    ids, n = [], FRESH_ID_START
    while len(ids) < count:
        if str(n) not in used:
            ids.append(str(n))
        n += 1
    return ids


def build_body(plan: Plan) -> dict[str, Any]:
    """The Envelopes:create body. Reads each PDF now, after every check has passed."""
    signers = [{"recipientId": t.recipient_id, "roleName": r.role, "routingOrder": t.routing_order,
                "name": r.name, "email": r.email} for r, t in plan.recipients]
    fresh = iter(_fresh_ids(plan.template, sum(1 for d in plan.documents if not d.carry)))
    composites: list[dict[str, Any]] = []
    for n, d in enumerate(plan.documents, start=1):
        document = {"documentId": d.template_document_id if d.carry else next(fresh),
                    "name": d.file.name, "fileExtension": "pdf",
                    "documentBase64": base64.b64encode(Path(d.file.path).read_bytes()).decode("ascii")}
        recipients = {"signers": [dict(s) for s in signers]}
        if d.carry:
            composites.append({
                "compositeTemplateId": str(n),
                "serverTemplates": [{"sequence": "1", "templateId": plan.template.template_id}],
                "inlineTemplates": [{"sequence": "2", "recipients": recipients}],
                "document": document})
        else:
            composites.append({
                "compositeTemplateId": str(n),
                "inlineTemplates": [{"sequence": "1", "recipients": recipients}],
                "document": document})
    # With composites, envelope custom fields belong in an inline template (root ones are ignored).
    composites[0]["inlineTemplates"][0]["customFields"] = {"textCustomFields": [
        {"name": "JobNo", "value": plan.job_no, "show": "false", "required": "false"}]}
    return {"status": DRAFT_STATUS, "emailSubject": plan.email_subject,
            "emailBlurb": plan.email_blurb, "compositeTemplates": composites}


def plan_view(plan: Plan) -> dict[str, Any]:
    """What the preview shows and the create repeats: everything a person approves."""
    sent_roles = {r.role for r, _ in plan.recipients}
    given_kinds = {d.kind for d in plan.documents}
    return {
        "template": plan.template.name,
        "status": DRAFT_STATUS,
        "job_no": plan.job_no,
        "email_subject": plan.email_subject,
        "recipients_set": [{"role": r.role, "name": r.name, "email": r.email} for r, _ in plan.recipients],
        "roles_left_as_template_defaults": [t.role for t in plan.template.roles if t.role not in sent_roles],
        "documents": [{"kind": d.kind, "file": d.file.name, "pages": d.file.pages,
                       "tabs": "carried from the template" if d.carry else f"none, flagged: {d.reason}"}
                      for d in plan.documents],
        "template_documents_left_out": [d.kind for d in plan.template.documents
                                        if d.kind not in given_kinds],
        "estimated_request_mib": round(estimated_body_bytes(plan.documents) / 1048576, 1),
    }
