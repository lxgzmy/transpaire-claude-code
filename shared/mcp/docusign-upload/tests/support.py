"""Synthetic fixtures for the docusign-upload tests. No real data, no network, no credentials."""
from __future__ import annotations

import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

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
