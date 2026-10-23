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
        self.headers = dict(self.client._client.headers)  # carries api-version, as production requires
        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=transport(self.fake), headers=self.headers)
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

    async def test_only_the_four_intake_activities_by_name(self):
        f = self.fake
        # another workflow template numbers its activities differently: same job, wrong activity
        fixout = f.add_activity(f.job_id, 2, "m) Fixout Complete - OK to Claim")
        await self.assert_blocked(await self.prepare("POST", f"/api/JobActivities/{fixout}/Complete",
                                                     body={"completionDate": "2026-10-15"}),
                                  "not one of the intake activities")
        await self.assert_blocked(await self.prepare("POST", f"/api/JobActivities/{fixout}/Messages",
                                                     form={"Subject": "NEW JOB"}),
                                  "not one of the intake activities")
        eoi = f.add_activity(f.job_id, 11, "a) Receive EOI Approval to Proceed from Marketer")
        out = await self.prepare("POST", f"/api/JobActivities/{eoi}/Complete", body={"completionDate": "2026-10-15"})
        self.assertTrue(out["ok"], out)
        self.assertNotIn("DataBuild", out["confirmation_text"])
        out = await self.prepare("POST", f"/api/JobActivities/{f.act6}/Complete", body={"completionDate": "2026-10-15"})
        self.assertTrue(out["ok"], out)
        self.assertIn("Warning: say yes only if the job has been entered in DataBuild.", out["confirmation_text"])

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
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(drop_writes), headers=self.headers)
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


