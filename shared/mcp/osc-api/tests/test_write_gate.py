"""The OnSite Companion write gate, end to end against a stateful fake. Synthetic data only.

Covers the owner's requirements for production writes (13 Oct 2026):
- only the named job, records and fields the person approved are written;
  unrelated data is kept and broad or protected updates are refused;
- a short plain-language confirmation names the job and every change,
  including the value it overwrites;
- cancel, no reply, an unclear reply or an ambiguous target changes nothing;
- if the change or the record differs from what was approved, it is
  confirmed again before anything is sent.
"""
import importlib
import os
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import httpx

from osc_mcp.client import OSCClient
from osc_mcp.config import Config, ConfigError, load_config
from osc_mcp.gate import reply_kind

from fake_osc import FakeOSC, transport

CONFIG = Config("https://osc.invalid", "synthetic", "synthetic", None, None, True, True, 5)
with patch("osc_mcp.config.load_config", return_value=CONFIG):
    server = importlib.import_module("osc_mcp.server")


class GateTestCase(unittest.IsolatedAsyncioTestCase):
    newest_job_days_ago = 1

    async def asyncSetUp(self):
        self.fake = FakeOSC(newest_job_days_ago=self.newest_job_days_ago)
        self.folder = tempfile.TemporaryDirectory()
        self.config = replace(CONFIG, upload_roots=(self.folder.name,))
        self.client = OSCClient(self.config)
        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=transport(self.fake))
        self.client._access_token = "synthetic"
        self.client._token_expiry = time.monotonic() + 3600
        self.patches = [patch.object(server, "_client", self.client), patch.object(server, "_config", self.config),
                        patch.object(server, "_gate", None)]
        for p in self.patches:
            p.start()

    async def asyncTearDown(self):
        for p in reversed(self.patches):
            p.stop()
        await self.client.aclose()
        self.folder.cleanup()

    def use_config(self, **changes):
        cfg = replace(self.config, **changes)
        p = patch.object(server, "_config", cfg)
        p.start()
        self.patches.append(p)
        self.client.config = cfg

    async def prepare(self, method, path, job_id=None, **kw):
        job_id = self.fake.job_id if job_id is None else job_id
        return await server.osc_prepare_write(method, path, job_id, **kw)

    def job(self):
        return self.fake.jobs[self.fake.job_id]


