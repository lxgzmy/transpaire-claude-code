"""Synthetic contract-workflow coverage; never load local configuration."""
import copy
import importlib
import json
import os
import tempfile
import time
import unittest
from dataclasses import replace
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from unittest.mock import patch

import httpx

from osc_mcp.client import OSCClient, _explain_status
from osc_mcp.config import Config, ConfigError, load_config
from osc_mcp.spec import SpecView, find_operation

CONFIG = Config("https://osc.invalid", "synthetic", "synthetic", "https://osc.invalid/spec",
                None, True, True, 5)
with patch("osc_mcp.config.load_config", return_value=CONFIG):
    server = importlib.import_module("osc_mcp.server")


def fixture():
    return {
        "paths": {
            "/api/Jobs/{JobID}/Messages": {
                "parameters": [{"$ref": "#/components/parameters/JobID"}],
                "post": {
                    "requestBody": {"$ref": "#/components/requestBodies/Message"},
                    "responses": {"201": {"$ref": "#/components/responses/Created"}},
                },
            },
            "/api/Jobs": {"post": {
                "requestBody": {"content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Job"}}}},
                "responses": {"201": {"description": "Created"}},
            }},
        },
        "components": {
            "parameters": {"JobID": {"name": "JobID", "in": "path", "required": True,
                "description": "Job identifier", "schema": {"type": "string", "format": "uuid"}}},
            "requestBodies": {"Message": {"required": True, "content": {
                "multipart/form-data": {"schema": {"type": "object", "properties": {
                    "Subject": {"type": "string"}, "Documents": {"type": "array", "items": {
                        "$ref": "#/components/schemas/Document"}}}}}}}},
            "responses": {"Created": {"description": "Created", "headers": {
                "Location": {"schema": {"type": "string"}}}, "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Job"}}}}},
            "schemas": {
                "Document": {"type": "object", "required": ["description", "file"], "properties": {
                    "description": {"type": "string"}, "file": {"type": "string", "format": "binary"}}},
                "Job": {"type": "object", "required": ["address", "contact"], "properties": {
                    "address": {"$ref": "#/components/schemas/Address"},
                    "contact": {"$ref": "#/components/schemas/Contact"}}},
                "Address": {"required": ["suburb"], "properties": {"suburb": {"type": "string"},
                    "state": {"type": "string", "enum": ["NSW", "QLD"]}}},
                "Contact": {"properties": {"manager": {"$ref": "#/components/schemas/Contact"},
                    "missing": {"$ref": "#/components/schemas/Missing"},
                    "external": {"$ref": "https://external.invalid/schema"}}},
                "Unused": {"type": "string"},
            },
        },
    }


