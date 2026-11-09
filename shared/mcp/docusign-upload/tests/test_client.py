"""The client's fixed call list and its error handling."""
import inspect
import json
import re
import tempfile
import unittest

import httpx

from docusign_upload import client as client_module
from docusign_upload.client import DocuSignClient, DocuSignError
from support import FakeDocuSign, keypair, make_config, write_key


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fake = FakeDocuSign()
        self.client = DocuSignClient(make_config(write_key(self.tmp.name, keypair()[0])),
                                     httpx.AsyncClient(transport=self.fake.transport()))
        self.addAsyncCleanup(self.client.aclose)

    def last(self, method, suffix):
        return [r for r in self.fake.requests if r.method == method and r.url.path.endswith(suffix)][-1]

    async def test_list_templates_asks_for_documents_and_recipients(self):
        templates = await self.client.list_templates("QLD Build _ Single Buyer")
        self.assertEqual(templates[0]["templateId"], "tmpl-qld-single")
        request = self.last("GET", "/templates")
        self.assertEqual((request.url.params["search_text"], request.url.params["include"]),
                         ("QLD Build _ Single Buyer", "documents,recipients"))
        self.assertEqual(request.headers["Authorization"], "Bearer synthetic-token")

    async def test_template_recipients_include_tabs(self):
        data = await self.client.template_recipients("tmpl-qld-single")
        self.assertIn("signers", data)
        self.assertEqual(self.last("GET", "/recipients").url.params["include_tabs"], "true")

    async def test_list_envelopes_filters_on_job_no_and_live_statuses(self):
        await self.client.list_envelopes("2026-04-16", "JobNo=00001")
        params = self.last("GET", "/envelopes").url.params
        self.assertEqual((params["from_date"], params["custom_field"], params["include"]),
                         ("2026-04-16", "JobNo=00001", "custom_fields"))
        self.assertEqual(params["status"], "created,sent,delivered,signed,completed,processing,timedout")

    async def test_create_draft_refuses_any_other_status_without_a_call(self):
        for status in ("sent", "Created", None):
            with self.subTest(status=status), self.assertRaisesRegex(DocuSignError, "only creates drafts"):
                await self.client.create_draft({"status": status, "compositeTemplates": []})
        self.assertEqual(self.fake.requests, [])

    async def test_create_draft_posts_with_merge_roles_on_draft(self):
        body = {"status": "created", "emailSubject": "s", "emailBlurb": "b", "compositeTemplates": [
            {"compositeTemplateId": "1",
             "inlineTemplates": [{"sequence": "1", "recipients": {"signers": []},
                                  "customFields": {"textCustomFields": []}}],
             "document": {"documentId": "1", "name": "B.pdf", "fileExtension": "pdf",
                          "documentBase64": ""}}]}
        out = await self.client.create_draft(body)
        self.assertEqual(out["envelopeId"], "env-synthetic")
        post = self.last("POST", "/envelopes")
        self.assertEqual(post.url.params["merge_roles_on_draft"], "true")
        self.assertEqual(json.loads(post.content)["status"], "created")

    async def test_docusign_errors_carry_code_and_message(self):
        self.fake.create_error = (400, {"errorCode": "INVALID_REQUEST_BODY", "message": "Synthetic."})
        with self.assertRaises(DocuSignError) as cm:
            await self.client.create_draft({"status": "created", "compositeTemplates": []})
        self.assertEqual((cm.exception.status, cm.exception.error_code, cm.exception.detail),
                         (400, "INVALID_REQUEST_BODY", "Synthetic."))

    async def test_a_non_json_error_body_does_not_crash(self):
        self.fake.create_error = (502, "<html><body>Bad gateway</body></html>")
        with self.assertRaises(DocuSignError) as cm:
            await self.client.create_draft({"status": "created", "compositeTemplates": []})
        self.assertEqual((cm.exception.status, cm.exception.error_code), (502, None))

    def test_the_client_has_no_call_that_could_send_or_change_an_envelope(self):
        source = inspect.getsource(client_module)
        self.assertIsNone(re.search(r"\.(put|patch|delete|request|send)\(", source))
        public = {n for n in dir(DocuSignClient) if not n.startswith("_")}
        self.assertEqual(public, {"aclose", "create_draft", "envelope", "envelope_custom_fields",
                                  "envelope_documents", "envelope_recipients", "list_envelopes",
                                  "list_templates", "template_recipients"})
