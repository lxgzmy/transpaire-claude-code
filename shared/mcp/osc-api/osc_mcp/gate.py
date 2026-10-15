"""Confirmation gate for OnSite Companion writes (production).

Every write goes through two steps, and nothing reaches OSC between them:

1. build_plan() matches the request to one of the approved contract-intake
   changes, checks the target belongs to the job the person is working on,
   reads the target's current values from OSC, works out exactly which fields
   change (old value and new value), and builds the smallest request that makes
   only those changes. Anything ambiguous, unknown or protected blocks the plan.
   render() turns the plan into a short confirmation in plain words.
2. confirm() takes the confirmation code from step 1 and the person's own
   reply. Only a plain "yes" goes ahead. The target is read again first; if
   anything differs from what was confirmed, nothing is sent and a fresh
   confirmation is returned instead. Otherwise the stored request (never a
   new one) is sent, and the record is read back to check that the confirmed
   fields changed and nothing else did.

A batch (build_batch) is the same two steps for several changes to one job:
each change is planned as above, the person reads one confirmation listing
them all, and one plain "yes" sends them in order. Everything is checked
again before the first is sent; each later change is planned again just
before it goes, and if it no longer matches what was approved the batch
stops there and asks again for the rest. A change can use the ID of a
record an earlier change in the batch creates ("{{1.clientID}}").

Codes live in this server process only: a new chat starts with none, and a
code is used once, replaced by a newer check of the same target, or expires.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import mimetypes
from typing import Any

import httpx

from .client import OSCClient, OSCError
from .config import Config

GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?[^ ]*)?$")
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I/L to misread


class GateError(Exception):
    """A reason the change cannot go ahead, worded for the person."""


class AlreadyDone(GateError):
    """OSC already holds what the change asks for. In a batch the change is left out, not a blocker."""


NOTHING_TO_CHANGE = "OnSite Companion already holds these values, so there is nothing to change."
REF = re.compile(r"\{\{(\d+)\.(clientID|personID|jobID)\}\}")
CREATED_ID = {"create_client": "clientID", "create_person": "personID", "create_job": "jobID"}
MAX_BATCH = 25


# ---------------------------------------------------------------------------
# What may be written
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    method: str
    route: str
    kind: str
    what: str
    needs_job: bool = True

    def match(self, method: str, path: str) -> dict[str, str] | None:
        if method != self.method:
            return None
        parts = []
        for segment in self.route.split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                parts.append(f"(?P<{segment[1:-1]}>[^/]+)")
            else:
                parts.append(re.escape(segment))
        found = re.fullmatch("/".join(parts), path.rstrip("/"), flags=re.I)
        return found.groupdict() if found else None


# The contract-intake changes (issue #34, Word items 4-9). Anything else is a
# person's job in OnSite Companion. Adding a route is a reviewed code change.
APPROVED = (
    Rule("POST", "/api/Clients", "create_client", "new client", needs_job=False),
    Rule("PATCH", "/api/Clients/{ClientID}", "update_client", "client"),
    Rule("POST", "/api/Persons", "create_person", "new person", needs_job=False),
    Rule("PATCH", "/api/Persons/{PersonID}", "update_person", "person"),
    Rule("POST", "/api/Clients/{ClientID}/Contacts/{PersonID}", "link_client", "client contact"),
    Rule("PATCH", "/api/Clients/{ClientID}/Contacts/{PersonID}", "update_client_link", "client contact"),
    Rule("POST", "/api/Jobs/{JobID}/Contacts/{PersonID}", "link_job", "job contact"),
    Rule("PATCH", "/api/Jobs/{JobID}/Contacts/{PersonID}", "update_job_link", "job contact"),
    Rule("POST", "/api/Jobs", "create_job", "new job", needs_job=False),
    Rule("PATCH", "/api/Jobs/{JobID}", "update_job", "job"),
    Rule("POST", "/api/JobActivities/{JobActivityID}/Complete", "complete_activity", "activity"),
    Rule("PUT", "/api/JobActivities/{JobActivityID}/Questions/{CompletionQuestionID}",
         "answer_question", "answer"),
    Rule("POST", "/api/Jobs/{JobID}/Messages", "job_message", "job message"),
    Rule("POST", "/api/JobActivities/{JobActivityID}/Messages", "activity_message", "activity message"),
)

CREATE_KINDS = {"create_client", "create_person", "create_job", "link_client", "link_job"}
MESSAGE_KINDS = {"job_message", "activity_message"}

ADDRESS = frozenset({"country", "line1", "line2", "poBoxNumber", "postcode", "propertyName", "state", "suburb"})
SITE_ADDRESS = frozenset({"blockNumber", "country", "dpLotNumber", "line1", "line2", "lotNumber",
                          "mapFriendlyAddress", "postcode", "propertyName", "sectionNumber", "state", "suburb"})
WORK_CONTACT = frozenset({"contactDetailsPrimaryCommunicationMethodID", "direct", "email", "fax", "mobile", "phone"})
PERSONAL_CONTACT = frozenset({"contactDetailsPrimaryCommunicationMethodID", "email", "fax", "mobile", "phone"})
CUSTOM = "customFieldValues"

_CLIENT = {"abn": None, "entityCode": None, "name": None, "postalAddress": ADDRESS, "salespersonID": None,
           "workAddress": ADDRESS, "workContactDetails": WORK_CONTACT, "workUrl": None}
_PERSON = {"companyName": None, CUSTOM: CUSTOM, "dateOfBirth": None, "givenName": None, "honorific": None,
           "jobDescription": None, "middleNames": None, "personalAddress": ADDRESS,
           "personalContactDetails": PERSONAL_CONTACT, "postalAddress": ADDRESS, "salespersonID": None,
           "surname": None, "workAddress": ADDRESS, "workContactDetails": WORK_CONTACT, "workUrl": None}
_JOB = {"contractNumber": None, "contractValueExcludingGst": None, "contractValueIncludingGst": None,
        CUSTOM: CUSTOM, "regionID": None, "siteAddress": SITE_ADDRESS, "startDate": None}
FIELDS: dict[str, dict[str, Any]] = {
    "create_client": _CLIENT, "update_client": _CLIENT,
    "create_person": _PERSON, "update_person": _PERSON,
    "link_client": {"isPrimaryContact": None, "isSecondaryContact": None,
                    "preferredCommunicationGroupID": None, "relationship": None},
    "link_job": {"preferredCommunicationGroupID": None, "relationship": None},
    "create_job": {**_JOB, "clientID": None, "workflowTemplateID": None},
    "update_job": _JOB,
    "complete_activity": {"completionDate": None},
    "answer_question": {"completionAnswerStateID": None, "note": None},
}
FIELDS["update_client_link"] = FIELDS["link_client"]
FIELDS["update_job_link"] = FIELDS["link_job"]

PRICE = "the contract price is entered in DataBuild only, never in OnSite Companion"
PROTECTED: dict[str, dict[str, str]] = {
    "create_job": {"contractNumber": "OnSite Companion generates the contract number",
                   "contractValueIncludingGst": PRICE, "contractValueExcludingGst": PRICE},
    "update_job": {"contractNumber": "the contract number is never changed through Claude",
                   "contractValueIncludingGst": PRICE, "contractValueExcludingGst": PRICE,
                   "regionID": "the region is set when the job is created"},
    "create_client": {"entityCode": "the DataBuild client code is entered by a person"},
    "update_client": {"entityCode": "the DataBuild client code is entered by a person"},
}

# Body field -> where the same value sits in the GET record, when it differs.
ALIASES = {
    "contactDetailsPrimaryCommunicationMethodID": ("primaryCommunicationMethod",
                                                   "contactDetailsPrimaryCommunicationMethodID"),
    "preferredCommunicationGroupID": ("preferredCommunicationGroup", "preferredCommunicationGroupID"),
}
# Read-only fields OSC recalculates when a name part changes.
DERIVED = {"givenName": ("fullName",), "middleNames": ("fullName",), "surname": ("fullName",),
           "honorific": ("fullName",), "name": ("clientName",)}

FORM_KEY = re.compile(r"^(Subject|Body|Documents\[\d+\]\.description)$")
FILE_KEY = re.compile(r"^Documents\[\d+\]\.file$")

LABELS = {
    "siteAddress": "Site address", "postalAddress": "Postal address", "workAddress": "Work address",
    "personalAddress": "Personal address", "workContactDetails": "Work contact",
    "personalContactDetails": "Personal contact", "name": "Name", "abn": "ABN", "givenName": "Given name",
    "middleNames": "Middle names", "surname": "Surname", "honorific": "Title", "dateOfBirth": "Date of birth",
    "companyName": "Company name", "jobDescription": "Job description", "workUrl": "Website",
    "salespersonID": "Salesperson", "startDate": "Start date", "regionID": "Region",
    "workflowTemplateID": "Workflow template", "clientID": "Client", "isPrimaryContact": "Primary contact",
    "isSecondaryContact": "Secondary contact", "preferredCommunicationGroupID": "Preferred communication",
    "relationship": "Relationship", "completionDate": "Completion date", "completionAnswerStateID": "Answer",
    "note": "Note", "entityCode": "Entity code", "contractNumber": "Contract number",
    "contractValueIncludingGst": "Contract price incl. GST", "contractValueExcludingGst": "Contract price excl. GST",
    "line1": "street", "line2": "line 2", "lotNumber": "lot number", "dpLotNumber": "DP lot number",
    "blockNumber": "block number", "sectionNumber": "section number", "poBoxNumber": "PO box",
    "postcode": "postcode", "state": "state", "suburb": "suburb", "country": "country",
    "propertyName": "property name", "mapFriendlyAddress": "map address", "email": "email",
    "mobile": "mobile", "phone": "phone", "fax": "fax", "direct": "direct line",
    "contactDetailsPrimaryCommunicationMethodID": "preferred method",
}

YES = {"yes", "y", "yep", "yeah", "ok", "okay", "confirm", "confirmed", "approve", "approved",
       "go ahead", "proceed", "do it", "yes please", "yes go ahead",
       "是", "是的", "确认", "好", "好的", "可以", "同意"}
NO = {"no", "n", "nope", "cancel", "stop", "don't", "do not", "no thanks",
      "不", "不要", "否", "取消", "不用"}


LOT_PAGE = 500  # jobs read per lot-number check; reaching it means the check could be incomplete
# The only activities the intake touches (issue #34 items 7-8), matched by name without the "a) " prefix.
DATABUILD_ACTIVITY = "create job within databuild"
INTAKE_ACTIVITIES = {"initial contact", "follow up initial contact", DATABUILD_ACTIVITY,
                     "receive eoi approval to proceed from marketer"}


def _activity_name(text: Any) -> str:
    return re.sub(r"^\s*[a-z]\)\s*", "", re.sub(r"\s+", " ", str(text or "")).strip().lower())
NAME_FILLER = {"and", "pty", "ltd", "atf", "the", "trust", "family", "no", "no.1", "acn", "abn"}


def _q(text: str) -> str:
    """A value inside an OData string literal: apostrophes doubled."""
    return str(text).replace("'", "''")


def _describe(plan: Plan) -> str:
    return plan.headline or (plan.rule.what if plan.rule else f"{plan.method} {plan.path}")


def _created_name(plan: Plan) -> str:
    body = plan.inputs.get("body") or {}
    if plan.rule.kind == "create_client":
        return str(body.get("name") or "the new client")
    if plan.rule.kind == "create_person":
        return " ".join(str(body.get(k)) for k in ("givenName", "surname") if body.get(k)) or "the new person"
    return plan.job_label or "the new job"


def label(path: str) -> str:
    head, _, tail = path.partition(".")
    first = LABELS.get(head, head)
    return f"{first}, {LABELS.get(tail, tail)}" if tail else first


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------
def _norm(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return value[:10] if ISO_DATE.match(value) else value
    return json.dumps(value, sort_keys=True, default=str)


def same(a: Any, b: Any) -> bool:
    return _norm(a) == _norm(b)


def _parse_dt(text: Any) -> datetime | None:
    m = ISO_DATE.match(text) if isinstance(text, str) else None
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)


def fmt_date(value: Any) -> str:
    dt = value if isinstance(value, datetime) else _parse_dt(value)
    return f"{dt.day} {dt.strftime('%b')} {dt.year}" if dt else str(value)


def _shown(value: Any) -> str:
    if value is None or value == "":
        return "empty"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str) and ISO_DATE.match(value):
        return fmt_date(value)
    text = str(value)
    text = text if len(text) <= 120 else text[:117] + "..."
    return f'"{text}"'


def _current(record: dict | None, key: str) -> Any:
    if not isinstance(record, dict):
        return None
    if key in record:
        return record[key]
    alias = ALIASES.get(key)
    if alias and isinstance(record.get(alias[0]), dict):
        return record[alias[0]].get(alias[1])
    return None


def _strip(obj: Any) -> Any:
    """Drop OSC's per-field timestamps and schedule forecasts (they move on their own)."""
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items()
                if not k.endswith("LastUpdatedOnUtc") and not k.startswith("forecasted")}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _flatten(obj: Any, prefix: str = "", out: dict | None = None) -> dict[str, Any]:
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == CUSTOM and isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        out[f"{prefix}{CUSTOM}.{str(item.get('customFieldID')).lower()}"] = item.get("value")
            else:
                _flatten(v, f"{prefix}{k}.", out)
    elif isinstance(obj, list):
        out[prefix.rstrip(".")] = json.dumps(obj, sort_keys=True, default=str)
    else:
        out[prefix.rstrip(".")] = obj
    return out


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Upload checks (metadata only; a file is opened only when the change is sent)
# ---------------------------------------------------------------------------
def _forms(p: str) -> set[str]:
    out = {os.path.normcase(os.path.abspath(p))}
    try:
        out.add(os.path.normcase(os.path.realpath(p)))
    except OSError:
        pass
    return out


