"""Checks on a job PDF before any of it goes into a request.

The path must be absolute and sit under an upload root (resolved, so a link
out of the root is refused). The file must be a regular .pdf that starts with
%PDF-, holds at most 25 MB, is not password-protected and has a readable page
count. Only the PDF's structure is read here; draft.py reads the bytes for the
request after every check has passed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from .config import is_inside

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


class PdfCheckError(Exception):
    """A document failed a check; the message says which."""


@dataclass(frozen=True)
class PdfFile:
    path: str
    name: str
    bytes: int
    pages: int


def check_pdf(path: str, roots: tuple[str, ...]) -> PdfFile:
    if not path or not os.path.isabs(path):
        raise PdfCheckError("not an absolute path")
    if not any(is_inside(path, root) for root in roots):
        raise PdfCheckError("outside the allowed upload roots")
    p = Path(path)
    if not p.is_file():
        raise PdfCheckError("not an existing file on the server")
    if p.suffix.lower() != ".pdf":
        raise PdfCheckError("not a .pdf file")
    size = p.stat().st_size
    if size > MAX_DOCUMENT_BYTES:
        raise PdfCheckError(f"{size / 1048576:.1f} MB, over the {MAX_DOCUMENT_BYTES // 1048576} MB "
                            "limit per document")
    with p.open("rb") as fh:
        if fh.read(5) != b"%PDF-":
            raise PdfCheckError("does not start with %PDF-, so it is not a PDF")
    try:
        reader = PdfReader(str(p))
        encrypted = reader.is_encrypted
        pages = 0 if encrypted else len(reader.pages)
    except Exception as exc:  # pypdf raises several types on a damaged file
        raise PdfCheckError("its page count could not be read (a damaged PDF?)") from exc
    if encrypted:
        raise PdfCheckError("password-protected, and DocuSign cannot open it")
    if pages < 1:
        raise PdfCheckError("has no pages")
    return PdfFile(path=path, name=p.name, bytes=size, pages=pages)
