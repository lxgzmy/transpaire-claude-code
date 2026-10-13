"""The only DocuSign calls this server can make.

Reads: the template list (with documents and recipients), one template's
recipients with tabs, the envelope list for the duplicate check, and one
envelope's status, documents, recipients with tabs and custom fields. One
write: create an envelope, and only with status "created". There is no PUT,
PATCH or DELETE and no generic request method, so nothing here can send, void,
correct or delete an envelope.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .auth import Authenticator
from .config import Config
from .draft import DRAFT_STATUS

# Every status except voided, declined and deleted: a live envelope for the job blocks a new draft.
LIVE_STATUSES = "created,sent,delivered,signed,completed,processing,timedout"


class DocuSignError(RuntimeError):
    """A DocuSign call failed. Carries DocuSign's own errorCode and message when it sent them."""

    def __init__(self, message: str, *, status: int | None = None, error_code: str | None = None,
                 detail: str | None = None):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.detail = detail


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _result(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if not resp.is_success:
        raise DocuSignError(f"DocuSign returned {resp.status_code}.", status=resp.status_code,
                            error_code=data.get("errorCode"), detail=data.get("message"))
    return data


class DocuSignClient:
    def __init__(self, config: Config, http: httpx.AsyncClient | None = None):
        self.config = config
        self.http = http or httpx.AsyncClient(timeout=config.timeout)
        self.auth = Authenticator(config, self.http)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        session = await self.auth.session()
        resp = await self.http.get(session.account_url(self.config.account_id) + path,
                                   params=params, headers=_headers(session.access_token))
        return _result(resp)

    async def list_templates(self, search_text: str) -> list[dict[str, Any]]:
        data = await self._get("/templates", {"search_text": search_text,
                                              "include": "documents,recipients"})
        return list(data.get("envelopeTemplates") or [])

    async def template_recipients(self, template_id: str) -> dict[str, Any]:
        return await self._get(f"/templates/{quote(template_id, safe='')}/recipients",
                               {"include_tabs": "true"})

    async def list_envelopes(self, from_date: str, custom_field: str) -> list[dict[str, Any]]:
        data = await self._get("/envelopes", {"from_date": from_date, "custom_field": custom_field,
                                              "status": LIVE_STATUSES, "include": "custom_fields"})
        return list(data.get("envelopes") or [])

    async def create_draft(self, body: dict[str, Any]) -> dict[str, Any]:
        if body.get("status") != DRAFT_STATUS:
            raise DocuSignError("Refused: this server only creates drafts (status 'created').")
        session = await self.auth.session()
        resp = await self.http.post(session.account_url(self.config.account_id) + "/envelopes",
                                    params={"merge_roles_on_draft": "true"}, json=body,
                                    headers=_headers(session.access_token))
        return _result(resp)

    async def envelope(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}")

    async def envelope_documents(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/documents")

    async def envelope_recipients(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/recipients",
                               {"include_tabs": "true"})

    async def envelope_custom_fields(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/custom_fields")
