"""The three tools end to end against a fake DocuSign: no network, synthetic data."""
import importlib
import json
import logging
import os
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import httpx

from docusign_upload.client import DocuSignClient, DocuSignError
from support import FakeDocuSign, keypair, make_config, make_pdf, write_key
from support import readback_for as real_readback_for

with patch("docusign_upload.config.load_config", return_value=make_config("/nonexistent/key.pem")):
    server = importlib.import_module("docusign_upload.server")

API = "/restapi/v2.1/accounts/acct-synthetic"
ENV = f"{API}/envelopes/env-synthetic"
ALLOWED_CALLS = {
    ("POST", "/oauth/token"), ("GET", "/oauth/userinfo"),
    ("GET", f"{API}/templates"), ("GET", f"{API}/templates/tmpl-qld-single/recipients"),
    ("GET", f"{API}/envelopes"), ("POST", f"{API}/envelopes"),
    ("GET", ENV), ("GET", f"{ENV}/documents"), ("GET", f"{ENV}/recipients"),
    ("GET", f"{ENV}/custom_fields"),
}


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        keys = os.path.join(self.tmp.name, "keys")
        self.root = os.path.join(self.tmp.name, "runtime")
        self.job = os.path.join(self.root, "CONTRACT DOCUMENTATION")
        os.makedirs(keys)
        os.makedirs(self.job)
        self.config = make_config(write_key(keys, keypair()[0]), (self.root,))
        self.fake = FakeDocuSign()
        self.client = DocuSignClient(self.config, httpx.AsyncClient(transport=self.fake.transport()))
        self.addAsyncCleanup(self.client.aclose)
        for p in (patch.object(server, "_config", self.config),
                  patch.object(server, "_client", self.client)):
            p.start()
            self.addCleanup(p.stop)
        self.args = {
            "template_name": "QLD Build _ Single Buyer",
            "recipients": [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}],
            "email_subject": "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE",
            "email_blurb": "Dear Alex,\n\nPlease find the building contract for review and signing."
                           "\n\nThank you\nSales Admin",
            "job_no": "00001",
            "documents": [self.doc("BUILD CONTRACT", 37), self.doc("INCLUSIONS", 15),
                          self.doc("PLANS", 5)],
        }

    def doc(self, kind, pages, name=None):
        name = name or f"{kind}_LOT 1_TESTVILLE_EXAMPLE.pdf"
        return {"kind": kind, "path": make_pdf(os.path.join(self.job, name), pages)}

    def posts(self):
        return [c for c in self.fake.calls() if c == ("POST", f"{API}/envelopes")]

    async def test_token_info(self):
        out = await server.docusign_token_info()
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["environment"], out["account"], out["user"]),
                         ("SANDBOX", "synthetic", "Synthetic User"))
        self.assertNotIn(self.config.private_key_path, json.dumps(out))

    async def test_preview_plans_and_creates_nothing(self):
        out = await server.docusign_draft_preview(**self.args)
        self.assertTrue(out["ok"], out)
        self.assertEqual([d["tabs"] for d in out["plan"]["documents"]],
                         ["carried from the template", "carried from the template",
                          "none, flagged: 5 pages, the template's has 4"])
        self.assertEqual(self.posts(), [])

    async def test_create_makes_one_draft_and_reads_it_back(self):
        out = await server.docusign_create_draft(**self.args)
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["envelopeId"], out["status"], out["environment"]),
                         ("env-synthetic", "created", "SANDBOX"))
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["plan"]["template"], "QLD Build _ Single Buyer")
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.fake.created["status"], "created")
        post = [r for r in self.fake.requests if r.method == "POST" and r.url.path.endswith("/envelopes")][0]
        self.assertEqual(post.url.params["merge_roles_on_draft"], "true")
        self.assertLessEqual(set(self.fake.calls()), ALLOWED_CALLS)

    async def test_writes_off_refuses_before_any_call(self):
        with patch.object(server, "_config", replace(self.config, enable_writes=False)):
            out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertIn("Writes are disabled", out["error"])
        self.assertEqual(self.fake.calls(), [])

    async def test_an_existing_draft_for_the_job_stops_both_tools(self):
        self.fake.existing = [{"envelopeId": "env-old", "status": "created", "customFields": {
            "textCustomFields": [{"name": "JobNo", "value": "00001"}]}}]
        for tool in (server.docusign_draft_preview, server.docusign_create_draft):
            out = await tool(**self.args)
            self.assertTrue(out["stop"], out)
            self.assertIn("env-old", out["error"])
        self.assertEqual(self.posts(), [])

    async def test_stops_reach_the_caller(self):
        outside = make_pdf(os.path.join(self.tmp.name, "outside.pdf"), 37)
        cases = [
            ({"documents": [self.doc("BUILD CONTRACT", 36, name="BUILD CONTRACT_SHORT.pdf")]},
             "fixed form"),
            ({"documents": [{"kind": "BUILD CONTRACT", "path": outside}]},
             "outside the allowed upload roots"),
            ({"template_name": "QLD Build _ 2 Buyer"}, "matched 0 templates"),
            ({"recipients": [{"role": "BUYER", "name": "A", "email": "a@example.com"}]},
             "not on template"),
        ]
        for change, needle in cases:
            with self.subTest(needle=needle):
                out = await server.docusign_draft_preview(**{**self.args, **change})
                self.assertFalse(out["ok"])
                self.assertTrue(out["stop"])
                self.assertIn(needle, out["error"])

    async def test_job_no_with_query_characters_is_refused_before_network(self):
        out = await server.docusign_draft_preview(**{**self.args, "job_no": "00001&status=any"})
        self.assertFalse(out["ok"])
        self.assertIn("job_no", out["error"])
        self.assertEqual(self.fake.calls(), [])

    async def test_a_docusign_error_is_returned_verbatim_and_not_retried(self):
        self.fake.create_error = (400, {"errorCode": "RECIPIENT_LIMIT_EXCEEDED",
                                        "message": "Synthetic limit message."})
        out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertEqual((out["errorCode"], out["message"]),
                         ("RECIPIENT_LIMIT_EXCEEDED", "Synthetic limit message."))
        self.assertEqual(len(self.posts()), 1)

    async def test_a_gateway_error_on_create_says_the_outcome_is_uncertain(self):
        # a 5xx (or a proxy's HTML page) can arrive after DocuSign created the draft
        self.fake.create_error = (502, "<html><body>Bad gateway</body></html>")
        out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertIn("uncertain", out["error"])
        self.assertIn("docusign_draft_preview", out["error"])
        self.assertNotIn("refused", out["error"])
        self.assertEqual(out["status"], 502)
        self.assertEqual(len(self.posts()), 1)

    async def test_a_read_back_it_cannot_parse_still_returns_the_envelope_id(self):
        def malformed(body, template_tabs):
            readback = real_readback_for(body, template_tabs)
            readback["custom_fields"] = {"textCustomFields": None}  # a shape the fake never sends
            return readback
        with patch("support.readback_for", side_effect=malformed):
            out = await server.docusign_create_draft(**self.args)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["envelopeId"], "env-synthetic")
        self.assertIn("the draft exists", out["read_back"])
        self.assertEqual(len(self.posts()), 1)

    async def test_a_transport_failure_says_the_outcome_is_uncertain(self):
        self.fake.create_transport_error = True
        out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertIn("uncertain", out["error"])
        self.assertIn("docusign_draft_preview", out["error"])
        self.assertEqual(len(self.posts()), 1)

    def test_request_urls_stay_out_of_the_server_log(self):
        # FastMCP logs at INFO; httpx would then log every URL (account and envelope ids)
        # into the MCP log, which lives in the user profile on C:
        for name in ("httpx", "httpcore"):
            self.assertGreaterEqual(logging.getLogger(name).getEffectiveLevel(), logging.WARNING, name)

    async def test_a_docusign_error_on_a_read_is_reported_with_its_code(self):
        refused = DocuSignError("DocuSign returned 401.", status=401,
                                error_code="USER_LACKS_PERMISSIONS", detail="Synthetic read refusal.")
        with patch.object(self.client, "list_templates", AsyncMock(side_effect=refused)):
            out = await server.docusign_draft_preview(**self.args)
        self.assertFalse(out["ok"])
        self.assertEqual((out["status"], out["errorCode"], out["message"]),
                         (401, "USER_LACKS_PERMISSIONS", "Synthetic read refusal."))

    async def test_consent_required_is_reported_with_the_consent_url(self):
        self.fake.token_error = "consent_required"
        out = await server.docusign_draft_preview(**self.args)
        self.assertFalse(out["ok"])
        self.assertTrue(out["consent_url"].startswith("https://account-d.docusign.com/oauth/auth?"))

    async def test_not_configured(self):
        message = "Missing required setting(s): DOCUSIGN_USER_ID."
        with patch.object(server, "_config", None), patch.object(server, "_config_error", message):
            for tool in (server.docusign_draft_preview, server.docusign_create_draft):
                self.assertIn("DOCUSIGN_USER_ID", (await tool(**self.args))["error"])
            self.assertIn("DOCUSIGN_USER_ID", (await server.docusign_token_info())["error"])
