"""Synthetic fixtures for the docusign-upload tests. No real data, no network, no credentials."""
from __future__ import annotations

import json
import os

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pypdf import PdfWriter

from docusign_upload.config import Config

ACCOUNT = "acct-synthetic"
BASE = "https://demo.invalid"

_KEYPAIR: tuple[bytes, bytes] | None = None


def keypair() -> tuple[bytes, bytes]:
    """(private PEM, public PEM), generated once per test run."""
    global _KEYPAIR
    if _KEYPAIR is None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _KEYPAIR = (
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()),
            key.public_key().public_bytes(serialization.Encoding.PEM,
                                          serialization.PublicFormat.SubjectPublicKeyInfo),
        )
    return _KEYPAIR


def write_key(folder: str, private_pem: bytes) -> str:
    path = os.path.join(folder, "synthetic-key.pem")
    with open(path, "wb") as fh:
        fh.write(private_pem)
    return path


def make_config(key_path: str, roots: tuple[str, ...] = (), **overrides) -> Config:
    values = dict(environment="demo", integration_key="ik-synthetic-0000",
                  user_id="user-synthetic-0000", account_id=ACCOUNT, private_key_path=key_path,
                  upload_roots=roots, enable_writes=True, enable_writes_source="env",
                  consent_redirect_uri="https://example.com/consent", timeout=5.0)
    values.update(overrides)
    return Config(**values)


