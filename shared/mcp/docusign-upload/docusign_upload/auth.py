"""JWT Grant for the DocuSign eSignature REST API.

An RS256 assertion (iss the integration key, sub the impersonated user, aud the
environment's auth server, scope "signature impersonation") is exchanged at
/oauth/token for an access token, and /oauth/userinfo then gives the base URI
of the configured account. The key file is opened only here, only to sign; its
contents never leave this module and no message includes its path.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx
import jwt

from .config import Config

SCOPE = "signature impersonation"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
REFRESH_MARGIN_SECONDS = 300


class AuthError(RuntimeError):
    """Sign-in failed. consent_url is set when the user has not consented yet."""

    def __init__(self, message: str, *, consent_url: str | None = None, status: int | None = None):
        super().__init__(message)
        self.consent_url = consent_url
        self.status = status


@dataclass(frozen=True)
class Session:
    access_token: str
    expires_at: float  # time.monotonic() seconds
    base_uri: str
    account_name: str
    user_name: str

    def account_url(self, account_id: str) -> str:
        return f"{self.base_uri.rstrip('/')}/restapi/v2.1/accounts/{quote(account_id, safe='')}"


def build_assertion(config: Config, private_key_pem: bytes, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    claims = {"iss": config.integration_key, "sub": config.user_id, "aud": config.auth_host,
              "iat": now, "exp": now + 3600, "scope": SCOPE}
    return jwt.encode(claims, private_key_pem, algorithm="RS256")


def _json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class Authenticator:
    def __init__(self, config: Config, http: httpx.AsyncClient):
        self.config = config
        self.http = http
        self._session: Session | None = None

    async def session(self) -> Session:
        if self._session is None or time.monotonic() >= self._session.expires_at:
            self._session = await self._login()
        return self._session

    async def _login(self) -> Session:
        try:
            with open(self.config.private_key_path, "rb") as fh:
                pem = fh.read()
        except OSError:
            raise AuthError("The private key file could not be read by the server. Check "
                            "DOCUSIGN_PRIVATE_KEY_PATH and the folder's permissions.") from None
        assertion = build_assertion(self.config, pem)
        host = self.config.auth_host
        resp = await self.http.post(f"https://{host}/oauth/token",
                                    data={"grant_type": GRANT_TYPE, "assertion": assertion})
        if resp.status_code != 200:
            body = _json(resp)
            error = str(body.get("error") or "no error code")
            if error == "consent_required":
                raise AuthError("Consent has not been granted for this integration key and user. "
                                "The template owner opens the consent URL once, signs in and "
                                "clicks Accept.", consent_url=self.config.consent_url(),
                                status=resp.status_code)
            detail = str(body.get("error_description") or "")
            raise AuthError(f"Token request refused ({resp.status_code} {error}"
                            f"{', ' + detail if detail else ''}). Check the integration key, the "
                            "user id, the key pair and the environment.", status=resp.status_code)
        payload = resp.json()
        token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))
        info = await self.http.get(f"https://{host}/oauth/userinfo",
                                   headers={"Authorization": f"Bearer {token}"})
        if info.status_code != 200:
            raise AuthError(f"userinfo failed ({info.status_code}).", status=info.status_code)
        data = _json(info)
        account = next((a for a in data.get("accounts", [])
                        if a.get("account_id") == self.config.account_id), None)
        if account is None:
            raise AuthError("The configured account is not one of this user's accounts. Check "
                            "DOCUSIGN_ACCOUNT_ID against the Apps and Keys page.")
        return Session(access_token=token,
                       expires_at=time.monotonic() + max(expires_in - REFRESH_MARGIN_SECONDS, 60),
                       base_uri=str(account.get("base_uri", "")),
                       account_name=str(account.get("account_name", "")),
                       user_name=str(data.get("name", "")))