class ConfirmationTests(GateTestCase):
    async def test_confirmation_names_job_and_every_change_with_current_values(self):
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={
            "siteAddress": {"suburb": "BOX HILL", "line2": "", "postcode": "2000"},
            "customFieldValues": [{"customFieldID": self.fake.f_sp, "value": "DP 1285148"}]})
        self.assertTrue(out["ok"], out)
        text = out["confirmation_text"]
        self.assertIn("OnSite Companion (production)", text)
        self.assertIn("Job: 26999 - LOT 12 SAMPLE STREET, TESTVILLE NSW 2000", text)
        self.assertIn('- Site address, suburb: now "TESTVILLE", will be "BOX HILL"', text)
        self.assertIn('- SP No.: now empty, will be "DP 1285148"', text)
        self.assertIn("Nothing else on this job changes.", text)
        self.assertIn('Reply "yes"', text)
        # unchanged values (postcode already 2000, line2 already empty) are neither shown nor sent
        self.assertNotIn("postcode", text)
        self.assertEqual(len(out["changes"]), 2)
        self.assertEqual(len(out["confirmation_code"]), 6)
        self.assertEqual(self.fake.writes, [], "preparing must never write")

    async def test_overwrite_and_clear_are_spelled_out(self):
        out = await self.prepare("PATCH", f"/api/Clients/{self.fake.client_id}",
                                 body={"postalAddress": {"line1": "2 NEW STREET", "suburb": ""}})
        text = out["confirmation_text"]
        self.assertIn('- Postal address, street: now "1 TEST STREET", will be "2 NEW STREET"', text)
        self.assertIn('- Postal address, suburb: now "TESTVILLE", will be cleared', text)

    async def test_yes_sends_only_the_approved_fields_and_keeps_everything_else(self):
        before = self.job()
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={
            "siteAddress": {"suburb": "BOX HILL", "state": "NSW"},
            "customFieldValues": [{"customFieldID": self.fake.f_sp, "value": "DP 1285148"}]})
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["state"], "verified")
        self.assertIn("nothing else on it changed", result["result_text"])
        self.assertEqual(len(self.fake.writes), 1)
        sent = self.fake.writes[0]["body"]
        # smallest request: only the changed site-address field...
        self.assertEqual(sent["siteAddress"], {"suburb": "BOX HILL"})
        # ...and the whole custom-field set, because OSC replaces that collection
        self.assertEqual(len(sent["customFieldValues"]), 3)
        self.assertNotIn("contractValueIncludingGst", sent)
        job = self.job()
        self.assertEqual(job["siteAddress"]["suburb"], "BOX HILL")
        self.assertEqual(job["siteAddress"]["line1"], before["siteAddress"]["line1"])
        self.assertEqual(job["contractValueIncludingGst"], before["contractValueIncludingGst"])
        values = {c["customFieldID"]: c["value"] for c in job["customFieldValues"]}
        self.assertEqual(values[self.fake.f_design], "Hampton 22")
        self.assertEqual(values[self.fake.f_facade], "Coastal")
        self.assertEqual(values[self.fake.f_sp], "DP 1285148")
        other = self.fake.jobs[self.fake.other_job_id]
        self.assertEqual(other["siteAddress"]["suburb"], "OTHERTON")

    async def test_read_back_reports_an_unrelated_field_that_changed(self):
        def fault(kind, record):
            record["siteAddress"]["lotNumber"] = None  # an API side effect nobody approved
        self.fake.patch_hook = fault
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "X"}})
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "sent_unverified")
        self.assertIn("siteAddress.lotNumber", result["verification"]["unexpected_changes"])
        self.assertIn("Check it in OnSite Companion", result["result_text"])

    async def test_shared_client_change_says_which_other_jobs_see_it(self):
        self.fake.add_job(self.fake.client_id, "25042", lot="12", line1="SAMPLE STREET", suburb="TESTVILLE",
                          postcode="2000", days_ago=200)
        out = await self.prepare("PATCH", f"/api/Clients/{self.fake.client_id}", body={"abn": "12 345 678 901"})
        self.assertIn("this client is also on 1 other job(s) (25042)", out["confirmation_text"])

    async def test_new_job_shows_duplicate_lot_and_generated_number(self):
        out = await self.prepare("POST", "/api/Jobs", job_id="", body={
            "clientID": self.fake.client_id, "regionID": self.fake.region_nsw,
            "workflowTemplateID": self.fake.template,
            "siteAddress": {"lotNumber": "12", "line1": "SAMPLE STREET", "suburb": "TESTVILLE", "state": "NSW",
                            "postcode": "2000"}})
        self.assertTrue(out["ok"], out)
        text = out["confirmation_text"]
        self.assertIn('Change: a new job is created for client "SYNTHETIC, Alex"', text)
        self.assertIn('- Region: "SYDNEY01"', text)
        self.assertIn('- Workflow template: "1.1 - Pre Sales Investor v1"', text)
        self.assertIn("- Contract number: generated by OnSite Companion", text)
        self.assertIn("Warning: OnSite Companion already has job 26999 - LOT 12", text)
        result = await server.osc_confirm_write(out["confirmation_code"], "Yes, go ahead")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["verification"]["contract_number"], "26100")

    async def test_message_with_attachment_is_checked_without_opening_the_file(self):
        path = Path(self.folder.name) / "request.msg"
        path.write_bytes(b"synthetic email")
        self.fake.add_message(f"/api/Jobs/{self.fake.job_id}", "NEW JOB")
        with patch.object(Path, "open", side_effect=AssertionError("file opened before approval")):
            out = await self.prepare("POST", f"/api/Jobs/{self.fake.job_id}/Messages",
                                     form={"Subject": "NEW JOB", "Body": "Contract request email attached."},
                                     files={"Documents[0].file": str(path)})
        self.assertTrue(out["ok"], out)
        self.assertIn("- Attachment: request.msg (1 KB)", out["confirmation_text"])
        self.assertIn('already a message called "NEW JOB"', out["confirmation_text"])
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.fake.writes[0]["files"], {"Documents[0].file": ("request.msg", b"synthetic email")})

    async def test_activity_completion_and_question_answer(self):
        out = await self.prepare("POST", f"/api/JobActivities/{self.fake.act1}/Complete",
                                 body={"completionDate": "2026-10-13"})
        self.assertIn('activity 1 "Initial Contact" is marked complete', out["confirmation_text"])
        self.assertIn("- Completion date: now empty, will be 13 Oct 2026", out["confirmation_text"])
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        # PUT replaces the answer: the existing note is carried, not wiped
        out = await self.prepare("PUT", f"/api/JobActivities/{self.fake.act6}/Questions/{self.fake.q2}",
                                 body={"completionAnswerStateID": 1})
        self.assertIn('- Answer: now empty, will be "Completed"', out["confirmation_text"])
        self.assertEqual(out["would_send"]["json"], {"note": "folder made by hand", "completionAnswerStateID": 1})
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)


