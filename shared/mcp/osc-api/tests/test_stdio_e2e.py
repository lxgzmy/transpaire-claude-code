"""End to end over MCP stdio: the server is started the way Claude Code starts it
(python -m osc_mcp.server, OSC_ENVIRONMENT=production) and pointed at the fake
OSC on a local port through a throwaway env file. Synthetic data only; nothing
leaves this machine.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fake_osc import FakeOSC, serve

PACKAGE = Path(__file__).resolve().parent.parent


def payload(result) -> dict:
    text = result.content[0].text if result.content else ""
    try:
        return json.loads(text)
    except ValueError:
        raise AssertionError(f"tool returned non-JSON (isError={result.isError}): {text[:500]}") from None


class StdioEndToEnd(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeOSC()
        self.http, base_url = serve(self.fake)
        self.folder = tempfile.TemporaryDirectory()
        env_file = Path(self.folder.name) / "production.env"
        env_file.write_text(f"OSC_BASE_URL={base_url}\nOSC_CLIENT_ID=synthetic\nOSC_CLIENT_SECRET=synthetic\n"
                            f"OSC_UPLOAD_ROOTS={self.folder.name}\n", encoding="utf-8")
        # The write log goes to the throwaway folder too: left to its default it
        # lands in the checkout's real runtime\contract-admin\logs\osc-writes.jsonl,
        # labelled production, beside the record of real changes.
        self.params = StdioServerParameters(
            command=sys.executable, args=["-m", "osc_mcp.server"],
            env={**os.environ, "PYTHONPATH": str(PACKAGE), "OSC_ENV_FILE": str(env_file),
                 "OSC_ENVIRONMENT": "production", "OSC_ENABLE_WRITES": "true", "OSC_TIMEOUT": "20",
                 "OSC_LOG_ROOT": self.folder.name})

    async def asyncTearDown(self):
        self.http.shutdown()
        self.folder.cleanup()

    async def test_prepare_confirm_and_cancel_over_stdio(self):
        f = self.fake
        async with stdio_client(self.params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                self.assertEqual(names, {"osc_token_info", "osc_list_endpoints", "osc_describe_endpoint",
                                         "osc_get", "osc_prepare_write", "osc_prepare_changes",
                                         "osc_confirm_write", "osc_cancel_write"})

                info = payload(await session.call_tool("osc_token_info", {}))
                self.assertEqual(info["config"]["environment"], "production")
                self.assertTrue(info["live_check"]["live"])
                self.assertNotIn("127.0.0.1", json.dumps(info), "the host never appears in tool output")

                prep = payload(await session.call_tool("osc_prepare_write", {
                    "method": "PATCH", "path": f"/api/Jobs/{f.job_id}", "job_id": f.job_id,
                    "body": {"siteAddress": {"suburb": "BOX HILL"}}}))
                self.assertTrue(prep["ok"], prep)
                self.assertIn('now "TESTVILLE", will be "BOX HILL"', prep["confirmation_text"])
                self.assertEqual(f.writes, [])

                # the person says no: nothing is sent
                no = payload(await session.call_tool("osc_confirm_write", {
                    "confirmation_code": prep["confirmation_code"], "user_reply": "no"}))
                self.assertTrue(no["cancelled"])
                self.assertEqual(f.writes, [])

                # prepared again, then discarded with the cancel tool
                prep = payload(await session.call_tool("osc_prepare_write", {
                    "method": "PATCH", "path": f"/api/Jobs/{f.job_id}", "job_id": f.job_id,
                    "body": {"siteAddress": {"suburb": "BOX HILL"}}}))
                cancel = payload(await session.call_tool("osc_cancel_write",
                                                         {"confirmation_code": prep["confirmation_code"]}))
                self.assertTrue(cancel["cancelled"])
                self.assertEqual(f.writes, [])

                # prepared once more and confirmed with a plain yes
                prep = payload(await session.call_tool("osc_prepare_write", {
                    "method": "PATCH", "path": f"/api/Jobs/{f.job_id}", "job_id": f.job_id,
                    "body": {"siteAddress": {"suburb": "BOX HILL"}}}))
                done = payload(await session.call_tool("osc_confirm_write", {
                    "confirmation_code": prep["confirmation_code"], "user_reply": "yes"}))
                self.assertEqual(done["state"], "verified", done)
                self.assertEqual(len(f.writes), 1)
                self.assertEqual(f.writes[0]["body"], {"siteAddress": {"suburb": "BOX HILL"}})
                self.assertEqual(f.jobs[f.job_id]["siteAddress"]["line1"], "SAMPLE STREET")

                # a stage of the intake: one confirmation, one yes, every change read back
                listed = payload(await session.call_tool("osc_get", {
                    "path": "/api/Jobs", "query": {"$top": 5}, "odata_filter": {"shouldShowMyJobsOnly": False}}))
                self.assertNotIn("fake-osc-host", json.dumps(listed), "the OData context link is dropped")
                batch = payload(await session.call_tool("osc_prepare_changes", {"job_id": f.job_id, "changes": [
                    {"method": "POST", "path": f"/api/JobActivities/{f.act1}/Complete",
                     "body": {"completionDate": "2026-10-15"}},
                    {"method": "POST", "path": f"/api/JobActivities/{f.act2}/Complete",
                     "body": {"completionDate": "2026-10-15"}}]}))
                self.assertTrue(batch["ok"], batch)
                self.assertIn("1 change, made in this order", batch["confirmation_text"])
                self.assertIn("left out", batch["confirmation_text"])  # activity 2 was already complete
                self.assertEqual(len(f.writes), 1)
                done = payload(await session.call_tool("osc_confirm_write", {
                    "confirmation_code": batch["confirmation_code"], "user_reply": "yes"}))
                self.assertEqual(done["state"], "verified", done)
                self.assertEqual(len(f.writes), 2)

                # a route outside the intake is refused over the wire too
                refused = payload(await session.call_tool("osc_prepare_write", {
                    "method": "DELETE", "path": f"/api/Persons/{f.person_id}", "job_id": f.job_id,
                    "body": {"x": 1}}))
                self.assertFalse(refused["ok"])
                self.assertEqual(len(f.writes), 2)

        # every answered confirmation (no, yes, the batch's yes) is logged in the throwaway folder
        log = Path(self.folder.name) / "contract-admin" / "logs" / "osc-writes.jsonl"
        replies = [json.loads(line)["reply"] for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(replies, ["no", "yes", "yes"])


if __name__ == "__main__":
    unittest.main()