class BatchTests(GateTestCase):
    """One confirmation per intake stage (15 Oct 2026): fewer interruptions, the same protections."""

    async def batch(self, changes, job_id=None):
        return await server.osc_prepare_changes(self.fake.job_id if job_id is None else job_id, changes)

    def message_file(self, name="request.msg"):
        path = Path(self.folder.name) / name
        path.write_bytes(b"synthetic email")
        return str(path)

    def stage_two(self):
        f = self.fake
        return [
            {"method": "PATCH", "path": f"/api/Jobs/{f.job_id}",
             "body": {"customFieldValues": [{"customFieldID": f.f_sp, "value": "DP 1285148"}]}},
            {"method": "POST", "path": f"/api/Jobs/{f.job_id}/Contacts/{f.other_person_id}",
             "body": {"relationship": "SALES"}},
            {"method": "POST", "path": f"/api/JobActivities/{f.act1}/Complete", "body": {"completionDate": "2026-10-15"}},
            {"method": "POST", "path": f"/api/JobActivities/{f.act2}/Complete", "body": {"completionDate": "2026-10-15"}},
            {"method": "POST", "path": f"/api/Jobs/{f.job_id}/Messages",
             "form": {"Subject": "NEW JOB", "Body": "Contract request email attached.",
                      "Documents[0].description": "NEW JOB"},
             "files": {"Documents[0].file": self.message_file()}},
        ]

    async def test_one_confirmation_lists_every_change_and_one_yes_sends_them_in_order(self):
        out = await self.batch(self.stage_two())
        self.assertTrue(out["ok"], out)
        text = out["confirmation_text"]
        self.assertIn("Job: 26999 - LOT 12 SAMPLE STREET, TESTVILLE NSW 2000", text)
        self.assertIn("4 changes, made in this order:", text)
        self.assertIn('1. Job details\n   - SP No.: now empty, will be "DP 1285148"', text)
        self.assertIn("2. Sam OTHER is added as a contact on this job", text)
        self.assertIn('3. Activity 1 "Initial Contact" is marked complete', text)
        self.assertIn("4. A message is added to the job", text)
        self.assertIn('Already in OnSite Companion, so left out: change 4 (activity): Activity 2 "Follow Up Initial '
                      'Contact" is already complete', text)
        self.assertIn('Reply "yes" to make all 4 changes', text)
        self.assertEqual(self.fake.writes, [], "preparing must never write")
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["state"], "verified")
        self.assertEqual([c["state"] for c in result["changes"]], ["verified"] * 4)
        self.assertIn("all 4 change(s) made and read back", result["result_text"])
        self.assertEqual([w["method"] + " " + w["path"].split("/")[2] for w in self.fake.writes],
                         ["PATCH Jobs", "POST Jobs", "POST JobActivities", "POST Jobs"])
        values = {c["customFieldID"]: c["value"] for c in self.job()["customFieldValues"]}
        self.assertEqual(values[self.fake.f_design], "Hampton 22", "unrelated custom fields are kept")
        self.assertEqual(self.fake.activities[self.fake.act2]["completionDate"], "2026-04-17T00:00:00Z")
        # a used code is dead
        self.assertFalse((await server.osc_confirm_write(out["confirmation_code"], "yes"))["sent"])
        self.assertEqual(len(self.fake.writes), 4)

    async def test_no_or_an_unclear_reply_sends_nothing(self):
        for reply in ("no", "yes but not the contact", ""):
            with self.subTest(reply=reply):
                out = await self.batch(self.stage_two())
                result = await server.osc_confirm_write(out["confirmation_code"], reply)
                self.assertFalse(result["sent"])
        self.assertEqual(self.fake.writes, [])

    async def test_one_change_that_cannot_go_ahead_blocks_the_whole_batch(self):
        changes = self.stage_two() + [{"method": "PATCH", "path": f"/api/Jobs/{self.fake.other_job_id}",
                                       "body": {"startDate": "2026-11-01"}}]
        out = await self.batch(changes)
        self.assertFalse(out["ok"])
        self.assertIsNone(out["confirmation_code"])
        self.assertTrue(out["confirmation_text"].startswith("Nothing was changed in OnSite Companion."))
        self.assertIn("Change 6: The job in the request is not the job named for this change.", out["confirmation_text"])
        protected = await self.batch([{"method": "PATCH", "path": f"/api/Jobs/{self.fake.job_id}",
                                       "body": {"contractValueIncludingGst": 1.0}}])
        self.assertIn("DataBuild only", protected["confirmation_text"])
        twice = await self.batch([{"method": "PATCH", "path": f"/api/Jobs/{self.fake.job_id}",
                                   "body": {"siteAddress": {"suburb": "X"}}},
                                  {"method": "PATCH", "path": f"/api/Jobs/{self.fake.job_id}",
                                   "body": {"startDate": "2026-11-01"}}])
        self.assertIn("Changes 1 and 2 are for the same record", twice["confirmation_text"])
        self.assertEqual(self.fake.writes, [])

    async def test_record_changed_before_the_yes_sends_nothing_and_asks_again(self):
        out = await self.batch(self.stage_two())
        self.job()["siteAddress"]["suburb"] = "EDITED IN OSC"
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertFalse(result["sent"])
        self.assertTrue(result["changed"])
        self.assertIn("4 changes, made in this order", result["confirmation_text"])
        self.assertEqual(self.fake.writes, [])
        self.assertTrue((await server.osc_confirm_write(result["confirmation_code"], "yes"))["ok"])

    async def test_a_later_change_that_moved_stops_the_batch_there(self):
        f = self.fake

        def someone_completes_activity_1(kind, record):
            f.activities[f.act1]["completionDate"] = "2026-10-14T00:00:00Z"
        f.patch_hook = someone_completes_activity_1
        out = await self.batch(self.stage_two())
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(len(result["changes"]), 2, "the job details and the contact went before the stop")
        self.assertIn("no longer matches what was confirmed", result["result_text"])
        self.assertEqual(len(f.writes), 2)
        # the rest is offered again, with the activity now left out
        self.assertIn("1 change, made in this order", result["confirmation_text"])
        self.assertIn("1. A message is added to the job", result["confirmation_text"])
        rest = await server.osc_confirm_write(result["confirmation_code"], "yes")
        self.assertTrue(rest["ok"], rest)
        self.assertEqual(len(f.writes), 3)

    async def test_a_failed_change_stops_the_rest(self):
        self.fake.fail_write = lambda w: 500 if w["path"].endswith("/Complete") else None
        out = await self.batch(self.stage_two())
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "failed")
        self.assertIn("2 of 4 change(s) made and read back", result["result_text"])
        self.assertIn("The other 1 change(s) were not sent.", result["result_text"])
        self.assertFalse(any(w["path"].endswith("/Messages") for w in self.fake.writes))

    async def test_new_intake_in_two_stages_with_references(self):
        f = self.fake
        stage_one = await self.batch([
            {"method": "POST", "path": "/api/Clients",
             "body": {"name": "Jamie NEWBUYER", "postalAddress": {"line1": "5 HOME STREET", "suburb": "TESTVILLE",
                                                                  "state": "NSW", "postcode": "2000"},
                      "workAddress": {}, "workContactDetails": {}}},
            {"method": "POST", "path": "/api/Jobs",
             "body": {"clientID": "{{1.clientID}}", "regionID": f.region_nsw, "workflowTemplateID": f.template,
                      "siteAddress": {"lotNumber": "77", "line1": "NEW ROAD", "suburb": "BOX HILL", "state": "NSW",
                                      "postcode": "2765"}}},
        ], job_id="")
        self.assertTrue(stage_one["ok"], stage_one)
        text = stage_one["confirmation_text"]
        self.assertIn("Job: new job at LOT 77 NEW ROAD, BOX HILL NSW 2765", text)
        self.assertIn('2. A new job is created for client "Jamie NEWBUYER"', text)
        self.assertIn('- Client: "Jamie NEWBUYER"', text)
        done = await server.osc_confirm_write(stage_one["confirmation_code"], "yes")
        self.assertTrue(done["ok"], done)
        self.assertIn("Contract number: 26100.", done["result_text"])
        client_id, job_id = done["created"]["{{1.clientID}}"], done["created"]["{{2.jobID}}"]
        self.assertEqual(f.jobs[job_id]["clientID"], client_id)
        stage_two = await self.batch([
            {"method": "POST", "path": "/api/Persons",
             "body": {"givenName": "Jamie", "surname": "NEWBUYER",
                      "personalContactDetails": {"email": "jamie@example.invalid"},
                      "personalAddress": {}, "postalAddress": {}, "workAddress": {}, "workContactDetails": {}}},
            {"method": "POST", "path": f"/api/Clients/{client_id}/Contacts/{{{{1.personID}}}}",
             "body": {"relationship": "Client Contact", "isPrimaryContact": True}},
            {"method": "POST", "path": f"/api/Clients/{client_id}/Contacts/{f.other_person_id}",
             "body": {"relationship": "SALES"}},
        ], job_id=job_id)
        self.assertTrue(stage_two["ok"], stage_two)
        self.assertIn("2. Jamie NEWBUYER is added as a contact on the job's client", stage_two["confirmation_text"])
        done = await server.osc_confirm_write(stage_two["confirmation_code"], "yes")
        self.assertTrue(done["ok"], done)
        person_id = done["created"]["{{1.personID}}"]
        links = {(c["personID"], c["relationship"]) for c in f.client_contacts if c["clientID"] == client_id}
        self.assertEqual(links, {(person_id, "Client Contact"), (f.other_person_id, "SALES")})

    async def test_a_reference_must_be_an_earlier_create(self):
        f = self.fake
        for changes, words in (
            ([{"method": "POST", "path": "/api/Jobs", "body": {"clientID": "{{2.clientID}}", "regionID": f.region_nsw,
                                                              "siteAddress": {"lotNumber": "1"}}}],
             "not the ID of a record that an earlier change"),
            ([{"method": "PATCH", "path": "/api/Persons/{{1.personID}}", "body": {"surname": "X"}}],
             "not the ID of a record that an earlier change"),
        ):
            with self.subTest(words=words):
                out = await self.batch(changes, job_id="")
                self.assertFalse(out["ok"])
                self.assertIn(words, out["confirmation_text"])
        self.assertEqual(f.writes, [])