class NothingChangesTests(GateTestCase):
    async def prepared(self):
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "X"}})
        self.assertTrue(out["ok"], out)
        return out["confirmation_code"]

    async def test_no_cancels(self):
        code = await self.prepared()
        result = await server.osc_confirm_write(code, "no")
        self.assertTrue(result["cancelled"])
        self.assertIn("Nothing was changed", result["result_text"])
        self.assertEqual(self.fake.writes, [])
        again = await server.osc_confirm_write(code, "yes")  # a cancelled code is dead
        self.assertFalse(again["sent"])
        self.assertEqual(self.fake.writes, [])

    async def test_cancel_tool(self):
        code = await self.prepared()
        self.assertTrue((await server.osc_cancel_write(code))["cancelled"])
        self.assertFalse((await server.osc_confirm_write(code, "yes"))["sent"])
        self.assertEqual(self.fake.writes, [])

    async def test_no_reply_means_no_write_and_codes_expire(self):
        code = await self.prepared()
        self.assertEqual(self.fake.writes, [])  # never confirmed: nothing sent
        server._gate.pending[code].created -= 31 * 60  # past the 30-minute life of a code
        result = await server.osc_confirm_write(code, "yes")
        self.assertFalse(result["sent"])
        self.assertIn("not valid any more", result["result_text"])
        self.assertEqual(self.fake.writes, [])

    async def test_a_reply_that_asks_for_something_else_is_not_a_yes(self):
        for reply in ("yes but make it BOX HILL", "maybe", "", "sure, change the lot too"):
            with self.subTest(reply=reply):
                code = await self.prepared()
                result = await server.osc_confirm_write(code, reply)
                self.assertFalse(result["sent"])
                self.assertIn("not a plain yes", result["result_text"])
        self.assertEqual(self.fake.writes, [])

    async def test_a_code_is_used_once(self):
        code = await self.prepared()
        self.assertTrue((await server.osc_confirm_write(code, "yes"))["ok"])
        second = await server.osc_confirm_write(code, "yes")
        self.assertFalse(second["sent"])
        self.assertEqual(len(self.fake.writes), 1)

    async def test_record_changed_after_confirmation_asks_again(self):
        code = await self.prepared()
        self.job()["siteAddress"]["suburb"] = "EDITED IN OSC"  # someone edits the job meanwhile
        result = await server.osc_confirm_write(code, "yes")
        self.assertFalse(result["sent"])
        self.assertTrue(result["changed"])
        self.assertIn('now "EDITED IN OSC", will be "X"', result["confirmation_text"])
        self.assertNotEqual(result["confirmation_code"], code)
        self.assertEqual(self.fake.writes, [])
        self.assertFalse((await server.osc_confirm_write(code, "yes"))["sent"])  # the old code is gone
        done = await server.osc_confirm_write(result["confirmation_code"], "yes")
        self.assertTrue(done["ok"], done)

    async def test_a_changed_request_replaces_the_earlier_code(self):
        first = await self.prepared()
        second = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "Y"}})
        self.assertFalse((await server.osc_confirm_write(first, "yes"))["sent"])
        self.assertEqual(self.fake.writes, [])
        self.assertTrue((await server.osc_confirm_write(second["confirmation_code"], "yes"))["ok"])
        self.assertEqual(self.job()["siteAddress"]["suburb"], "Y")

    async def test_writes_switched_off_shows_but_never_sends(self):
        self.use_config(enable_writes=False)
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "X"}})
        self.assertFalse(out["ok"])
        self.assertIsNone(out["confirmation_code"])
        self.assertIn("now \"TESTVILLE\", will be \"X\"", out["confirmation_text"])
        self.assertIn("switched off", out["error"])
        self.assertEqual(self.fake.writes, [])

    async def test_values_already_in_osc_are_not_a_change(self):
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "TESTVILLE"}})
        self.assertFalse(out["ok"])
        self.assertIn("nothing to change", out["confirmation_text"])