def _inside(candidate: str, roots: tuple[str, ...]) -> bool:
    for root in roots:
        for r in _forms(root):
            r = r.rstrip("\\/") + os.sep
            if any(c.startswith(r) for c in _forms(candidate)):
                return True
    return False


def check_uploads(files: dict[str, str], roots: tuple[str, ...]) -> list[dict[str, Any]]:
    checks = []
    for name, value in files.items():
        p = Path(value)
        entry: dict[str, Any] = {"field": name, "path": value, "ok": False}
        if not p.is_absolute():
            entry["problem"] = "not an absolute path"
        elif not roots:
            entry["problem"] = "no upload roots configured (OSC_UPLOAD_ROOTS)"
        elif not _inside(value, roots):
            entry["problem"] = "outside the allowed upload roots"
        elif not p.is_file():
            entry["problem"] = "not an existing regular file on the MCP server machine"
        else:
            stat = p.stat()
            entry.update(ok=True, bytes=stat.st_size, modified=stat.st_mtime_ns)
        checks.append(entry)
    return checks


# ---------------------------------------------------------------------------
# Plans and pending confirmations
# ---------------------------------------------------------------------------
@dataclass
class Plan:
    method: str
    path: str
    job_id: str
    inputs: dict[str, Any]
    rule: Rule | None = None
    params: dict[str, str] = field(default_factory=dict)
    job_label: str = ""
    headline: str = ""
    changes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    request: dict[str, Any] = field(default_factory=dict)
    before: dict[str, Any] | None = None
    reads: dict[str, Any] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)
    refs: dict[str, dict[str, Any]] = field(default_factory=dict)  # batch placeholders -> the record they create
    done: bool = False  # blocked only because OSC already holds it
    step: int = 0       # the change's number in its batch, as the caller numbered it

    @property
    def fingerprint(self) -> str:
        return digest({"reads": self.reads, "request": self.request, "changes": self.changes,
                       "warnings": self.warnings, "blocked": self.blocked})

    def signature(self, ids: dict[str, str] | None = None) -> str:
        """What would be sent and what it changes; placeholders swapped for the IDs now known."""
        text = json.dumps({"method": self.method, "path": self.path.lower(), "request": self.request,
                           "changes": [[c["field"], c["current"], c["new"], c["action"]] for c in self.changes],
                           "files": self.reads.get("files")}, sort_keys=True, default=str)
        for placeholder, real in (ids or {}).items():
            text = text.replace(placeholder, real).replace(placeholder.lower(), real.lower())
        return hashlib.sha256(text.encode()).hexdigest()

    @property
    def target_key(self) -> str:
        key = f"{self.method} {self.path.lower()}"
        if self.rule and self.rule.kind in CREATE_KINDS:
            key += " " + digest(self.inputs.get("body"))[:12]
        return key


@dataclass
class Batch:
    """Several changes to one job (or the client, people and job of a new intake), one confirmation."""
    job_id: str
    changes: list[Any]
    steps: list[Plan] = field(default_factory=list)
    left_out: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    job_label: str = ""

    @property
    def fingerprint(self) -> str:
        return digest({"steps": [p.fingerprint for p in self.steps], "left_out": self.left_out,
                       "blocked": self.blocked})

    @property
    def target_key(self) -> str:
        return "batch " + (self.job_id.lower() or digest(self.changes)[:12])


@dataclass
class Pending:
    code: str
    plan: Plan | Batch
    created: float


def _change_lines(plan: Plan) -> list[str]:
    lines = []
    for c in plan.changes:
        cur, new = c.get("current_shown", _shown(c["current"])), c.get("new_shown", _shown(c["new"]))
        if c["action"] == "new":
            lines.append(f"- {c['label']}: {new}")
        elif c["action"] == "clear":
            lines.append(f"- {c['label']}: now {cur}, will be cleared")
        else:
            lines.append(f"- {c['label']}: now {cur}, will be {new}")
    return lines