class DuplicateCheckTests(GateTestCase):
    async def test_client_names_match_whatever_the_case_or_order(self):
        body = {"postalAddress": {}, "workAddress": {}, "workContactDetails": {}}
        out = await self.prepare("POST", "/api/Clients", job_id="", body={"name": "synthetic, alex", **body})
        self.assertIn('already has 1 client(s) called "synthetic, alex"', out["confirmation_text"])
        out = await self.prepare("POST", "/api/Clients", job_id="", body={"name": "Alex SYNTHETIC", **body})
        self.assertIn('1 client(s) with a similar name ("SYNTHETIC, Alex")', out["confirmation_text"])

    async def test_a_person_with_the_same_email_is_flagged(self):
        out = await self.prepare("POST", "/api/Persons", job_id="", body={
            "givenName": "Alexandra", "surname": "SYNTHETIC-SMITH",
            "personalContactDetails": {"email": "ALEX@example.invalid"},
            "personalAddress": {}, "postalAddress": {}, "workAddress": {}, "workContactDetails": {}})
        self.assertIn('1 person(s) with this email ("Alex SYNTHETIC")', out["confirmation_text"])

    async def test_same_lot_elsewhere_is_a_note_and_every_twin_is_found(self):
        f = self.fake
        for n in range(30):  # lot numbers repeat across estates
            f.add_job(f.other_client_id, f"25{n:03d}", lot="12", line1="FAR ROAD", suburb="FARAWAY", postcode="2999")
        f.add_job(f.other_client_id, "25999", lot="12", line1="SAMPLE STREET", suburb="TESTVILLE", postcode="2000")
        out = await self.prepare("POST", "/api/Jobs", job_id="", body={
            "clientID": f.client_id, "regionID": f.region_nsw,
            "siteAddress": {"lotNumber": "12", "line1": "SAMPLE STREET", "suburb": "TESTVILLE"}})
        text = out["confirmation_text"]
        self.assertIn("Warning: OnSite Companion already has job 25999 - LOT 12", text)
        self.assertIn("Warning: OnSite Companion already has job 26999 - LOT 12", text)
        self.assertIn("lot 12 is also used by 31 job(s) in other suburbs", text)
        self.assertNotIn("FARAWAY", text)


