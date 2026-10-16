"""JWT Grant: the assertion, the token exchange, userinfo, consent and caching."""
import dataclasses
import tempfile
import time
import unittest
from urllib.parse import parse_qs

import httpx
import jwt

from docusign_upload.auth import AuthError, Authenticator, build_assertion
from support import ACCOUNT, BASE, keypair, make_config, write_key


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.private, self.public = keypair()
        self.config = make_config(write_key(self.tmp.name, self.private))
        self.token_calls = 0
        self.forms = []
        self.token_reply = (200, {"access_token": "synthetic-token", "token_type": "Bearer",
                                  "expires_in": 3600})
        self.accounts = [{"account_id": ACCOUNT, "account_name": "synthetic", "base_uri": BASE}]

        def handle(request):
            if request.url.path == "/oauth/token":
                self.token_calls += 1
                self.forms.append(parse_qs(request.content.decode()))
                status, body = self.token_reply
                return httpx.Response(status, json=body)
            if request.url.path == "/oauth/userinfo":
                assert request.headers["Authorization"] == "Bearer synthetic-token"
                return httpx.Response(200, json={"name": "Synthetic User", "accounts": self.accounts})
            return httpx.Response(404)

        self.http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        self.addAsyncCleanup(self.http.aclose)
        self.auth = Authenticator(self.config, self.http)

    def test_assertion_claims_and_signature(self):
        token = build_assertion(self.config, self.private, now=1_000_000)
        claims = jwt.decode(token, self.public, algorithms=["RS256"],
                            audience="account-d.docusign.com",
                            options={"verify_exp": False, "verify_iat": False})
        self.assertEqual(claims, {"iss": "ik-synthetic-0000", "sub": "user-synthetic-0000",
                                  "aud": "account-d.docusign.com", "iat": 1_000_000,
                                  "exp": 1_003_600, "scope": "signature impersonation"})
        self.assertEqual(jwt.get_unverified_header(token)["alg"], "RS256")

    async def test_session_signs_in_once_and_reuses_the_token(self):
        first = await self.auth.session()
        second = await self.auth.session()
        self.assertIs(first, second)
        self.assertEqual(self.token_calls, 1)
        self.assertEqual(self.forms[0]["grant_type"], ["urn:ietf:params:oauth:grant-type:jwt-bearer"])
        self.assertIn("assertion", self.forms[0])
        self.assertEqual(first.account_url(ACCOUNT), f"{BASE}/restapi/v2.1/accounts/{ACCOUNT}")
        self.assertEqual((first.account_name, first.user_name), ("synthetic", "Synthetic User"))

    async def test_an_expired_token_signs_in_again(self):
        session = await self.auth.session()
        self.auth._session = dataclasses.replace(session, expires_at=time.monotonic() - 1)
        await self.auth.session()
        self.assertEqual(self.token_calls, 2)

    async def test_consent_required_carries_the_consent_url(self):
        self.token_reply = (400, {"error": "consent_required"})
        with self.assertRaises(AuthError) as cm:
            await self.auth.session()
        self.assertIn("Consent", str(cm.exception))
        self.assertTrue(cm.exception.consent_url.startswith("https://account-d.docusign.com/oauth/auth?"))

    async def test_a_refused_token_names_the_error_not_the_key(self):
        self.token_reply = (400, {"error": "invalid_grant",
                                  "error_description": "no_valid_keys_or_signatures"})
        with self.assertRaises(AuthError) as cm:
            await self.auth.session()
        self.assertIn("invalid_grant", str(cm.exception))
        self.assertIn("no_valid_keys_or_signatures", str(cm.exception))
        self.assertNotIn(self.config.private_key_path, str(cm.exception))

    async def test_an_account_the_user_does_not_hold_is_refused(self):
        self.accounts = [{"account_id": "acct-other", "account_name": "other", "base_uri": BASE}]
        with self.assertRaisesRegex(AuthError, "not one of this user's accounts"):
            await self.auth.session()

    async def test_an_unreadable_key_file_is_reported_plainly(self):
        self.auth.config = make_config("/nonexistent/synthetic-key.pem")
        with self.assertRaisesRegex(AuthError, "could not be read"):
            await self.auth.session()
        self.assertEqual(self.token_calls, 0)