def _blocked_text(reasons: list[str]) -> str:
    return "\n".join(["Nothing was changed in OnSite Companion."] + [f"- {reason}" for reason in reasons])


def render_batch(batch: Batch, environment: str = "production") -> str:
    """One confirmation for every change in a batch, in the order they will be made."""
    if batch.blocked:
        return _blocked_text(batch.blocked)
    n = len(batch.steps)
    lines = [f"OnSite Companion ({environment}): please check this before anything changes.", ""]
    if batch.job_label:
        lines.append(f"Job: {batch.job_label}")
    lines += [f"{n} change{'s' if n != 1 else ''}, made in this order:", ""]
    for i, plan in enumerate(batch.steps, 1):
        lines.append(f"{i}. {plan.headline[:1].upper()}{plan.headline[1:]}")
        lines += ["   " + line for line in _change_lines(plan)]
        lines += [f"   Note: {x}" for x in plan.notes]
        lines += [f"   Warning: {x}" for x in plan.warnings]
    lines.append("")
    if any(p.rule and p.rule.kind not in CREATE_KINDS | MESSAGE_KINDS for p in batch.steps):
        lines.append("Nothing else on these records changes.")
    lines += [f"Already in OnSite Companion, so left out: {x}" for x in batch.left_out]
    lines.append("")
    what = f"all {n} changes" if n > 1 else "this change"
    lines.append(f'Reply "yes" to make {what}, or "no" to leave OnSite Companion as it is.')
    return "\n".join(lines)


def render(plan: Plan, environment: str = "production") -> str:
    """The confirmation a person reads before anything changes."""
    if plan.blocked:
        return _blocked_text(plan.blocked)
    lines = [f"OnSite Companion ({environment}): please check this before anything changes.", ""]
    if plan.job_label:
        lines.append(f"Job: {plan.job_label}")
    lines.append(f"Change: {plan.headline}")
    lines.append("")
    lines += _change_lines(plan)
    lines.append("")
    if plan.rule and plan.rule.kind not in CREATE_KINDS | MESSAGE_KINDS:
        lines.append(f"Nothing else on this {plan.rule.what} changes.")
    lines += [f"Note: {n}" for n in plan.notes]
    lines += [f"Warning: {w}" for w in plan.warnings]
    lines.append("")
    lines.append('Reply "yes" to make this change, or "no" to leave OnSite Companion as it is.')
    return "\n".join(lines)


def reply_kind(reply: str, code: str = "") -> str:
    """'yes', 'no' or 'other' for the person's own reply."""
    text = (reply or "").strip().lower()
    if code:
        text = text.replace(code.lower(), " ")
    text = re.sub(r"[\s.!,。！，]+", " ", text).strip()
    if text in YES:
        return "yes"
    if text in NO:
        return "no"
    return "other"