class ReadBackTests(GateTestCase):
    async def test_a_message_whose_attachment_did_not_land_is_not_verified(self):
        path = Path(self.folder.name) / "request.msg"
        path.write_bytes(b"synthetic email")
        self.fake.keep_documents = False
        out = await self.prepare("POST", f"/api/Jobs/{self.fake.job_id}/Messages",
                                 form={"Subject": "NEW JOB"}, files={"Documents[0].file": str(path)})
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "sent_unverified")
        self.assertIn("0 of 1 attachment(s) are there", result["result_text"])

    async def test_osc_get_drops_the_context_link_with_the_host_name(self):
        out = await server.osc_get("/api/Jobs", {"$top": 1}, {"shouldShowMyJobsOnly": False})
        self.assertTrue(out["ok"])
        self.assertNotIn("@odata.context", out["data"])


class StaleCopyTests(GateTestCase):
    newest_job_days_ago = 53  # the retired dev copy: frozen 21 Aug, checked 13 Oct

    async def test_a_frozen_copy_is_never_written(self):
        out = await self.prepare("PATCH", f"/api/Jobs/{self.fake.job_id}", body={"siteAddress": {"suburb": "X"}})
        self.assertFalse(out["ok"])
        self.assertIn("looks like a frozen copy", out["confirmation_text"])
        info = await server.osc_token_info()
        self.assertFalse(info["live_check"]["live"])
        self.assertEqual(self.fake.writes, [])


class ApiVersionTests(GateTestCase):
    async def test_a_call_without_the_api_version_header_is_refused(self):
        bare = httpx.AsyncClient(transport=transport(self.fake))
        try:
            r = await bare.get("https://osc.invalid/api/Jobs")
        finally:
            await bare.aclose()
        self.assertEqual(r.status_code, 400)
        self.assertIn("api-version", r.text)

    async def test_the_client_sends_it_on_every_call(self):
        info = await server.osc_token_info()
        self.assertTrue(info["ok"], info)
        self.assertEqual(info["config"]["api_version"], "7.3")
        self.assertTrue(info["live_check"]["live"])


class ReplyAndConfigTests(unittest.TestCase):
    def test_reply_kinds(self):
        for text in ("yes", "Yes.", "YES!", "yes please", "ok", "Yes, go ahead", "yes ABC123"):
            self.assertEqual(reply_kind(text, "ABC123"), "yes", text)
        for text in ("no", "No.", "cancel", "Cancel!"):
            self.assertEqual(reply_kind(text), "no", text)
        # English only: anything else is not a yes, so nothing is sent
        for text in ("yes but change it", "yesterday", "", "y n", "sounds good but wait", "oui", "si"):
            self.assertEqual(reply_kind(text), "other", text)

    def test_only_production_and_its_own_env_file(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / "production.env"
            env.write_text("OSC_BASE_URL=https://prod.invalid\nOSC_CLIENT_ID=a\nOSC_CLIENT_SECRET=b\n",
                           encoding="utf-8")
            with patch.dict(os.environ, {"OSC_ENV_FILE": str(env)}, clear=True):
                cfg = load_config()
            self.assertEqual(cfg.environment, "production")
            self.assertEqual(cfg.api_version, "7.3")
            self.assertEqual(OSCClient(cfg)._client.headers["api-version"], "7.3")
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