class RefusedTargetTests(GateTestCase):
    async def assert_blocked(self, out, words):
        self.assertFalse(out["ok"], out)
        self.assertIsNone(out["confirmation_code"])
        self.assertTrue(out["confirmation_text"].startswith("Nothing was changed in OnSite Companion."))
        self.assertIn(words, out["confirmation_text"])
        self.assertEqual(self.fake.writes, [])

    async def test_routes_outside_the_intake_are_refused(self):
        for method, path in (("DELETE", f"/api/Persons/{self.fake.person_id}"),
                             ("POST", f"/api/JobActivities/{self.fake.act1}/EmailWorkReleases"),
                             ("PATCH", f"/api/Jobs/{self.fake.job_id}/Contract"),
                             ("POST", f"/api/Jobs/{self.fake.job_id}/AddWorkflowTemplate"),
                             ("GET", "/api/Jobs")):
            with self.subTest(method=method, path=path):
                await self.assert_blocked(await self.prepare(method, path, body={"x": 1}),
                                          "not one of the approved")

    async def test_job_must_be_named_and_real(self):
        path = f"/api/Jobs/{self.fake.job_id}"
        await self.assert_blocked(await self.prepare("PATCH", path, job_id="", body={"startDate": "2026-11-01"}),
                                  "Say which job")
        await self.assert_blocked(await self.prepare("PATCH", path, job_id="26999", body={"startDate": "2026-11-01"}),
                                  "Say which job")
        missing = "00000000-0000-0000-0000-000000000000"
        await self.assert_blocked(await self.prepare("PATCH", f"/api/Jobs/{missing}", job_id=missing,
                                                     body={"startDate": "2026-11-01"}), "No job with that ID")

    async def test_a_record_on_another_job_is_refused(self):
        f = self.fake
        cases = [
            ("PATCH", f"/api/Jobs/{f.other_job_id}", {"startDate": "2026-11-01"}, "not the job named"),
            ("PATCH", f"/api/Clients/{f.other_client_id}", {"abn": "1"}, "not the client on job 26999"),
            ("PATCH", f"/api/Persons/{f.other_person_id}", {"surname": "X"}, "not a contact on job 26999"),
            ("POST", f"/api/JobActivities/{f.other_act}/Complete", {"completionDate": "2026-10-13"},
             "belongs to a different job"),
            ("POST", f"/api/Clients/{f.other_client_id}/Contacts/{f.person_id}", {"relationship": "PURCHASER"},
             "not the client on job 26999"),
        ]
        for method, path, body, words in cases:
            with self.subTest(path=path):
                await self.assert_blocked(await self.prepare(method, path, body=body), words)

    async def test_ids_must_be_single_records(self):
        await self.assert_blocked(await self.prepare("PATCH", "/api/Jobs/26999", body={"startDate": "2026-11-01"}),
                                  "must be a single record ID")

    async def test_duplicate_rows_make_the_target_ambiguous(self):
        twin = dict(self.fake.persons[self.fake.person_id])
        self.fake.persons["twin"] = twin  # same personID twice
        await self.assert_blocked(await self.prepare("PATCH", f"/api/Persons/{self.fake.person_id}",
                                                     body={"middleNames": "J"}), "ambiguous")

    async def test_protected_and_unknown_fields(self):
        path = f"/api/Jobs/{self.fake.job_id}"
        await self.assert_blocked(await self.prepare("PATCH", path, body={"contractValueIncludingGst": 1.0}),
                                  "DataBuild only")
        await self.assert_blocked(await self.prepare("PATCH", path, body={"contractNumber": "26999"}),
                                  "never changed through Claude")
        await self.assert_blocked(await self.prepare("PATCH", path, body={"regionID": self.fake.region_qld}),
                                  "region is set when the job is created")
        await self.assert_blocked(await self.prepare("PATCH", path, body={"siteAddress": {"colour": "red"}}),
                                  "no field called 'colour'")
        await self.assert_blocked(await self.prepare("PATCH", path, body={"customFieldValues": [
            {"customFieldID": "11111111-1111-1111-1111-111111111111", "value": "x"}]}), "not one of this")
        await self.assert_blocked(await self.prepare("POST", "/api/Jobs", job_id="", body={
            "clientID": self.fake.client_id, "regionID": self.fake.region_nsw, "contractNumber": "26999",
            "siteAddress": {"lotNumber": "1"}}), "generates the contract number")

    async def test_completed_activity_and_existing_link_are_not_redone(self):
        f = self.fake
        await self.assert_blocked(await self.prepare("POST", f"/api/JobActivities/{f.act2}/Complete",
                                                     body={"completionDate": "2026-10-13"}), "already complete")
        await self.assert_blocked(await self.prepare("POST", f"/api/Clients/{f.client_id}/Contacts/{f.person_id}",
                                                     body={"relationship": "PURCHASER"}), "already a contact")