class Gate:
    def __init__(self, client: OSCClient, config: Config):
        self.client = client
        self.config = config
        self.pending: dict[str, Pending] = {}
        self._lookups: dict[str, dict[str, str]] = {}
        self._live: tuple[float, dict[str, Any]] | None = None

    # ---- reads ----------------------------------------------------------
    async def _get(self, path: str, query: dict | None, body: Any, what: str) -> Any:
        try:
            res = await self.client.request("GET", path, params=query, json_body=body)
        except OSCError as exc:
            raise GateError(f"Could not read the {what} from OnSite Companion ({exc}).") from exc
        except httpx.HTTPError as exc:
            raise GateError(f"Could not reach OnSite Companion to read the {what}.") from exc
        if not res.get("ok"):
            raise GateError(f"Could not read the {what} from OnSite Companion (HTTP {res.get('status')}).")
        return res.get("data")

    @staticmethod
    def _rows(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("value", "pagedItems", "jobWorkflowTemplates"):
                if isinstance(data.get(key), list):
                    return data[key]
        raise GateError("OnSite Companion answered in a shape this check does not know.")

    async def _find(self, path: str, flt: str, what: str, body: Any = None, top: int = 20) -> list[dict]:
        return self._rows(await self._get(path, {"$filter": flt, "$top": top}, body, what))

    async def _one(self, path: str, id_field: str, id_value: str, what: str, body: Any = None) -> dict:
        rows = await self._find(path, f"{id_field} eq {id_value}", what, body, top=2)
        if not rows:
            raise GateError(f"No {what} with that ID exists in OnSite Companion.")
        if len(rows) > 1:
            raise GateError(f"More than one {what} matched that ID, so the target is ambiguous.")
        return rows[0]

    async def _job(self, job_id: str) -> dict:
        return await self._one("/api/Jobs", "jobID", job_id, "job", {"shouldShowMyJobsOnly": False})

    async def _activity(self, activity_id: str) -> dict:
        return await self._one("/api/JobActivities", "jobActivityID", activity_id, "job activity")

    async def _lookup(self, name: str, required: bool = False) -> dict[str, str]:
        if name in self._lookups:
            return self._lookups[name]
        sources = {
            "regions": ("/api/Regions", "regionID", "description"),
            "templates": ("/api/Jobs/WorkflowTemplates", "workflowTemplateID", "name"),
            "job_fields": ("/api/Jobs/CustomFieldSchemas", "customFieldID", "label"),
            "person_fields": ("/api/Persons/CustomFieldSchemas", "customFieldID", "label"),
            "methods": ("/api/Miscellaneous/ContactDetailsPrimaryCommunicationMethods",
                        "contactDetailsPrimaryCommunicationMethodID", "description"),
            "groups": ("/api/Miscellaneous/PreferredCommunicationGroups", "preferredCommunicationGroupID",
                       "description"),
            "answers": ("/api/JobActivities/CompletionAnswerStates", "completionAnswerStateID", "description"),
        }
        path, key, text = sources[name]
        query = {"$top": 500} if name in {"regions", "job_fields", "person_fields", "answers"} else None
        try:
            rows = self._rows(await self._get(path, query, None, name.replace("_", " ")))
        except GateError:
            if required:
                raise
            return {}
        table = {str(r.get(key)).lower(): str(r.get(text)) for r in rows if isinstance(r, dict)}
        self._lookups[name] = table
        return table

    async def live_check(self, force: bool = False) -> dict[str, Any]:
        """Is this the OnSite Companion staff use, or a frozen copy? Judged by the newest job."""
        now = time.monotonic()
        if self._live and not force and now - self._live[0] < 600:
            return self._live[1]
        data = await self._get("/api/Jobs", {"$orderby": "createdOnUtc desc", "$top": 1,
                                             "$select": "contractNumber,createdOnUtc"},
                               {"shouldShowMyJobsOnly": False}, "newest job")
        rows = self._rows(data)
        created = _parse_dt(rows[0].get("createdOnUtc")) if rows else None
        if created is None:
            result = {"live": False, "reason": "OnSite Companion returned no job to date-check."}
        else:
            age = (datetime.now(timezone.utc) - created).days
            result = {"live": age <= self.config.stale_after_days, "newest_job_created": created.date().isoformat(),
                      "age_days": age, "newest_contract": rows[0].get("contractNumber")}
            if not result["live"]:
                result["reason"] = (
                    f"The newest job in this OnSite Companion was created on {fmt_date(created)}, {age} days "
                    "ago. That looks like a frozen copy rather than the system staff use, so nothing is written.")
        self._live = (now, result)
        return result

    # ---- planning -------------------------------------------------------
    async def build_plan(self, method: str, path: str, job_id: str = "", body: Any = None,
                         form: dict | None = None, files: dict | None = None,
                         refs: dict[str, dict[str, Any]] | None = None) -> Plan:
        plan = Plan(method=(method or "").upper(), path=(path or "").strip(), job_id=(job_id or "").strip(),
                    inputs={"method": method, "path": path, "job_id": job_id, "body": body,
                            "form": form, "files": files}, refs=dict(refs or {}))
        try:
            await self._plan(plan, body, form, files)
        except GateError as exc:
            plan.blocked.append(str(exc))
            plan.done = isinstance(exc, AlreadyDone)
        if not plan.blocked and not plan.changes:
            plan.blocked.append(NOTHING_TO_CHANGE)
            plan.done = True
        return plan

    async def build_batch(self, job_id: str, changes: Any) -> Batch:
        """Plan every change of a batch. Any change that cannot go ahead blocks the whole batch."""
        batch = Batch(job_id=(job_id or "").strip(), changes=changes if isinstance(changes, list) else [])
        if not batch.changes:
            batch.blocked.append("The batch has no changes in it.")
            return batch
        if len(batch.changes) > MAX_BATCH:
            batch.blocked.append(f"A batch takes at most {MAX_BATCH} changes. Split it into stages.")
            return batch
        refs: dict[str, dict[str, Any]] = {}
        targets: dict[str, int] = {}
        for n, change in enumerate(batch.changes, 1):
            if not isinstance(change, dict) or not change.get("method") or \
                    set(change) - {"method", "path", "body", "form", "files"}:
                batch.blocked.append(f"Change {n}: give method and path, plus body (or form and files), "
                                     "and nothing else.")
                continue
            inputs = {"method": change.get("method"), "path": change.get("path"), "job_id": batch.job_id,
                      "body": change.get("body"), "form": change.get("form"), "files": change.get("files")}
            unknown = [m.group(0) for m in REF.finditer(json.dumps(inputs, default=str))
                       if m.group(0) not in refs]
            if unknown:
                batch.blocked.append(f"Change {n} uses {unknown[0]}, which is not the ID of a record that an "
                                     "earlier change in this batch creates.")
                continue
            plan = await self.build_plan(**inputs, refs=refs)
            plan.step = n
            if plan.done:
                batch.left_out.append(f"change {n} ({_describe(plan)}): {plan.blocked[0]}")
                continue
            if plan.blocked:
                batch.blocked += [f"Change {n}: {reason}" for reason in plan.blocked]
                continue
            if plan.target_key in targets:
                batch.blocked.append(f"Changes {targets[plan.target_key]} and {n} are for the same record. "
                                     "Put both into one change.")
                continue
            targets[plan.target_key] = n
            if plan.rule.kind in CREATED_ID:
                refs["{{%d.%s}}" % (n, CREATED_ID[plan.rule.kind])] = {
                    "kind": plan.rule.kind, "step": n, "name": _created_name(plan)}
            batch.steps.append(plan)
            batch.job_label = batch.job_label or plan.job_label
        if not batch.blocked and not batch.steps:
            batch.blocked.append(NOTHING_TO_CHANGE)
        return batch

    async def _plan(self, plan: Plan, body: Any, form: dict | None, files: dict | None) -> None:
        for rule in APPROVED:
            params = rule.match(plan.method, plan.path)
            if params is not None:
                plan.rule, plan.params = rule, params
                break
        else:
            raise GateError(
                f"{plan.method} {plan.path} is not one of the approved OnSite Companion changes. Claude can "
                "only make the contract-intake changes; anything else is done by a person in OnSite Companion.")
        rule = plan.rule
        for name, value in plan.params.items():
            new = plan.refs.get(value)
            if new and name == "PersonID" and rule.kind in {"link_client", "link_job"} \
                    and new["kind"] == "create_person":
                continue  # a person an earlier change in this batch creates
            if not GUID.fullmatch(value):
                raise GateError(f"{name} must be a single record ID (a GUID), not {value!r}.")
        if rule.kind in MESSAGE_KINDS:
            if body is not None:
                raise GateError("A message is sent as form fields and files, not a JSON body.")
            if not form or not str(form.get("Subject") or "").strip():
                raise GateError("A message needs a Subject.")
        else:
            if form or files:
                raise GateError("This change takes a JSON body, not form fields or files.")
            if not isinstance(body, dict) or not body:
                raise GateError("The change has no fields in it.")

        live = await self.live_check()
        if not live["live"]:
            raise GateError(live["reason"])

        job = None
        if rule.needs_job:
            if not GUID.fullmatch(plan.job_id):
                raise GateError("Say which job this change is for: job_id must be the job's ID (a GUID).")
            job = await self._job(plan.job_id)
        elif plan.job_id:
            if rule.kind == "create_job":
                raise GateError("A new job has no job ID yet, so leave job_id empty.")
            if not GUID.fullmatch(plan.job_id):
                raise GateError("job_id must be the job's ID (a GUID).")
            job = await self._job(plan.job_id)
        if job is not None:
            plan.job_label = job_label(job)
            plan.reads["job"] = _strip(job)

        await getattr(self, "_plan_" + rule.kind)(plan, job, body or {}, form or {}, files or {})

    def _same_id(self, a: Any, b: Any, message: str) -> None:
        if str(a or "").lower() != str(b or "").lower():
            raise GateError(message)

    async def _diff(self, plan: Plan, body: dict, current: dict | None, minimise: bool = True,
                    field_labels: dict[str, str] | None = None) -> dict:
        """Record every change against the current record and return the request body to send."""
        kind = plan.rule.kind
        allowed, protected = FIELDS[kind], PROTECTED.get(kind, {})
        safe: dict[str, Any] = {}
        for key, value in body.items():
            if key in protected:
                raise GateError(f"{label(key)} cannot be changed here: {protected[key]}.")
            if key not in allowed:
                raise GateError(f"OnSite Companion has no field called {key!r} on a {plan.rule.what}.")
            sub = allowed[key]
            if sub == CUSTOM:
                full = await self._custom(plan, value, (current or {}).get(CUSTOM), field_labels or {})
                if full is not None:
                    safe[key] = full if minimise else value
            elif isinstance(sub, frozenset):
                if not isinstance(value, dict):
                    raise GateError(f"{label(key)} must be a group of fields.")
                cur = (current or {}).get(key) or {}
                part = {}
                for k2, v2 in value.items():
                    if k2 not in sub:
                        raise GateError(f"OnSite Companion has no field called {k2!r} in {label(key)}.")
                    before = _current(cur, k2)
                    if not same(before, v2):
                        await self._add_change(plan, f"{key}.{k2}", before, v2, current is None)
                        part[k2] = v2
                if part or not minimise:
                    safe[key] = part if minimise else value
            else:
                before = _current(current, key)
                if not same(before, value):
                    await self._add_change(plan, key, before, value, current is None)
                    safe[key] = value
                elif not minimise:
                    safe[key] = value
        return safe

    async def _custom(self, plan: Plan, value: Any, current: Any, labels: dict[str, str]) -> list | None:
        """Custom fields: changes against current values; the full set is sent so none is dropped."""
        if not isinstance(value, list):
            raise GateError("Custom fields must be a list of {customFieldID, value}.")
        original = {}
        merged: dict[str, Any] = {}
        for item in current or []:
            fid = str(item.get("customFieldID")).lower()
            original[fid] = item.get("customFieldID")
            merged[fid] = item.get("value")
        seen, changed = set(), False
        for item in value:
            if not isinstance(item, dict) or set(item) - {"customFieldID", "value"}:
                raise GateError("Each custom field must be {customFieldID, value} and nothing else.")
            fid = str(item.get("customFieldID") or "").lower()
            if not GUID.fullmatch(fid):
                raise GateError("A custom field ID is not a GUID.")
            if fid in seen:
                raise GateError(f"Custom field {labels.get(fid, fid)} appears twice.")
            seen.add(fid)
            if fid not in labels:
                raise GateError("A custom field ID is not one of this OnSite Companion's fields.")
            new = item.get("value")
            if not same(merged.get(fid), new):
                changed = True
                plan.changes.append(self._change(f"{CUSTOM}.{fid}", labels[fid], merged.get(fid), new,
                                                 current is None))
                original.setdefault(fid, item.get("customFieldID"))
                merged[fid] = new
        if not changed:
            return None
        return [{"customFieldID": original[fid], "value": v} for fid, v in merged.items()]

    @staticmethod
    def _change(fld: str, name: str, current: Any, new: Any, creating: bool) -> dict[str, Any]:
        if creating:
            action = "new"
        elif current is None or current == "":
            action = "set"
        elif new is None or new == "":
            action = "clear"
        else:
            action = "change"
        return {"field": fld, "label": name, "current": current, "new": new, "action": action}

    async def _add_change(self, plan: Plan, fld: str, current: Any, new: Any, creating: bool) -> None:
        change = self._change(fld, label(fld), current, new, creating)
        leaf = fld.rsplit(".", 1)[-1]
        names = {"regionID": "regions", "workflowTemplateID": "templates",
                 "contactDetailsPrimaryCommunicationMethodID": "methods",
                 "preferredCommunicationGroupID": "groups", "completionAnswerStateID": "answers"}.get(leaf)
        if names:
            table = await self._lookup(names)
            for side in ("current", "new"):
                v = change[side]
                if v not in (None, "") and str(v).lower() in table:
                    change[f"{side}_shown"] = f'"{table[str(v).lower()]}"'
        plan.changes.append(change)

    async def _scope_client(self, plan: Plan, client_id: str, job: dict) -> None:
        rows = await self._find("/api/Jobs", f"clientID eq {client_id}", "client's jobs",
                                {"shouldShowMyJobsOnly": False})
        plan.reads["client_jobs"] = sorted(str(r.get("jobID")).lower() for r in rows)
        others = [r for r in rows if str(r.get("jobID")).lower() != plan.job_id.lower()]
        if others:
            names = ", ".join(str(r.get("contractNumber") or "no number") for r in others[:5])
            plan.notes.append(f"this client is also on {len(others)} other job(s) ({names}). "
                              "The change shows there too.")

    # ---- per change -----------------------------------------------------
    async def _plan_update_job(self, plan, job, body, form, files):
        self._same_id(plan.params["JobID"], plan.job_id, "The job in the request is not the job named for this change.")
        labels = await self._lookup("job_fields", required=CUSTOM in body)
        plan.before = job
        plan.request = {"json": await self._diff(plan, body, job, field_labels=labels)}
        plan.headline = "job details"

    async def _plan_update_client(self, plan, job, body, form, files):
        cid = plan.params["ClientID"]
        self._same_id(cid, job.get("clientID"), f"That client is not the client on job {plan.job_label}.")
        client = await self._one("/api/Clients", "clientID", cid, "client")
        plan.reads["client"] = _strip(client)
        await self._scope_client(plan, cid, job)
        plan.before = client
        plan.request = {"json": await self._diff(plan, body, client)}
        plan.headline = f"client details for {client.get('name') or 'this client'}"

    async def _plan_update_person(self, plan, job, body, form, files):
        pid = plan.params["PersonID"]
        on_client = await self._find("/api/Clients/Contacts",
                                     f"clientID eq {job.get('clientID')} and personID eq {pid}", "client contacts")
        on_job = await self._find("/api/Jobs/Contacts", f"jobID eq {plan.job_id} and personID eq {pid}",
                                  "job contacts")
        if not on_client and not on_job:
            raise GateError(f"That person is not a contact on job {plan.job_label} or its client.")
        person = await self._one("/api/Persons", "personID", pid, "person")
        plan.reads["person"] = _strip(person)
        clients = await self._find("/api/Clients/Contacts", f"personID eq {pid}", "person's clients")
        jobs = await self._find("/api/Jobs/Contacts", f"personID eq {pid}", "person's jobs")
        plan.reads["links"] = [len(clients), len(jobs)]
        if len(clients) + len(jobs) > 1:
            plan.notes.append(f"this person is a contact on {len(clients)} client(s) and {len(jobs)} job(s) in "
                              "OnSite Companion. The change shows on all of them.")
        labels = await self._lookup("person_fields", required=CUSTOM in body)
        plan.before = person
        plan.request = {"json": await self._diff(plan, body, person, field_labels=labels)}
        plan.headline = f"person details for {person.get('fullName') or 'this person'}"

    async def _link_parts(self, plan, job, client_side: bool):
        pid = plan.params["PersonID"]
        if client_side:
            self._same_id(plan.params["ClientID"], job.get("clientID"),
                          f"That client is not the client on job {plan.job_label}.")
        else:
            self._same_id(plan.params["JobID"], plan.job_id, "The job in the request is not the job named for this change.")
        new = plan.refs.get(pid)
        if new:  # created earlier in this batch: no record and no link exist yet
            plan.reads["link"] = []
            return {"fullName": new["name"]}, []
        if client_side:
            rows = await self._find("/api/Clients/Contacts",
                                    f"clientID eq {plan.params['ClientID']} and personID eq {pid}", "client contacts")
        else:
            rows = await self._find("/api/Jobs/Contacts", f"jobID eq {plan.job_id} and personID eq {pid}",
                                    "job contacts")
        person = await self._one("/api/Persons", "personID", pid, "person")
        plan.reads["link"] = _strip(rows)
        return person, rows

    @staticmethod
    def _existing_link(person: dict, rows: list[dict], body: dict, where: str) -> None:
        name = person.get("fullName") or "That person"
        if len(rows) == 1 and all(same(_current(rows[0], k), v) for k, v in body.items()):
            raise AlreadyDone(f"{name} is already a contact on {where}, set up as asked.")
        raise GateError(f"{name} is already a contact on {where}. Change the existing contact instead of "
                        "adding another.")

    async def _plan_link_client(self, plan, job, body, form, files):
        person, rows = await self._link_parts(plan, job, client_side=True)
        if rows:
            self._existing_link(person, rows, body, "this client")
        if not str(body.get("relationship") or "").strip():
            raise GateError("A client contact needs a relationship.")
        plan.request = {"json": await self._diff(plan, body, None, minimise=False)}
        plan.headline = f"{person.get('fullName') or 'a person'} is added as a contact on the job's client"

    async def _plan_update_client_link(self, plan, job, body, form, files):
        person, rows = await self._link_parts(plan, job, client_side=True)
        if len(rows) != 1:
            raise GateError("That person is not a contact on this client (or is listed twice), so the target is unclear.")
        plan.before = rows[0]
        plan.request = {"json": await self._diff(plan, body, rows[0])}
        plan.headline = f"client contact details for {person.get('fullName') or 'this person'}"

    async def _plan_link_job(self, plan, job, body, form, files):
        person, rows = await self._link_parts(plan, job, client_side=False)
        if rows:
            self._existing_link(person, rows, body, "this job")
        if not str(body.get("relationship") or "").strip():
            raise GateError("A job contact needs a relationship.")
        plan.request = {"json": await self._diff(plan, body, None, minimise=False)}
        plan.headline = f"{person.get('fullName') or 'a person'} is added as a contact on this job"

    async def _plan_update_job_link(self, plan, job, body, form, files):
        person, rows = await self._link_parts(plan, job, client_side=False)
        if len(rows) != 1:
            raise GateError("That person is not a contact on this job (or is listed twice), so the target is unclear.")
        plan.before = rows[0]
        plan.request = {"json": await self._diff(plan, body, rows[0])}
        plan.headline = f"job contact details for {person.get('fullName') or 'this person'}"

    async def _plan_create_client(self, plan, job, body, form, files):
        name = str(body.get("name") or "").strip()
        if not name:
            raise GateError("A new client needs a name.")
        for part in ("postalAddress", "workAddress", "workContactDetails"):
            if not isinstance(body.get(part), dict):
                raise GateError(f"{label(part)} must be given (an empty group is fine where nothing is sourced).")
        # Case-insensitive, and every word of the name in any order: OSC holds clients that differ
        # only by case, and "Given SURNAME & Given SURNAME" is typed in either order.
        rows = await self._find("/api/Clients", f"tolower(name) eq '{_q(name.lower())}'", "clients", top=50)
        exact = {str(r.get("clientID")).lower() for r in rows}
        words = [w for w in re.split(r"[\s,&]+", name.lower()) if len(w) > 1 and w not in NAME_FILLER][:4]
        similar = []
        if len(words) >= 2:
            flt = " and ".join(f"contains(tolower(name),'{_q(w)}')" for w in words)
            similar = [r for r in await self._find("/api/Clients", flt, "clients with a similar name", top=50)
                       if str(r.get("clientID")).lower() not in exact]
        plan.reads["same_name"] = sorted(exact)
        plan.reads["similar_name"] = sorted(str(r.get("clientID")).lower() for r in similar)
        if rows:
            plan.warnings.append(f"OnSite Companion already has {len(rows)} client(s) called \"{name}\". "
                                 "Use the existing client if it is the same buyer.")
        if similar:
            names = ", ".join(f"\"{r.get('name')}\"" for r in similar[:5])
            plan.warnings.append(f"OnSite Companion has {len(similar)} client(s) with a similar name ({names}). "
                                 "Use one of them if it is the same buyer.")
        plan.request = {"json": await self._diff(plan, body, None, minimise=False)}
        plan.headline = f"a new client \"{name}\" is created"

    async def _plan_create_person(self, plan, job, body, form, files):
        if not any(str(body.get(k) or "").strip() for k in ("honorific", "givenName", "middleNames", "surname")):
            raise GateError("A new person needs a name.")
        for part in ("personalAddress", "personalContactDetails", "postalAddress", "workAddress",
                     "workContactDetails"):
            if not isinstance(body.get(part), dict):
                raise GateError(f"{label(part)} must be given (an empty group is fine where nothing is sourced).")
        given, surname = str(body.get("givenName") or "").strip(), str(body.get("surname") or "").strip()
        rows = await self._find("/api/Persons", f"tolower(givenName) eq '{_q(given.lower())}' and "
                                                f"tolower(surname) eq '{_q(surname.lower())}'", "people", top=50)
        plan.reads["same_name"] = sorted(str(r.get("personID")).lower() for r in rows)
        whole = " ".join(x for x in (given, surname) if x)
        if rows:
            plan.warnings.append(f"OnSite Companion already has {len(rows)} person(s) called \"{whole}\". "
                                 "Use the existing person if it is the same one.")
        # The same email or mobile is a stronger sign of the same person than the name.
        contact = body.get("personalContactDetails") if isinstance(body.get("personalContactDetails"), dict) else {}
        email = str(contact.get("email") or "").strip().lower()
        digits = re.sub(r"\D", "", str(contact.get("mobile") or ""))
        checks = []
        if email:
            checks.append(("email", f"tolower(personalContactDetails/email) eq '{_q(email)}'"))
        if len(digits) >= 8:
            forms = {digits, f"{digits[:4]} {digits[4:7]} {digits[7:]}" if len(digits) == 10 else digits,
                     str(contact.get("mobile")).strip()}
            checks.append(("mobile", " or ".join(f"personalContactDetails/mobile eq '{_q(f)}'"
                                                 for f in sorted(forms))))
        for what, flt in checks:
            found = [r for r in await self._find("/api/Persons", flt, f"people with the same {what}", top=20)
                     if str(r.get("personID")).lower() not in plan.reads["same_name"]]
            plan.reads[f"same_{what}"] = sorted(str(r.get("personID")).lower() for r in found)
            if found:
                names = ", ".join(f"\"{r.get('fullName') or 'no name'}\"" for r in found[:5])
                plan.warnings.append(f"OnSite Companion already has {len(found)} person(s) with this {what} "
                                     f"({names}). Use the existing person if it is the same one.")
        labels = await self._lookup("person_fields", required=CUSTOM in body)
        plan.request = {"json": await self._diff(plan, body, None, minimise=False, field_labels=labels)}
        plan.headline = f"a new person \"{whole}\" is created"

    async def _plan_create_job(self, plan, job, body, form, files):
        new_client = plan.refs.get(str(body.get("clientID") or ""))
        if new_client and new_client["kind"] != "create_client":
            raise GateError(f"{body['clientID']} is not a client that an earlier change in this batch creates.")
        for key in ("clientID", "regionID"):
            if not (key == "clientID" and new_client) and not GUID.fullmatch(str(body.get(key) or "")):
                raise GateError(f"A new job needs {label(key).lower()} as an ID.")
        if not isinstance(body.get("siteAddress"), dict):
            raise GateError("A new job needs a site address.")
        client = ({"name": new_client["name"]} if new_client
                  else await self._one("/api/Clients", "clientID", body["clientID"], "client"))
        regions = await self._lookup("regions", required=True)
        if str(body["regionID"]).lower() not in regions:
            raise GateError("That region is not one of OnSite Companion's regions.")
        if body.get("workflowTemplateID"):
            templates = await self._lookup("templates", required=True)
            if str(body["workflowTemplateID"]).lower() not in templates:
                raise GateError("That workflow template is not one of OnSite Companion's templates.")
        site = body["siteAddress"]
        lot = str(site.get("lotNumber") or "").strip()
        if lot:
            # Every job on the lot number, cancelled ones included. Lot numbers repeat across estates
            # (one is on 28 production jobs, 15 Oct 2026), so a short page could hide the real twin.
            rows = await self._find("/api/Jobs", f"siteAddress/lotNumber eq '{_q(lot)}'", "jobs on the same lot",
                                    {"shouldShowMyJobsOnly": False}, top=LOT_PAGE)
            if len(rows) >= LOT_PAGE:
                raise GateError(f"More than {LOT_PAGE - 1} jobs use lot {lot}, so they could not all be checked "
                                "for a duplicate. A person creates this job in OnSite Companion.")
            plan.reads["same_lot"] = sorted(str(r.get("jobID")).lower() for r in rows)
            suburb = str(site.get("suburb") or "").strip().upper()
            here = [r for r in rows if not suburb
                    or str((r.get("siteAddress") or {}).get("suburb") or "").strip().upper() == suburb]
            here.sort(key=lambda r: ("cancel" in str(r.get("workflowStatusName") or "").lower(),
                                     str(r.get("contractNumber") or "")))
            where = f"lot {lot} in {suburb}" if suburb else f"lot {lot}"
            for r in here[:10]:
                plan.warnings.append(f"OnSite Companion already has job {job_label(r)} "
                                     f"({r.get('workflowStatusName') or 'status unknown'}) on {where}. "
                                     "Make sure it is not this job.")
            if len(here) > 10:
                plan.warnings.append(f"... and {len(here) - 10} more job(s) on {where}.")
            if len(rows) > len(here):
                plan.notes.append(f"lot {lot} is also used by {len(rows) - len(here)} job(s) in other suburbs. "
                                  "None of them is at this site.")
        else:
            plan.warnings.append("No lot number is given, so OnSite Companion could not be checked for a job "
                                 "on the same lot.")
        labels = await self._lookup("job_fields", required=CUSTOM in body)
        plan.request = {"json": await self._diff(plan, body, None, minimise=False, field_labels=labels)}
        for c in plan.changes:
            if c["field"] == "clientID":
                c["new_shown"] = f"\"{client.get('name')}\""
        plan.changes.append({"field": "contractNumber", "label": "Contract number", "current": None,
                             "new": None, "new_shown": "generated by OnSite Companion", "action": "new"})
        plan.job_label = f"new job at {job_label({'siteAddress': site}).lstrip(' -')}"
        plan.headline = f"a new job is created for client \"{client.get('name')}\""

    async def _activity_for_job(self, plan) -> dict:
        activity = await self._activity(plan.params["JobActivityID"])
        self._same_id(activity.get("jobID"), plan.job_id,
                      f"That activity belongs to a different job, not {plan.job_label}.")
        # Sequence numbers differ between workflow templates (on three production jobs, 15 Oct 2026,
        # activity 2 is "m) Fixout Complete - OK to Claim"), so the activity is checked by its name.
        if _activity_name(activity.get("description")) not in INTAKE_ACTIVITIES:
            raise GateError(f"Activity {activity.get('sequence')} \"{activity.get('description')}\" is not one of "
                            "the intake activities (Initial Contact, Follow Up Initial Contact, Create Job within "
                            "Databuild, Receive EOI Approval to Proceed from Marketer). A person handles it in "
                            "OnSite Companion.")
        plan.reads["activity"] = _strip(activity)
        return activity

    async def _plan_complete_activity(self, plan, job, body, form, files):
        activity = await self._activity_for_job(plan)
        name = f"activity {activity.get('sequence')} \"{activity.get('description')}\""
        if not isinstance(body.get("completionDate"), str) or not _parse_dt(body["completionDate"]):
            raise GateError("A completion date (YYYY-MM-DD) is needed.")
        if activity.get("completionDate"):
            raise AlreadyDone(f"{name[0].upper() + name[1:]} is already complete "
                              f"({fmt_date(activity['completionDate'])}), so there is nothing to change.")
        if activity.get("isNotApplicable"):
            raise GateError(f"{name[0].upper() + name[1:]} is marked not applicable. A person decides that one.")
        # A completion is one action, checked by its date on read-back; OSC may
        # fill other activity fields when it completes one, so no whole-record compare.
        plan.request = {"json": await self._diff(plan, body, {"completionDate": None})}
        plan.headline = f"{name} is marked complete"
        if _activity_name(activity.get("description")) == DATABUILD_ACTIVITY:
            plan.warnings.append("say yes only if the job has been entered in DataBuild.")

    async def _plan_answer_question(self, plan, job, body, form, files):
        activity = await self._activity_for_job(plan)
        qid = plan.params["CompletionQuestionID"].lower()
        questions = self._rows(await self._get(f"/api/JobActivities/{plan.params['JobActivityID']}/Questions",
                                               None, None, "activity questions"))
        match = [q for q in questions if str(q.get("completionQuestionID")).lower() == qid]
        if len(match) != 1:
            raise GateError("That question is not on this activity, so the target is unclear.")
        answer = match[0].get("answer") or {}
        current = {"completionAnswerStateID": answer.get("answerStateID"), "note": answer.get("note")}
        plan.reads["question"] = _strip(match[0])
        plan.before = current
        changed = await self._diff(plan, body, current)
        # PUT replaces the whole answer: carry the current value of anything not being changed.
        plan.request = {"json": {**{k: v for k, v in current.items() if v is not None}, **changed}}
        if plan.request["json"].get("completionAnswerStateID") in (None, ""):
            raise GateError("An answer needs its answer state (completionAnswerStateID).")
        plan.headline = (f"activity {activity.get('sequence')} \"{activity.get('description')}\", "
                         f"question \"{match[0].get('questionText')}\"")

    async def _plan_message(self, plan, form, files, list_path: str):
        bad = [k for k in form if not FORM_KEY.match(k)] + [k for k in files if not FILE_KEY.match(k)]
        if bad:
            raise GateError(f"Unknown message field(s): {', '.join(bad)}.")
        plan.checks = check_uploads(files, self.config.upload_roots)
        problems = [f"{c['path']}: {c['problem']}" for c in plan.checks if not c["ok"]]
        if problems:
            raise GateError("The attachment cannot be used: " + "; ".join(problems) + ".")
        rows = self._rows(await self._get(list_path, {"$orderby": "createdOnUtc desc", "$top": 50}, None,
                                          "existing messages"))
        subject = str(form["Subject"]).strip()
        same_subject = [r for r in rows if str(r.get("subject") or "").strip().lower() == subject.lower()]
        plan.reads["same_subject"] = sorted(str(r.get("messageID")).lower() for r in same_subject)
        if same_subject:
            when = fmt_date(same_subject[0].get("createdOnUtc"))
            plan.warnings.append(f"there is already a message called \"{subject}\" here (added {when}). "
                                 "Sending adds another one.")
        plan.reads["files"] = [[c["path"], c["bytes"], c["modified"]] for c in plan.checks]
        for key, value in form.items():
            plan.changes.append({"field": key, "label": "Subject" if key == "Subject" else
                                 ("Text" if key == "Body" else "Attachment description"),
                                 "current": None, "new": value, "action": "new"})
        for c in plan.checks:
            plan.changes.append({"field": c["field"], "label": "Attachment", "current": None, "new": c["path"],
                                 "new_shown": f"{Path(c['path']).name} ({max(1, round(c['bytes'] / 1024))} KB)",
                                 "action": "new"})
        plan.request = {"form": dict(form), "files": dict(files)}

    async def _plan_job_message(self, plan, job, body, form, files):
        self._same_id(plan.params["JobID"], plan.job_id, "The job in the request is not the job named for this change.")
        await self._plan_message(plan, form, files, f"/api/Jobs/{plan.params['JobID']}/Messages")
        plan.headline = "a message is added to the job"

    async def _plan_activity_message(self, plan, job, body, form, files):
        activity = await self._activity_for_job(plan)
        await self._plan_message(plan, form, files,
                                 f"/api/JobActivities/{plan.params['JobActivityID']}/Messages")
        plan.headline = (f"a message is added to activity {activity.get('sequence')} "
                         f"\"{activity.get('description')}\"")

    # ---- confirmations --------------------------------------------------
    def register(self, plan: Plan) -> str:
        """Hold a sendable plan under a new code; a newer check of the same target replaces the older one."""
        self._expire()
        for code, pending in list(self.pending.items()):
            if pending.plan.target_key == plan.target_key:
                del self.pending[code]
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        self.pending[code] = Pending(code, plan, time.monotonic())
        return code

    def _expire(self) -> None:
        limit = self.config.approval_minutes * 60
        for code, pending in list(self.pending.items()):
            if time.monotonic() - pending.created > limit:
                del self.pending[code]

    def cancel(self, code: str) -> bool:
        return self.pending.pop((code or "").strip().upper(), None) is not None

    async def confirm(self, code: str, user_reply: str) -> dict[str, Any]:
        code = (code or "").strip().upper()
        self._expire()
        pending = self.pending.get(code)
        if pending is None:
            return {"ok": False, "sent": False, "result_text":
                    "Nothing was sent. That confirmation code is not valid any more: it was already used, "
                    "replaced by a newer check of the same change, expired, or came from another chat. "
                    "Prepare the change again and show the new confirmation."}
        kind = reply_kind(user_reply, code)
        if kind != "yes":
            del self.pending[code]
            if kind == "no":
                return {"ok": True, "sent": False, "cancelled": True,
                        "result_text": "Cancelled. Nothing was changed in OnSite Companion."}
            return {"ok": False, "sent": False, "result_text":
                    "Nothing was sent: the reply was not a plain yes. If the person asked for something "
                    "different, prepare that change and show its confirmation."}
        if not self.config.enable_writes:
            return {"ok": False, "sent": False, "result_text":
                    "Nothing was sent: writing to OnSite Companion is switched off for this chat."}
        del self.pending[code]  # single use, before anything is sent
        if isinstance(pending.plan, Batch):
            return await self._confirm_batch(pending.plan)
        fresh = await self.build_plan(**pending.plan.inputs)
        if fresh.blocked:
            return {"ok": False, "sent": False, "result_text": render(fresh, self.config.environment)}
        if fresh.fingerprint != pending.plan.fingerprint:
            new_code = self.register(fresh)
            return {"ok": False, "sent": False, "changed": True, "confirmation_code": new_code,
                    "confirmation_text": render(fresh, self.config.environment),
                    "result_text": "Nothing was sent: OnSite Companion changed after this was confirmed, or "
                                   "the change itself is different now. Show the person the new confirmation "
                                   "and ask again."}
        return await self._send(pending.plan)

    async def _confirm_batch(self, approved: Batch) -> dict[str, Any]:
        env = self.config.environment
        fresh = await self.build_batch(approved.job_id, approved.changes)
        if fresh.blocked:
            return {"ok": False, "sent": False, "result_text": render_batch(fresh, env)}
        if fresh.fingerprint != approved.fingerprint:
            new_code = self.register(fresh)
            return {"ok": False, "sent": False, "changed": True, "confirmation_code": new_code,
                    "confirmation_text": render_batch(fresh, env),
                    "result_text": "Nothing was sent: OnSite Companion changed after this was confirmed, or the "
                                   "changes themselves are different now. Show the person the new confirmation "
                                   "and ask again."}
        where = f" on job {fresh.job_label}" if fresh.job_label and fresh.job_id else ""
        total, ids, done = len(fresh.steps), {}, []
        for i, step in enumerate(fresh.steps, 1):
            plan = step
            if i > 1:
                # Planned again just before it goes: an earlier change, or someone in OSC, may have moved it.
                inputs = json.loads(_swap(json.dumps(step.inputs, default=str), ids))
                plan = await self.build_plan(**inputs)
                if plan.blocked or plan.signature() != step.signature(ids):
                    return await self._batch_stopped(approved, step, ids, done, total, plan)
            res = await self._send(plan)
            entry = {"change": i, "what": _describe(plan), "state": res.get("state", "failed"),
                     "result_text": res.get("result_text")}
            if res.get("verification", {}).get("contract_number"):
                entry["contract_number"] = res["verification"]["contract_number"]
            key = CREATED_ID.get(plan.rule.kind)
            if res.get("ok") and key:
                new_id = (res.get("data") or {}).get(key) if isinstance(res.get("data"), dict) else None
                ids["{{%d.%s}}" % (step.step, key)] = str(new_id)
                entry[key] = new_id
            done.append(entry)
            if not res.get("ok"):
                return {"ok": False, "sent": bool(res.get("sent")) or i > 1, "state": entry["state"],
                        "changes": done, "created": ids,
                        "result_text": (f"{i - 1} of {total} change(s) made and read back{where}. Change {i} "
                                        f"({entry['what']}): {res.get('result_text')} The other {total - i} "
                                        "change(s) were not sent.")}
        text = f"Done{where}: all {total} change(s) made and read back from OnSite Companion."
        numbers = [d["contract_number"] for d in done if d.get("contract_number")]
        if numbers:
            text += f" Contract number: {numbers[0]}."
        return {"ok": True, "sent": True, "state": "verified", "changes": done, "created": ids, "result_text": text}

    async def _batch_stopped(self, approved: Batch, step: Plan, ids: dict[str, str], done: list[dict],
                             total: int, plan: Plan) -> dict[str, Any]:
        """A later change no longer matches what was approved: stop, and ask again for the rest."""
        first = step.step
        rest = [json.loads(_renumber(_swap(json.dumps(c, default=str), ids), first - 1))
                for c in approved.changes[first - 1:]]
        again = await self.build_batch(approved.job_id, rest)
        out: dict[str, Any] = {
            "ok": False, "sent": bool(done), "state": "stopped", "changes": done, "created": ids,
            "confirmation_text": render_batch(again, self.config.environment),
            "result_text": (f"{len(done)} of {total} change(s) made and read back. The next change "
                            f"({_describe(step)}) no longer matches what was confirmed"
                            + (f" ({plan.blocked[0]})" if plan.blocked else "")
                            + ", so nothing more was sent. Show the person the new confirmation for the rest.")}
        if not again.blocked:
            out["confirmation_code"] = self.register(again)
        return out

    async def _send(self, plan: Plan) -> dict[str, Any]:
        req = plan.request
        try:
            if "json" in req:
                res = await self.client.request(plan.method, plan.path, json_body=req["json"])
            else:
                with ExitStack() as stack:
                    uploads = {k: (Path(v).name, stack.enter_context(Path(v).open("rb")),
                                   mimetypes.guess_type(Path(v).name)[0] or "application/octet-stream")
                               for k, v in req["files"].items()}
                    res = await self.client.request(plan.method, plan.path, form_data=req["form"], files=uploads)
        except OSCError as exc:
            return {"ok": False, "sent": False, "state": "failed",
                    "result_text": f"OnSite Companion could not be reached to make the change ({exc}). Nothing "
                                   "was changed."}
        except OSError:
            return {"ok": False, "sent": False, "state": "failed",
                    "result_text": "The attachment could not be read, so nothing was sent."}
        except httpx.HTTPError:
            return {"ok": False, "sent": True, "state": "sent_unverified",
                    "result_text": "The connection dropped while sending, so it is not known whether the change "
                                   "was made. Read the record in OnSite Companion before trying again."}
        if not res.get("ok"):
            detail = res.get("data") or res.get("text") or ""
            return {"ok": False, "sent": True, "state": "failed", "status": res.get("status"), "data": res.get("data"),
                    "result_text": f"OnSite Companion refused the change (HTTP {res.get('status')}). Nothing "
                                   f"was changed. {str(detail)[:300]}".strip()}
        verification = await self._verify(plan, res.get("data"))
        return {"ok": verification["verified"], "sent": True, "status": res.get("status"), "data": res.get("data"),
                "state": "verified" if verification["verified"] else "sent_unverified",
                "verification": verification, "result_text": verification["text"]}

    # ---- read-back ------------------------------------------------------
    async def _verify(self, plan: Plan, data: Any) -> dict[str, Any]:
        kind = plan.rule.kind
        where = f" on job {plan.job_label}" if plan.job_label and kind != "create_job" else ""
        try:
            if kind in MESSAGE_KINDS:
                return await self._verify_message(plan, data, where)
            after = await self._read_back(plan, data)
        except GateError as exc:
            return {"verified": False, "text": f"The change was sent{where}, but reading it back failed: {exc} "
                                               "Check it in OnSite Companion."}
        if after is None:
            return {"verified": False, "text": f"The change was sent{where}, but OnSite Companion did not return "
                                               "the new record, so it could not be read back. Check it in "
                                               "OnSite Companion."}
        applied, missing, unchecked = [], [], []
        custom_after = _flatten({CUSTOM: after.get(CUSTOM) or []})
        for c in plan.changes:
            if c["field"] == "contractNumber" and kind == "create_job":
                continue
            if c["field"].startswith(CUSTOM + "."):
                present, now = c["field"] in custom_after, custom_after.get(c["field"])
            else:
                head, _, tail = c["field"].partition(".")
                container, leaf = (after.get(head), tail) if tail else (after, head)
                present = isinstance(container, dict) and (
                    leaf in container or (leaf in ALIASES and ALIASES[leaf][0] in container))
                now = _current(container, leaf)
            if not present:
                unchecked.append(c["label"])  # OSC's read view does not show this field
            else:
                (applied if same(now, c["new"]) else missing).append(c["label"])
        unexpected = []
        if plan.before is not None:
            touched = {c["field"] for c in plan.changes}
            skip = set(touched)
            for t in touched:
                head, _, tail = t.partition(".")
                leaf = tail or head
                if leaf in ALIASES:
                    skip.add((head + "." if tail else "") + ALIASES[leaf][0])
                for d in DERIVED.get(leaf, ()):
                    skip.add(d)
            b, a = _flatten(_strip(plan.before)), _flatten(_strip(after))
            for key in sorted(set(b) | set(a)):
                if any(key == s or key.startswith(s + ".") for s in skip):
                    continue
                if not same(b.get(key), a.get(key)):
                    unexpected.append(key)
        result: dict[str, Any] = {"verified": not missing and not unexpected, "applied": applied,
                                  "not_applied": missing, "not_checked": unchecked,
                                  "unexpected_changes": unexpected}
        if kind == "create_job":
            number = after.get("contractNumber")
            result["contract_number"] = number
            if not number:
                result["verified"] = False
                missing.append("contract number")
        if result["verified"]:
            extra = " and nothing else on it changed" if plan.before is not None else ""
            what = f" Contract number: {after.get('contractNumber')}." if kind == "create_job" else ""
            result["text"] = (f"Done{where}. I read it back from OnSite Companion: {len(applied)} change(s) in "
                              f"place{extra}.{what}")
            if unchecked:
                result["text"] += (" OnSite Companion's read view does not show " + ", ".join(unchecked)
                                   + ", so that part could not be checked.")
        else:
            parts = []
            if missing:
                parts.append("these did not take: " + ", ".join(missing))
            if unexpected:
                parts.append("these other fields also changed: " + ", ".join(label(k) for k in unexpected[:8]))
            result["text"] = (f"The change was sent{where}, but the read-back found a problem ("
                              + "; ".join(parts) + "). Check it in OnSite Companion before going on.")
        return result

    async def _read_back(self, plan: Plan, data: Any) -> dict | None:
        kind, p = plan.rule.kind, plan.params
        if kind == "update_job":
            return await self._job(plan.job_id)
        if kind == "update_client":
            return await self._one("/api/Clients", "clientID", p["ClientID"], "client")
        if kind == "update_person":
            return await self._one("/api/Persons", "personID", p["PersonID"], "person")
        if kind in {"link_client", "update_client_link"}:
            rows = await self._find("/api/Clients/Contacts", f"clientID eq {p['ClientID']} and personID eq "
                                    f"{p['PersonID']}", "client contact")
            return rows[0] if len(rows) == 1 else None
        if kind in {"link_job", "update_job_link"}:
            rows = await self._find("/api/Jobs/Contacts", f"jobID eq {p['JobID']} and personID eq {p['PersonID']}",
                                    "job contact")
            return rows[0] if len(rows) == 1 else None
        if kind == "complete_activity":
            return await self._activity(p["JobActivityID"])
        if kind == "answer_question":
            questions = self._rows(await self._get(f"/api/JobActivities/{p['JobActivityID']}/Questions", None,
                                                   None, "activity questions"))
            for q in questions:
                if str(q.get("completionQuestionID")).lower() == p["CompletionQuestionID"].lower():
                    answer = q.get("answer") or {}
                    return {"completionAnswerStateID": answer.get("answerStateID"), "note": answer.get("note")}
            return None
        ids = {"create_client": ("clientID", "/api/Clients", "client"),
               "create_person": ("personID", "/api/Persons", "person"),
               "create_job": ("jobID", "/api/Jobs", "job")}
        key, path, what = ids[kind]
        new_id = data.get(key) if isinstance(data, dict) else None
        if not GUID.fullmatch(str(new_id or "")):
            return None
        body = {"shouldShowMyJobsOnly": False} if kind == "create_job" else None
        return await self._one(path, key, new_id, what, body)

    async def _verify_message(self, plan: Plan, data: Any, where: str) -> dict[str, Any]:
        """Read the message back from OSC itself: listed where it was posted, with its attachments.

        Production lists messages without their documents, so the attachments are read from
        /api/Messages/Documents by message ID (checked 15 Oct 2026)."""
        message_id = str(data.get("messageID") or "") if isinstance(data, dict) else ""
        expected = len(plan.request.get("files") or {})
        if not GUID.fullmatch(message_id):
            return {"verified": False, "message_id": None, "attachments": 0,
                    "text": f"The message was sent{where}, but OnSite Companion did not return its ID, so it could "
                            "not be read back. Check it in OnSite Companion before sending it again."}
        rows = self._rows(await self._get(plan.path, {"$orderby": "createdOnUtc desc", "$top": 50}, None,
                                          "messages"))
        listed = [r for r in rows if str(r.get("messageID")).lower() == message_id.lower()]
        subject = str(plan.request.get("form", {}).get("Subject") or "").strip()
        documents = self._rows(await self._get("/api/Messages/Documents", {"$filter": f"messageID eq {message_id}"},
                                               None, "message attachments")) if expected else []
        problems = []
        if not listed:
            problems.append("the message is not listed")
        elif str(listed[0].get("subject") or "").strip() != subject:
            problems.append(f"its subject reads \"{listed[0].get('subject')}\"")
        if len(documents) < expected:
            problems.append(f"{len(documents)} of {expected} attachment(s) are there")
        ok = not problems
        text = (f"Done{where}. I read it back from OnSite Companion: the message \"{subject}\" is there with "
                f"{len(documents)} attachment(s)." if ok else
                f"The message was sent{where}, but the read-back found a problem ({'; '.join(problems)}). "
                "Check it in OnSite Companion before sending it again.")
        return {"verified": ok, "message_id": message_id, "attachments": len(documents), "text": text}


def _swap(text: str, ids: dict[str, str]) -> str:
    for placeholder, real in ids.items():
        text = text.replace(placeholder, real)
    return text


def _renumber(text: str, offset: int) -> str:
    """Placeholders of a batch's remaining changes, numbered from 1 again."""
    return REF.sub(lambda m: "{{%d.%s}}" % (int(m.group(1)) - offset, m.group(2)), text)


def job_label(job: dict) -> str:
    """26999 - LOT 12 SAMPLE STREET, TESTVILLE NSW 2000 (the house style for naming a job)."""
    a = job.get("siteAddress") or {}
    street = " ".join(x for x in (f"LOT {a['lotNumber']}" if a.get("lotNumber") else "", a.get("line1") or "") if x)
    place = " ".join(str(x) for x in (a.get("suburb"), a.get("state"), a.get("postcode")) if x)
    address = ", ".join(x for x in (street, a.get("line2"), place) if x).upper()
    number = job.get("contractNumber") or ""
    return f"{number} - {address}" if number and address else (number or address or "job with no address")
