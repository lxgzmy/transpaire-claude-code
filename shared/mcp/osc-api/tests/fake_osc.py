"""A small stateful stand-in for the OnSite Companion API. Synthetic data only.

PATCH behaves as the 8 Oct 2026 dev evidence showed: fields left out are kept,
null clears, nested groups merge field by field. A custom-field collection is
REPLACED as a whole (the OData rule, and the worst case for losing data), so a
request that sends only one custom field would wipe the rest.

Used two ways: as an httpx MockTransport (unit tests) and behind a local HTTP
server (the stdio end-to-end test).
"""
from __future__ import annotations

import copy
import itertools
import json
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

import httpx

GROUP_FIELDS = {"contactDetailsPrimaryCommunicationMethodID": ("primaryCommunicationMethod", "methods"),
                "preferredCommunicationGroupID": ("preferredCommunicationGroup", "groups")}


def _id() -> str:
    return str(uuid.uuid4())


def _now(days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeOSC:
    def __init__(self, newest_job_days_ago: int = 1):
        self.writes: list[dict] = []      # every write that reached the API
        self.patch_hook = None            # optional f(kind, record) run after a PATCH (to simulate faults)
        self.numbers = itertools.count(26100)
        self.region_nsw, self.region_qld = _id(), _id()
        self.regions = [{"regionID": self.region_nsw, "description": "SYDNEY01", "isActive": True},
                        {"regionID": self.region_qld, "description": "SEQ01", "isActive": True}]
        self.template = _id()
        self.templates = [{"workflowTemplateID": self.template, "name": "1.1 - Pre Sales Investor v1"}]
        self.f_sp, self.f_design, self.f_facade = _id(), _id(), _id()
        self.job_fields = [{"customFieldID": self.f_sp, "label": "SP No.", "valueType": "Text"},
                           {"customFieldID": self.f_design, "label": "Design", "valueType": "Text"},
                           {"customFieldID": self.f_facade, "label": "Facade", "valueType": "Text"}]
        self.person_fields: list[dict] = []
        self.methods = [{"contactDetailsPrimaryCommunicationMethodID": 1, "description": "Phone"},
                        {"contactDetailsPrimaryCommunicationMethodID": 2, "description": "Email"}]
        self.groups = [{"preferredCommunicationGroupID": 1, "description": "All"},
                       {"preferredCommunicationGroupID": 2, "description": "None"}]
        self.answers = [{"completionAnswerStateID": 1, "description": "Completed"},
                        {"completionAnswerStateID": 2, "description": "Not Applicable"}]
        self.clients: dict[str, dict] = {}
        self.persons: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.client_contacts: list[dict] = []
        self.job_contacts: list[dict] = []
        self.activities: dict[str, dict] = {}
        self.questions: dict[str, list[dict]] = {}
        self.messages: dict[str, list[dict]] = {}
        self._seed(newest_job_days_ago)

    # ---- synthetic records ----------------------------------------------
    def _seed(self, days_ago: int) -> None:
        self.client_id = self.add_client("SYNTHETIC, Alex", line1="1 TEST STREET", suburb="TESTVILLE")
        self.other_client_id = self.add_client("OTHER, Sam", line1="9 ELSEWHERE ROAD", suburb="OTHERTON")
        self.job_id = self.add_job(self.client_id, "26999", lot="12", line1="SAMPLE STREET", suburb="TESTVILLE",
                                   postcode="2000", days_ago=days_ago + 30,
                                   custom={self.f_sp: "", self.f_design: "Hampton 22", self.f_facade: "Coastal"})
        self.other_job_id = self.add_job(self.other_client_id, "26033", lot="12", line1="SAMPLE AVENUE",
                                         suburb="OTHERTON", postcode="2000", days_ago=days_ago)
        self.person_id = self.add_person("Alex", "SYNTHETIC", email="alex@example.invalid")
        self.other_person_id = self.add_person("Sam", "OTHER")
        self.client_contacts.append({"clientID": self.client_id, "personID": self.person_id,
                                     "fullName": "Alex SYNTHETIC", "isPrimaryContact": True,
                                     "isSecondaryContact": False, "relationship": "PURCHASER",
                                     "_group": 1})
        self.client_contacts.append({"clientID": self.other_client_id, "personID": self.other_person_id,
                                     "fullName": "Sam OTHER", "isPrimaryContact": True,
                                     "isSecondaryContact": False, "relationship": "PURCHASER", "_group": 1})
        self.act1 = self.add_activity(self.job_id, 1, "Initial Contact")
        self.act2 = self.add_activity(self.job_id, 2, "Follow Up Initial Contact", done="2026-04-17T00:00:00Z")
        self.act6 = self.add_activity(self.job_id, 6, "Create Job within Databuild")
        self.q1, self.q2 = _id(), _id()
        self.questions[self.act6] = [
            {"completionQuestionID": self.q1, "questionText": "Create Job within Databuild", "sequence": 1,
             "answer": None},
            {"completionQuestionID": self.q2, "questionText": "Create Job File within Z:\\ Drive", "sequence": 2,
             "answer": {"answerStateID": None, "note": "folder made by hand", "answerState": None}}]
        self.other_act = self.add_activity(self.other_job_id, 1, "Initial Contact")

    def add_client(self, name, line1="", suburb="") -> str:
        cid = _id()
        self.clients[cid] = {"clientID": cid, "name": name, "abn": None, "entityCode": None, "workUrl": None,
                             "salespersonID": None, "createdOnUtc": _now(40),
                             "postalAddress": {"line1": line1, "line2": None, "suburb": suburb, "state": "NSW",
                                               "postcode": "2000", "country": None, "poBoxNumber": None,
                                               "propertyName": None},
                             "workAddress": {"line1": None, "line2": None, "suburb": None, "state": None,
                                             "postcode": None, "country": None, "poBoxNumber": None,
                                             "propertyName": None},
                             "workContactDetails": {"email": None, "mobile": None, "phone": None, "fax": None,
                                                    "direct": None, "primaryCommunicationMethod":
                                                        {"contactDetailsPrimaryCommunicationMethodID": 0,
                                                         "description": None}}}
        return cid

    def add_person(self, given, surname, email=None) -> str:
        pid = _id()
        empty = {"line1": None, "line2": None, "suburb": None, "state": None, "postcode": None,
                 "country": None, "poBoxNumber": None, "propertyName": None}
        self.persons[pid] = {"personID": pid, "givenName": given, "surname": surname, "middleNames": None,
                             "honorific": None, "fullName": f"{given} {surname}", "dateOfBirth": None,
                             "companyName": None, "jobDescription": None, "workUrl": None,
                             "salespersonID": None, "customFieldValues": [],
                             "personalAddress": dict(empty), "postalAddress": dict(empty),
                             "workAddress": dict(empty),
                             "personalContactDetails": {"email": email, "mobile": "0400 000 000", "phone": None,
                                                        "fax": None, "primaryCommunicationMethod":
                                                            {"contactDetailsPrimaryCommunicationMethodID": 2,
                                                             "description": "Email"}},
                             "workContactDetails": {"email": None, "mobile": None, "phone": None, "fax": None,
                                                    "direct": None, "primaryCommunicationMethod":
                                                        {"contactDetailsPrimaryCommunicationMethodID": 0,
                                                         "description": None}}}
        return pid

    def add_job(self, client_id, number, lot, line1, suburb, postcode, days_ago=1, custom=None) -> str:
        jid = _id()
        self.jobs[jid] = {"jobID": jid, "clientID": client_id, "clientName": self.clients[client_id]["name"],
                          "contractNumber": number, "createdOnUtc": _now(days_ago),
                          "contractValueIncludingGst": 450000.0, "contractValueExcludingGst": 409090.91,
                          "region": "SYDNEY01", "startDate": "2026-04-17T00:00:00Z",
                          "workflowStatusName": "1. Pre Sales",
                          "siteAddress": {"lotNumber": lot, "line1": line1, "line2": None, "suburb": suburb,
                                          "state": "NSW", "postcode": postcode, "country": None,
                                          "blockNumber": None, "dpLotNumber": None, "mapFriendlyAddress": None,
                                          "propertyName": None, "sectionNumber": None},
                          "customFieldValues": [{"customFieldID": k, "value": v}
                                                for k, v in (custom or {}).items()]}
        return jid

    def add_activity(self, job_id, seq, description, done=None) -> str:
        aid = _id()
        self.activities[aid] = {"jobActivityID": aid, "jobID": job_id, "sequence": seq,
                                "description": description, "completionDate": done, "isNotApplicable": False,
                                "forecastedStartDate": _now(), "hasCompletionQuestions": False}
        return aid

    def add_message(self, owner_path: str, subject: str, days_ago: int = 3) -> None:
        self.messages.setdefault(owner_path.lower(), []).append(
            {"messageID": _id(), "subject": subject, "body": "", "createdOnUtc": _now(days_ago)})

    # ---- request handling -----------------------------------------------
    def handle(self, method: str, path: str, params: dict, body, form=None, files=None):
        method = method.upper()
        parts = [p for p in path.split("/") if p]
        if path == "/api/Token":
            return 200, {"accessToken": "synthetic", "expiresIn": 3600, "tokenType": "Bearer",
                         "grantedScope": "Basic WorkReleasingAndCompletion", "userID": "synthetic"}
        if method == "GET":
            return self._get(path, parts, params)
        self.writes.append({"method": method, "path": path, "body": copy.deepcopy(body), "form": form,
                            "files": dict(files or {})})
        return self._write(method, path, parts, body or {}, form or {}, files or {})

    def _get(self, path, parts, params):
        table = {
            "/api/jobs": lambda: self.jobs.values(),
            "/api/clients": lambda: self.clients.values(),
            "/api/persons": lambda: self.persons.values(),
            "/api/clients/contacts": lambda: [{k: v for k, v in c.items() if not k.startswith("_")}
                                              for c in self.client_contacts],
            "/api/jobs/contacts": lambda: [self._job_contact_view(c) for c in self.job_contacts],
            "/api/jobactivities": lambda: self.activities.values(),
            "/api/regions": lambda: self.regions,
            "/api/jobs/customfieldschemas": lambda: self.job_fields,
            "/api/persons/customfieldschemas": lambda: self.person_fields,
            "/api/jobactivities/completionanswerstates": lambda: self.answers,
        }
        key = path.lower()
        if key == "/api/jobs/workflowtemplates":
            return 200, {"jobWorkflowTemplates": self.templates}
        if key == "/api/miscellaneous/contactdetailsprimarycommunicationmethods":
            return 200, self.methods
        if key == "/api/miscellaneous/preferredcommunicationgroups":
            return 200, self.groups
        if len(parts) == 4 and parts[1].lower() == "jobactivities" and parts[3].lower() == "questions":
            return 200, copy.deepcopy(self.questions.get(parts[2], []))
        if parts and parts[-1].lower() == "messages" and len(parts) == 4:
            rows = self.messages.get(key[: -len("/messages")], [])
            return 200, {"value": copy.deepcopy(sorted(rows, key=lambda r: r["createdOnUtc"], reverse=True))}
        if key not in table:
            return 404, {"error": "no such route"}
        rows = [copy.deepcopy(r) for r in table[key]()]
        flt = params.get("$filter")
        if flt:
            rows = [r for r in rows if self._match(r, flt)]
        if params.get("$orderby") == "createdOnUtc desc":
            rows.sort(key=lambda r: r.get("createdOnUtc") or "", reverse=True)
        if params.get("$top"):
            rows = rows[: int(params["$top"])]
        return 200, {"value": rows}

    @staticmethod
    def _match(row: dict, flt: str) -> bool:
        for clause in flt.split(" and "):
            fld, _, value = clause.strip().partition(" eq ")
            if value.startswith("'"):
                value = value[1:-1].replace("''", "'")
            node = row
            for part in fld.split("/"):
                node = node.get(part) if isinstance(node, dict) else None
            if str(node).lower() != value.lower():
                return False
        return True

    def _job_contact_view(self, c):
        g = c.get("_group")
        desc = next((x["description"] for x in self.groups if x["preferredCommunicationGroupID"] == g), None)
        return {"jobID": c["jobID"], "personID": c["personID"], "relationship": c.get("relationship"),
                "fullName": self.persons[c["personID"]]["fullName"],
                "preferredCommunicationGroup": {"preferredCommunicationGroupID": g, "description": desc}}

    def _merge(self, target: dict, changes: dict) -> None:
        for key, value in changes.items():
            if key in GROUP_FIELDS:
                nested, table = GROUP_FIELDS[key]
                desc = next((x["description"] for x in getattr(self, table)
                             if list(x.values())[0] == value), None)
                target[nested] = {list(getattr(self, table)[0].keys())[0]: value, "description": desc}
            elif key == "customFieldValues":
                target[key] = copy.deepcopy(value)  # whole collection replaced
            elif isinstance(value, dict) and isinstance(target.get(key), dict):
                self._merge(target[key], value)
            else:
                target[key] = value

    def _write(self, method, path, parts, body, form, files):
        p = [x.lower() for x in parts]
        if method == "PATCH" and p[:2] == ["api", "jobs"] and len(p) == 3:
            job = self.jobs.get(parts[2])
            if not job:
                return 404, {}
            self._merge(job, body)
            if self.patch_hook:
                self.patch_hook("job", job)
            return 200, {}
        if method == "PATCH" and p[:2] == ["api", "clients"] and len(p) == 3:
            client = self.clients[parts[2]]
            self._merge(client, body)
            if self.patch_hook:
                self.patch_hook("client", client)
            return 200, {}
        if method == "PATCH" and p[:2] == ["api", "persons"] and len(p) == 3:
            person = self.persons[parts[2]]
            self._merge(person, body)
            person["fullName"] = f"{person.get('givenName') or ''} {person.get('surname') or ''}".strip()
            return 200, {}
        if method == "POST" and p == ["api", "clients"]:
            cid = self.add_client(body["name"])
            self._merge(self.clients[cid], body)
            return 201, {"clientID": cid}
        if method == "POST" and p == ["api", "persons"]:
            pid = self.add_person(body.get("givenName"), body.get("surname"))
            self._merge(self.persons[pid], body)
            return 201, {"personID": pid}
        if method == "POST" and p == ["api", "jobs"]:
            site = body["siteAddress"]
            jid = self.add_job(body["clientID"], str(next(self.numbers)), site.get("lotNumber"), site.get("line1"),
                               site.get("suburb"), site.get("postcode"), days_ago=0)
            self.jobs[jid]["customFieldValues"] = copy.deepcopy(body.get("customFieldValues") or [])
            return 201, {"jobID": jid}
        if method in ("POST", "PATCH") and p[:2] == ["api", "clients"] and len(p) == 5 and p[3] == "contacts":
            rows = [c for c in self.client_contacts if c["clientID"] == parts[2] and c["personID"] == parts[4]]
            if method == "POST":
                if rows:
                    return 409, {}
                row = {"clientID": parts[2], "personID": parts[4],
                       "fullName": self.persons[parts[4]]["fullName"], "isPrimaryContact": False,
                       "isSecondaryContact": False, "relationship": None}
                self.client_contacts.append(row)
                rows = [row]
            row = rows[0]
            for k, v in body.items():
                row["_group" if k == "preferredCommunicationGroupID" else k] = v
            return 200, {}
        if method in ("POST", "PATCH") and p[:2] == ["api", "jobs"] and len(p) == 5 and p[3] == "contacts":
            rows = [c for c in self.job_contacts if c["jobID"] == parts[2] and c["personID"] == parts[4]]
            if method == "POST":
                row = {"jobID": parts[2], "personID": parts[4], "relationship": None, "_group": None}
                self.job_contacts.append(row)
                rows = [row]
            for k, v in body.items():
                rows[0]["_group" if k == "preferredCommunicationGroupID" else k] = v
            return 200, {}
        if method == "POST" and p[:2] == ["api", "jobactivities"] and p[-1] == "complete":
            self.activities[parts[2]]["completionDate"] = body["completionDate"]
            return 200, {"activityID": parts[2], "completionDate": body["completionDate"]}
        if method == "PUT" and p[:2] == ["api", "jobactivities"] and p[3] == "questions":
            for q in self.questions[parts[2]]:
                if q["completionQuestionID"] == parts[4]:
                    q["answer"] = {"answerStateID": body.get("completionAnswerStateID"),
                                   "note": body.get("note"), "answerState": None}
            return 200, {}
        if method == "POST" and p[-1] == "messages":
            owner = "/" + "/".join(parts[:-1])
            message = {"messageID": _id(), "subject": form.get("Subject"), "body": form.get("Body"),
                       "createdOnUtc": _now()}
            self.messages.setdefault(owner.lower(), []).append(message)
            return 201, {"messageID": message["messageID"],
                         "documents": [{"documentID": _id()} for _ in files]}
        return 404, {"error": "unsupported in fake"}


# ---- adapters -------------------------------------------------------------
def _parse_multipart(content_type: str, content: bytes):
    """Raw split on the boundary: keeps attachment bytes exact (an email parser
    would turn a .eml attachment into a nested message)."""
    boundary = re.search(r'boundary="?([^";]+)"?', content_type).group(1).encode()
    form, files = {}, {}
    for chunk in content.split(b"--" + boundary)[1:]:
        if chunk.startswith(b"--"):
            break
        head, _, payload = chunk.lstrip(b"\r\n").partition(b"\r\n\r\n")
        payload = payload[:-2] if payload.endswith(b"\r\n") else payload
        disposition = head.decode("latin-1")
        name = re.search(r'name="([^"]*)"', disposition).group(1)
        filename = re.search(r'filename="([^"]*)"', disposition)
        if filename:
            files[name] = (filename.group(1), payload)
        else:
            form[name] = payload.decode()
    return form, files


def _dispatch(fake: FakeOSC, method: str, path: str, params: dict, content_type: str, content: bytes):
    body = form = files = None
    if content and content_type.startswith("multipart/form-data"):
        form, files = _parse_multipart(content_type, content)
    elif content and "json" in content_type:
        body = json.loads(content)  # the token request is form-encoded and needs no body here
    return fake.handle(method, path, params, body, form, files)


def transport(fake: FakeOSC) -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        content = await request.aread()
        status, data = _dispatch(fake, request.method, request.url.path, dict(request.url.params),
                                 request.headers.get("content-type", ""), content)
        return httpx.Response(status, json=data)
    return httpx.MockTransport(handler)


def serve(fake: FakeOSC) -> tuple[ThreadingHTTPServer, str]:
    """Run the fake on a free local port; returns (server, base_url)."""
    class Handler(BaseHTTPRequestHandler):
        def _any(self):
            url = urlsplit(self.path)
            length = int(self.headers.get("content-length") or 0)
            content = self.rfile.read(length) if length else b""
            status, data = _dispatch(fake, self.command, url.path, dict(parse_qsl(url.query)),
                                     self.headers.get("content-type", ""), content)
            out = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = _any

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