def make_pdf(path: str, pages: int, *, password: str | None = None) -> str:
    """A blank A4 PDF with the given page count (optionally password-protected)."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if password:
        writer.encrypt(password, algorithm="AES-256")
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def qld_single_template() -> dict:
    """Shaped like the sandbox's QLD Single Buyer template: three documents (a mix of small
    and eight-digit ids, as in the account) and two signer roles. Synthetic names and ids."""
    return {"templateId": "tmpl-qld-single", "name": "QLD Build _ Single Buyer ",
            "documents": [
                {"documentId": "1", "name": "BUILD CONTRACT _LOT 0_SYNTHETIC.pdf", "pages": "37"},
                {"documentId": "86092972", "name": "INCLUSIONS_LOT 0_SYNTHETIC.pdf", "pages": "15"},
                {"documentId": "3", "name": "PLANS_LOT 0_SYNTHETIC.pdf", "pages": "4"}],
            "recipients": {"signers": [
                {"roleName": "Buyer", "recipientId": "1", "routingOrder": "1"},
                {"roleName": "Builder", "recipientId": "3", "routingOrder": "2"}],
                "carbonCopies": [], "recipientCount": "2"}}


def nsw_company_template() -> dict:
    """Shaped like NSW Build _ Company: four documents, the prelim named EXECUTED-..."""
    return {"templateId": "tmpl-nsw-company", "name": "NSW Build _ Company",
            "documents": [
                {"documentId": "1", "name": "BUILD CONTRACT_LOT 0_SYNTHETIC.pdf", "pages": "45"},
                {"documentId": "2", "name": "INCLUSIONS_LOT 0_SYNTHETIC.pdf", "pages": "18"},
                {"documentId": "4", "name": "EXECUTED-PRELIMINARY AGREEMENT_LOT 0.pdf", "pages": "3"},
                {"documentId": "3", "name": "PLANS_LOT 0_SYNTHETIC.pdf", "pages": "5"}],
            "recipients": {"signers": [
                {"roleName": "Buyer - Company Guarantor", "recipientId": "1", "routingOrder": "1"},
                {"roleName": "Builder", "recipientId": "2", "routingOrder": "2"},
                {"roleName": "Builder Witness", "recipientId": "3", "routingOrder": "3"},
                {"roleName": "Date Contract", "recipientId": "4", "routingOrder": "4"}]}}


def qld_single_template_tabs() -> dict:
    """The template's tabs, shaped like GET /templates/{id}/recipients?include_tabs=true.
    Same pattern as the real template: contract initials and signatures, inclusions initials
    on all but the last three pages, a plans signature on every page."""
    def tabs(doc, pages):
        return [{"documentId": doc, "pageNumber": str(p)} for p in pages]
    return {"signers": [
        {"roleName": "Buyer", "recipientId": "1", "routingOrder": "1", "tabs": {
            "signHereTabs": tabs("1", [3, 13]) + tabs("86092972", [13, 14, 15]) + tabs("3", [1, 2, 3, 4]),
            "initialHereTabs": tabs("1", range(6, 13)) + tabs("86092972", range(1, 13))}},
        {"roleName": "Builder", "recipientId": "3", "routingOrder": "2", "tabs": {
            "signHereTabs": tabs("1", [13]) + tabs("86092972", [13])}}],
        "recipientCount": "2"}


def readback_for(body: dict, template_tabs: dict) -> dict:
    """What DocuSign is expected to hold after the create: one document per composite (ids
    renumbered), the template's tabs on each carried document, each role once. The sandbox
    prototype checks the real service against the same expectation."""
    by_template_doc: dict[str, list[tuple[str, str, str]]] = {}
    for signer in template_tabs.get("signers", []):
        for tab_type, tabs in (signer.get("tabs") or {}).items():
            for tab in tabs:
                by_template_doc.setdefault(str(tab["documentId"]), []).append(
                    (signer["roleName"], tab_type, str(tab["pageNumber"])))
    roles = {s["roleName"]: {"roleName": s["roleName"], "recipientId": s["recipientId"],
                             "email": "builder@example.com", "tabs": {}}
             for s in template_tabs.get("signers", [])}
    documents = []
    for n, comp in enumerate(body["compositeTemplates"], start=1):
        doc = comp["document"]
        new_id = str(n)
        documents.append({"documentId": new_id, "name": doc["name"], "type": "content"})
        for signer in comp["inlineTemplates"][0]["recipients"]["signers"]:
            roles[signer["roleName"]]["email"] = signer["email"]
        if comp.get("serverTemplates"):
            for role, tab_type, page in by_template_doc.get(doc["documentId"], []):
                roles[role]["tabs"].setdefault(tab_type, []).append(
                    {"documentId": new_id, "pageNumber": page})
    custom = body["compositeTemplates"][0]["inlineTemplates"][0].get("customFields", {})
    return {"documents": {"envelopeDocuments": documents},
            "recipients": {"signers": list(roles.values()), "recipientCount": str(len(roles))},
            "custom_fields": custom}


class FakeDocuSign:
    """httpx.MockTransport handler standing in for DocuSign: auth, templates, envelopes.
    Anything it does not know answers 404 NOT_IN_FAKE, so a stray call shows up in a test."""

    ENVELOPE_ID = "env-synthetic"

    def __init__(self, template: dict | None = None, template_tabs: dict | None = None):
        self.template = template or qld_single_template()
        self.template_tabs = template_tabs or qld_single_template_tabs()
        self.existing: list[dict] = []
        self.token_error: str | None = None
        self.create_error: tuple[int, dict | str] | None = None
        self.create_transport_error = False
        self.requests: list[httpx.Request] = []
        self.created: dict | None = None
        self.readback: dict | None = None

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def calls(self) -> list[tuple[str, str]]:
        return [(r.method, r.url.path) for r in self.requests]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        method, path, host = request.method, request.url.path, request.url.host
        if host == "account-d.docusign.com":
            if (method, path) == ("POST", "/oauth/token"):
                if self.token_error:
                    return httpx.Response(400, json={"error": self.token_error})
                return httpx.Response(200, json={"access_token": "synthetic-token",
                                                 "token_type": "Bearer", "expires_in": 3600})
            if (method, path) == ("GET", "/oauth/userinfo"):
                return httpx.Response(200, json={"name": "Synthetic User", "accounts": [
                    {"account_id": ACCOUNT, "account_name": "synthetic", "base_uri": BASE,
                     "is_default": True}]})
        if host == "demo.invalid":
            api = f"/restapi/v2.1/accounts/{ACCOUNT}"
            env = f"{api}/envelopes/{self.ENVELOPE_ID}"
            if (method, path) == ("GET", f"{api}/templates"):
                return httpx.Response(200, json={"envelopeTemplates": [self.template]})
            if (method, path) == ("GET", f"{api}/templates/{self.template['templateId']}/recipients"):
                return httpx.Response(200, json=self.template_tabs)
            if (method, path) == ("GET", f"{api}/envelopes"):
                return httpx.Response(200, json={"envelopes": self.existing})
            if (method, path) == ("POST", f"{api}/envelopes"):
                if self.create_transport_error:
                    raise httpx.ConnectError("synthetic transport failure", request=request)
                if self.create_error:
                    status, payload = self.create_error
                    if isinstance(payload, dict):
                        return httpx.Response(status, json=payload)
                    return httpx.Response(status, text=payload)
                self.created = json.loads(request.content)
                self.readback = readback_for(self.created, self.template_tabs)
                return httpx.Response(201, json={"envelopeId": self.ENVELOPE_ID, "status": "created",
                                                 "uri": f"/envelopes/{self.ENVELOPE_ID}"})
            if method == "GET" and self.readback is not None:
                if path == env:
                    return httpx.Response(200, json={"envelopeId": self.ENVELOPE_ID, "status": "created",
                                                     "emailSubject": self.created["emailSubject"]})
                if path == f"{env}/documents":
                    return httpx.Response(200, json=self.readback["documents"])
                if path == f"{env}/recipients":
                    return httpx.Response(200, json=self.readback["recipients"])
                if path == f"{env}/custom_fields":
                    return httpx.Response(200, json=self.readback["custom_fields"])
        return httpx.Response(404, json={"errorCode": "NOT_IN_FAKE", "message": f"{method} {path}"})
