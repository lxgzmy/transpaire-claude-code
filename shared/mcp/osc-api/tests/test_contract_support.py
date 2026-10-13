"""Synthetic coverage for the read-side helpers; never loads local configuration.

The write path (prepare, confirm, read-back) is covered in test_write_gate.py.
"""
import copy
import importlib
import json
import os
import tempfile
import time
import unittest
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

    def test_the_old_direct_write_tool_is_gone(self):
        self.assertFalse(hasattr(server, "osc_write"),
                         "every write must go through osc_prepare_write and osc_confirm_write")


if __name__ == "__main__":
    unittest.main()