class ContractSupportTests(unittest.IsolatedAsyncioTestCase):
    def test_unsupported_media_type_explains_json_and_multipart(self):
        message = _explain_status(415)
        self.assertIn("osc_describe_endpoint", message)
        self.assertIn("form/files", message)

    async def asyncSetUp(self):
        self.requests = []

        async def handle(request):
            self.requests.append(request)
            await request.aread()
            return httpx.Response(201, json={"messageID": "synthetic"})

        self.client = OSCClient(CONFIG)
        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        self.client._access_token = "synthetic"
        self.client._token_expiry = time.monotonic() + 3600
        self.client._spec = fixture()
        self.patches = [patch.object(server, "_client", self.client), patch.object(server, "_config", CONFIG)]
        for p in self.patches:
            p.start()

    async def asyncTearDown(self):
        for p in reversed(self.patches):
            p.stop()
        await self.client.aclose()

    @staticmethod
    def roots(*folders, **overrides):
        """Allow uploads from the given folders (and override other Config fields)."""
        return patch.object(server, "_config", replace(CONFIG, upload_roots=tuple(folders), **overrides))

    def test_find_operation_prefers_literal_then_fewer_parameters(self):
        spec = {"paths": {
            "/api/Jobs/{JobID}/Messages": {"post": {"summary": "by job"}},
            "/api/{Kind}/{ID}/Messages": {"post": {"summary": "generic"}},
            "/api/Jobs/literal/Messages": {"post": {"summary": "literal"}},
        }}
        view = SpecView(spec)
        self.assertEqual(find_operation(spec, view, "/api/Jobs/literal/Messages", "POST"),
                         ("/api/Jobs/literal/Messages", {"summary": "literal"}))
        self.assertEqual(find_operation(spec, view, "/api/Jobs/abc/Messages", "POST"),
                         ("/api/Jobs/{JobID}/Messages", {"summary": "by job"}))
        self.assertEqual(find_operation(spec, view, "/api/Jobs/abc/Messages", "DELETE"),
                         ("/api/Jobs/{JobID}/Messages", {}))
        self.assertEqual(find_operation(spec, view, "/api/Jobs/abc/Messages/extra", "POST"), (None, {}))

    def test_upload_roots_come_from_env_or_default_to_runtime(self):
        base = {"OSC_BASE_URL": "https://osc.invalid", "OSC_CLIENT_ID": "x", "OSC_CLIENT_SECRET": "y",
                "OSC_ENV_FILE": os.path.join(tempfile.gettempdir(), "no-such-osc.env")}
        with patch.dict(os.environ, {**base, "OSC_UPLOAD_ROOTS": ""}, clear=True):
            cfg = load_config()
        self.assertEqual(len(cfg.upload_roots), 1)
        self.assertTrue(os.path.isabs(cfg.upload_roots[0]))
        self.assertEqual(os.path.basename(cfg.upload_roots[0]), "runtime")
        self.assertEqual(cfg.redacted()["upload_roots"], 1)
        a, b = tempfile.gettempdir(), os.path.dirname(tempfile.gettempdir())
        with patch.dict(os.environ, {**base, "OSC_UPLOAD_ROOTS": f"{a}; {b} ;"}, clear=True):
            self.assertEqual(load_config().upload_roots, (a, b))
        with patch.dict(os.environ, {**base, "OSC_UPLOAD_ROOTS": "relative/dir"}, clear=True):
            with self.assertRaises(ConfigError):
                load_config()

    async def test_description_exposes_transitive_required_fields_and_cycles(self):
        original = copy.deepcopy(self.client._spec)
        result = await server.osc_describe_endpoint("/api/Jobs/{JobID}/Messages", "POST")
        op = result["operations"]["POST"]
        self.assertIn("request_body", op)
        self.assertTrue(op["request_body"]["required"])
        self.assertEqual(op["request_body_content_types"], ["multipart/form-data"])
        self.assertEqual(op["parameters"][0]["schema"]["format"], "uuid")
        self.assertEqual(op["parameters"][0]["description"], "Job identifier")
        self.assertEqual(op["responses"], ["201"])
        self.assertIn("Location", op["response_details"]["201"]["headers"])
        refs = result["referenced_definitions"]
        self.assertEqual(refs["#/components/schemas/Job"]["required"], ["address", "contact"])
        self.assertEqual(refs["#/components/schemas/Address"]["properties"]["state"]["enum"], ["NSW", "QLD"])
        self.assertEqual(refs["#/components/schemas/Document"]["required"], ["description", "file"])
        self.assertNotIn("#/components/schemas/Unused", refs)
        self.assertEqual({x["reason"] for x in result["unresolved_references"]}, {"missing", "external"})
        self.assertEqual(self.requests, [])
        self.assertEqual(original, self.client._spec)
        json.dumps(result)  # Cyclic references must remain serialisable.

    async def test_parameter_override_and_escaped_json_pointer(self):
        path = self.client._spec["paths"]["/api/Jobs/{JobID}/Messages"]
        path["post"]["parameters"] = [{"name": "JobID", "in": "path", "required": True,
            "schema": {"$ref": "#/components/schemas/ID~1kind~0"}}]
        self.client._spec["components"]["schemas"]["ID/kind~"] = {"type": "string", "enum": ["a"]}
        result = await server.osc_describe_endpoint("/api/Jobs/{JobID}/Messages")
        self.assertIn("referenced_definitions", result)
        self.assertEqual(len(result["operations"]["POST"]["parameters"]), 1)
        self.assertEqual(result["referenced_definitions"]["#/components/schemas/ID~1kind~0"]["enum"], ["a"])

    async def test_method_filter_does_not_collect_unrelated_schemas(self):
        self.client._spec["paths"]["/api/Jobs"]["get"] = {
            "responses": {"200": {"$ref": "#/components/responses/UnrelatedMissing"}}}
        result = await server.osc_describe_endpoint("/api/Jobs", "POST")
        self.assertNotIn("#/components/responses/UnrelatedMissing",
                         {r["ref"] for r in result["unresolved_references"]})

    async def test_gates_never_open_files_or_send(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.eml"
            path.write_bytes(b"synthetic")
            for enabled, confirm in [(False, False), (False, True), (True, False)]:
                with self.subTest(enabled=enabled, confirm=confirm), self.roots(
                    folder, enable_writes=enabled
                ), patch.object(Path, "open", side_effect=AssertionError("File opened before approval")):
                    result = await server.osc_write("POST", "/api/Jobs/id/Messages", confirm=confirm,
                        form={"Subject": "NEW JOB"}, files={"Documents[0].file": str(path)})
                    self.assertEqual(result["would_send"]["files"], {"Documents[0].file": str(path)})
                    self.assertEqual(result["ok"], enabled)
                    # the preview ran the send's checks: route is multipart, file found, size known
                    self.assertTrue(all(c["ok"] for c in result["checks"]))
                    self.assertEqual(result["checks"][0]["route"], "/api/Jobs/{JobID}/Messages")
                    self.assertEqual(result["checks"][1]["bytes"], 9)
        self.assertEqual(self.requests, [])

    async def test_preview_reports_problems_instead_of_promising_success(self):
        with tempfile.TemporaryDirectory() as folder, self.roots(folder), patch.object(
            Path, "open", side_effect=AssertionError("File opened during preview")
        ):
            result = await server.osc_write("POST", "/api/Jobs", confirm=False,
                form={"Subject": "NEW JOB"}, files={"Documents[0].file": str(Path(folder) / "missing.eml")})
        self.assertFalse(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertIn("problems", result["error"])
        problems = {c["problem"] for c in result["checks"] if not c["ok"]}
        self.assertTrue(any("multipart/form-data" in p for p in problems))
        self.assertTrue(any("existing regular file" in p for p in problems))
        self.assertEqual(self.requests, [])

    async def test_upload_outside_allowed_roots_is_refused(self):
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as elsewhere:
            path = Path(elsewhere) / "secret.eml"
            path.write_bytes(b"synthetic")
            with self.roots(allowed):
                result = await server.osc_write("POST", "/api/Jobs/id/Messages", confirm=True,
                    files={"Documents[0].file": str(path)})
            self.assertFalse(result["ok"])
            self.assertEqual(result["checks"][1]["problem"], "outside the allowed upload roots")
            with self.roots():  # nothing configured at all
                result = await server.osc_write("POST", "/api/Jobs/id/Messages", confirm=True,
                    files={"Documents[0].file": str(path)})
            self.assertFalse(result["ok"])
            self.assertIn("no upload roots", result["checks"][1]["problem"])
        self.assertEqual(self.requests, [])

    async def test_multipart_encodes_field_names_bytes_and_filename(self):
        with tempfile.TemporaryDirectory() as folder, self.roots(folder):
            path = Path(folder) / "request.eml"
            path.write_bytes(b"Subject: Synthetic\r\n\r\n\x00attachment\xff")
            result = await server.osc_write("POST", "/api/Jobs/id/Messages", confirm=True,
                form={"Subject": "NEW JOB", "Documents[0].description": "NEW JOB"},
                files={"Documents[0].file": str(path)}, query={"sample": "1"})
        self.assertTrue(result["ok"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.url.params["sample"], "1")
        self.assertTrue(request.headers["content-type"].startswith("multipart/form-data; boundary="))
        message = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.content)
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        self.assertEqual(parts["Subject"].get_payload(decode=True), b"NEW JOB")
        self.assertEqual(parts["Documents[0].description"].get_payload(decode=True), b"NEW JOB")
        self.assertEqual(parts["Documents[0].file"].get_filename(), "request.eml")
        # message/rfc822 is parsed as a nested Message, so decoded payload is
        # None for .eml. Inspect the raw MIME part to prove binary preservation.
        boundary = message.get_boundary().encode()
        file_part = next(part for part in request.content.split(b"--" + boundary)
                         if b'name="Documents[0].file"' in part)
        self.assertEqual(file_part.split(b"\r\n\r\n", 1)[1],
                         b"Subject: Synthetic\r\n\r\n\x00attachment\xff\r\n")

    async def test_invalid_multipart_rejected_before_business_request(self):
        with tempfile.TemporaryDirectory() as folder, self.roots(folder):
            cases = [
                {"body": {}, "form": {"Subject": "x"}},
                {"files": {"file": "relative.eml"}},
                {"files": {"file": str(Path(folder) / "missing.eml")}},
                {"files": {"file": folder}},
                {"path": "/api/Jobs", "form": {"Subject": "x"}},
                {"path": "/api/Unknown", "form": {"Subject": "x"}},
                {"method": "DELETE", "form": {"Subject": "x"}},
                {"form": {}, "files": {}},
            ]
            for case in cases:
                with self.subTest(case=case):
                    args = {"method": "POST", "path": "/api/Jobs/id/Messages", "confirm": True, **case}
                    result = await server.osc_write(**args)
                    self.assertFalse(result["ok"])
                    self.assertEqual(self.requests, [])

    async def test_json_write_keeps_existing_behaviour(self):
        result = await server.osc_write("POST", "/api/Jobs", body={"name": "Synthetic"}, confirm=True)
        self.assertTrue(result["ok"])
        self.assertEqual(json.loads(self.requests[0].content), {"name": "Synthetic"})

    async def test_form_only_is_still_multipart(self):
        result = await server.osc_write("POST", "/api/Jobs/id/Messages",
                                        form={"Subject": "NEW JOB"}, confirm=True)
        self.assertTrue(result["ok"])
        self.assertTrue(self.requests[0].headers["content-type"].startswith("multipart/form-data;"))
        self.assertIn(b'name="Subject"\r\n\r\nNEW JOB', self.requests[0].content)

    async def test_unreadable_file_is_not_sent(self):
        with tempfile.TemporaryDirectory() as folder, self.roots(folder):
            path = Path(folder) / "request.eml"
            path.write_bytes(b"synthetic")
            with patch.object(Path, "open", side_effect=PermissionError("sensitive path")):
                result = await server.osc_write("POST", "/api/Jobs/id/Messages",
                    files={"Documents[0].file": str(path)}, confirm=True)
        self.assertFalse(result["ok"])
        self.assertNotIn("sensitive path", result["error"])
        self.assertEqual(self.requests, [])

    async def test_transport_failure_requires_reconciliation_and_closes_files(self):
        opened = []
        actual_open = Path.open

        def capture(path, *args, **kwargs):
            stream = actual_open(path, *args, **kwargs)
            opened.append(stream)
            return stream

        async def fail(request):
            self.requests.append(request)
            raise httpx.ReadTimeout("sensitive host", request=request)

        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
        with tempfile.TemporaryDirectory() as folder, self.roots(folder):
            path = Path(folder) / "request.eml"
            path.write_bytes(b"synthetic")
            with patch.object(Path, "open", capture):
                result = await server.osc_write("POST", "/api/Jobs/id/Messages",
                    files={"Documents[0].file": str(path)}, confirm=True)
        self.assertFalse(result["ok"])
        self.assertIn("uncertain", result["error"])
        self.assertNotIn("sensitive host", result["error"])
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].closed)


if __name__ == "__main__":
    unittest.main()
