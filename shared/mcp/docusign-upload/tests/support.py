"""Synthetic fixtures for the docusign-upload tests. No real data, no network, no credentials."""
from __future__ import annotations

import os

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