class SendFailureTests(GateTestCase):
    async def prepared_message(self):
        path = Path(self.folder.name) / "request.eml"
        path.write_bytes(b"Subject: Synthetic\r\n\r\n\x00attachment\xff")
        out = await self.prepare("POST", f"/api/Jobs/{self.fake.job_id}/Messages",
                                 form={"Subject": "NEW JOB", "Documents[0].description": "NEW JOB"},
                                 files={"Documents[0].file": str(path)})
        self.assertTrue(out["ok"], out)
        return out["confirmation_code"], path

    async def test_attachment_bytes_arrive_unchanged(self):
        code, path = await self.prepared_message()
        result = await server.osc_confirm_write(code, "yes")
        self.assertTrue(result["ok"], result)
        write = self.fake.writes[0]
        self.assertEqual(write["form"], {"Subject": "NEW JOB", "Documents[0].description": "NEW JOB"})
        self.assertEqual(write["files"]["Documents[0].file"], ("request.eml", path.read_bytes()))

    async def test_unreadable_attachment_sends_nothing(self):
        code, _ = await self.prepared_message()
        with patch.object(Path, "open", side_effect=PermissionError("sensitive path")):
            result = await server.osc_confirm_write(code, "yes")
        self.assertFalse(result["sent"])
        self.assertNotIn("sensitive path", result["result_text"])
        self.assertEqual(self.fake.writes, [])

    async def test_dropped_connection_is_reported_as_unknown_and_closes_the_file(self):
        code, _ = await self.prepared_message()
        reads = transport(self.fake).handler
        opened, actual_open = [], Path.open

        async def drop_writes(request):
            if request.method != "GET":
                raise httpx.ReadTimeout("sensitive host", request=request)
            return await reads(request)

        def capture(p, *args, **kwargs):
            stream = actual_open(p, *args, **kwargs)
            opened.append(stream)
            return stream

        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(drop_writes))
        with patch.object(Path, "open", capture):
            result = await server.osc_confirm_write(code, "yes")
        self.assertEqual(result["state"], "sent_unverified")
        self.assertIn("not known whether", result["result_text"])
        self.assertNotIn("sensitive host", result["result_text"])
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].closed)

    async def test_attachment_outside_the_upload_roots_is_refused(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            path = Path(elsewhere) / "secret.eml"
            path.write_bytes(b"synthetic")
            out = await self.prepare("POST", f"/api/Jobs/{self.fake.job_id}/Messages",
                                     form={"Subject": "NEW JOB"}, files={"Documents[0].file": str(path)})
        self.assertFalse(out["ok"])
        self.assertIn("outside the allowed upload roots", out["confirmation_text"])
        self.assertEqual(self.fake.writes, [])


class StaleCopyTests(GateTestCase):
    newest_job_days_ago = 53  # the retired dev copy: frozen 21 Aug, checked 13 Oct

    async def test_a_frozen_copy_is_never_written(self):
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "X"}})
        self.assertFalse(out["ok"])
        self.assertIn("looks like a frozen copy", out["confirmation_text"])
        info = await server.osc_token_info()
        self.assertFalse(info["live_check"]["live"])
        self.assertEqual(self.fake.writes, [])


class ReplyAndConfigTests(unittest.TestCase):
    def test_reply_kinds(self):
        for text in ("yes", "Yes.", "YES!", "yes please", "ok", "Yes, go ahead", "是", "确认", "yes ABC123"):
            self.assertEqual(reply_kind(text, "ABC123"), "yes", text)
        for text in ("no", "No.", "cancel", "不要", "取消"):
            self.assertEqual(reply_kind(text), "no", text)
        for text in ("yes but change it", "yesterday", "", "y n", "sounds good but wait"):
            self.assertEqual(reply_kind(text), "other", text)

    def test_only_production_and_its_own_env_file(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / "production.env"
            env.write_text("OSC_BASE_URL=https://prod.invalid\nOSC_CLIENT_ID=a\nOSC_CLIENT_SECRET=b\n",
                           encoding="utf-8")
            with patch.dict(os.environ, {"OSC_ENV_FILE": str(env)}, clear=True):
                cfg = load_config()
            self.assertEqual(cfg.environment, "production")
            self.assertTrue(cfg.verify_tls, "TLS is verified unless the env file says otherwise")
            self.assertFalse(cfg.enable_writes)
            self.assertNotIn("prod.invalid", str(cfg.redacted()), "no host name in what the tool shows")
            with patch.dict(os.environ, {"OSC_ENV_FILE": str(env), "OSC_ENVIRONMENT": "dev"}, clear=True):
                with self.assertRaises(ConfigError):
                    load_config()
        with patch.dict(os.environ, {"OSC_ENV_FILE": os.path.join(tempfile.gettempdir(), "absent.env")},
                        clear=True):
            with self.assertRaises(ConfigError) as caught:
                load_config()
            self.assertIn("production.env", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
