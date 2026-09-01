"""HTTP client for the OSC API: OAuth token handling plus request dispatch.

The OSC token endpoint follows RFC6750/RFC7617: HTTP Basic auth (client id +
secret) on POST /api/Token with a form body of GrantType=client_credentials.
It returns a bearer access token (expiresIn seconds) which is sent as
Authorization: Bearer <token> on every subsequent call.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from .config import Config

# Methods that change server state. Kept here so the server layer and the
# client agree on exactly one definition of "write".
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class OSCError(RuntimeError):
    """An OSC API call failed. Carries the HTTP status and response body."""

    def __init__(self, message: str, status: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


class OSCClient:
    def __init__(self, config: Config):
        self.config = config
        self._client = httpx.AsyncClient(
            verify=config.verify_tls,
            timeout=config.timeout,
        )
        self._access_token: str | None = None
        self._token_expiry: float = 0.0  # monotonic seconds
        self._token_meta: dict[str, Any] = {}
        self._spec: dict[str, Any] | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---- auth -------------------------------------------------------------
    async def _fetch_token(self) -> None:
        data = {"GrantType": "client_credentials"}
        if self.config.scopes:
            data["Scope"] = self.config.scopes
        resp = await self._client.post(
            self.config.token_url,
            data=data,
            auth=(self.config.client_id, self.config.client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise OSCError(
                f"Token request failed ({resp.status_code}). Check credentials, "
                f"base URL, and that the environment is reachable.",
                status=resp.status_code,
                body=resp.text[:500],
            )
        payload = resp.json()
        self._access_token = payload["accessToken"]
        expires_in = float(payload.get("expiresIn", 1800))
        # Refresh a minute early to avoid using a token that expires mid-flight.
        self._token_expiry = time.monotonic() + max(expires_in - 60, 30)
        self._token_meta = {
            "expiresIn": payload.get("expiresIn"),
            "grantedScope": payload.get("grantedScope"),
            "tokenType": payload.get("tokenType"),
            "userID": payload.get("userID"),
        }

    async def _ensure_token(self) -> str:
        if self._access_token is None or time.monotonic() >= self._token_expiry:
            await self._fetch_token()
        assert self._access_token is not None
        return self._access_token

    async def token_info(self) -> dict[str, Any]:
        """Return granted scope and expiry metadata (forces a token fetch)."""
        await self._ensure_token()
        return dict(self._token_meta)

    # ---- requests ---------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated request and return a structured result."""
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        # Several OSC "GET" collection endpoints (e.g. /api/Jobs) accept an OData
        # filter in a JSON request body. httpx will set the content-type when a
        # json body is supplied for any method.
        resp = await self._client.request(
            method.upper(),
            self.config.api_url(path),
            params=params,
            json=json_body,
            headers=headers,
        )
        result: dict[str, Any] = {
            "status": resp.status_code,
            "ok": resp.is_success,
            "method": method.upper(),
            "path": path,
        }
        text = resp.text
        try:
            result["data"] = resp.json()
        except ValueError:
            result["data"] = None
            if text:
                result["text"] = text[:2000]
        if not resp.is_success:
            result["error"] = _explain_status(resp.status_code)
        return result

    # ---- spec -------------------------------------------------------------
    async def get_spec(self) -> dict[str, Any]:
        """Fetch and cache the OpenAPI spec used for endpoint introspection."""
        if self._spec is not None:
            return self._spec
        if not self.config.swagger_url:
            raise OSCError(
                "No OSC_SWAGGER_URL configured, so endpoint introspection is "
                "unavailable. osc_get / osc_write still work with an explicit path."
            )
        resp = await self._client.get(self.config.swagger_url)
        if resp.status_code != 200:
            raise OSCError(
                f"Could not load OpenAPI spec ({resp.status_code}) from "
                f"{self.config.swagger_url}.",
                status=resp.status_code,
            )
        self._spec = resp.json()
        return self._spec


def _explain_status(status: int) -> str:
    return {
        401: "Unauthorised - token missing/expired or credentials rejected.",
        403: "Forbidden - the credential's granted scope does not cover this "
             "endpoint. Request a wider OSC_SCOPES if authorised.",
        404: "Not found - check the path against osc_list_endpoints.",
        415: "Unsupported media type - this endpoint expects a JSON body; pass "
             "one via the body/odata_filter argument.",
        429: "Too many requests - rate limited; back off and retry.",
    }.get(status, f"HTTP {status}.")
