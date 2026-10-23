"""The Permit Officer's OnSite Companion changes through the same gate. Synthetic data only.

Covers the design signed off on 23 Oct 2026:
- the Permit Officer workflow ticks only its ten building-approval activities, by name, and adds
  messages; it cannot make an intake change, and the intake cannot tick its activities;
- NSW jobs in pre-construction (or kept for testing) only;
- hard stops only where the change would be wrong: the step before not done, a date in the future
  (Sydney time), before the job or before the step before, completion questions, two open activities
  of the same name;
- everything borderline is one line inside the same confirmation, never a second stop;
- a tick, its message and the email attached to it go under one confirmation and one yes;
- every answered confirmation is logged with the reply exactly as typed.
"""
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from osc_mcp.gate import LODGED, sydney_time

from test_write_gate import GateTestCase, server

PO = "permit-officer"
RFI_IN = "Receive RFI from Certifier"
RFI_REVIEW = "Review RFI Information Request from Certifier"
RFI_OUT = "Return RFI Information to Certifier"
BA_IN = "h) Building Approval Received from Certifier"
COVENANT_IN = "Submit Covenant Application"
COVENANT_OK = "Receive Covenant Approval & Upload to OSC"
LEVY = "Pay Q Leave / Long Service Levy"
INSURANCES = "Email Copy of Relevant Insurances to Certifier"
EMAIL_NOTE = "date from the certifier's email received 20 Oct 2026"


class PermitOfficerTestCase(GateTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        f = self.fake
        self.job_id = f.add_job(f.client_id, "26998", lot="40", line1="SAMPLE ROAD", suburb="TESTVILLE",
                                postcode="2000", days_ago=40)
        self.osc_job = f.jobs[self.job_id]
        self.osc_job.update(workflowStatusName="3. Pre-Construction", createdOnUtc="2026-06-01T00:00:00Z")
        # Sequence numbers as on a pilot job that carries "Gas Mains Check" after lodgement
        self.a = {}
        for seq, name, done in ((52, LODGED, "2026-09-04T00:00:00Z"), (53, "Gas Mains Check", None),
                                (58, COVENANT_IN, None), (59, COVENANT_OK, None), (61, RFI_IN, None),
                                (62, RFI_REVIEW, None), (63, RFI_OUT, None), (73, LEVY, None),
                                (77, INSURANCES, None), (88, BA_IN, None)):
            self.a[name] = f.add_activity(self.job_id, seq, name, done=done)
        f.activities[self.a[INSURANCES]]["hasCompletionQuestions"] = True
        today = patch("osc_mcp.gate.sydney_today", return_value=date(2026, 10, 23))
        today.start()
        self.patches.append(today)
        self.logs = tempfile.TemporaryDirectory()
        self.use_config(log_root=self.logs.name)

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.logs.cleanup()

    def complete(self, name, day="2026-10-20", note=EMAIL_NOTE):
        change = {"method": "POST", "path": f"/api/JobActivities/{self.a[name]}/Complete",
                  "body": {"completionDate": day}}
        return {**change, "note": note} if note else change

    async def tick(self, name, day="2026-10-20", note=EMAIL_NOTE, workflow=PO):
        return await server.osc_prepare_write("POST", f"/api/JobActivities/{self.a[name]}/Complete", self.job_id,
                                              body={"completionDate": day}, workflow=workflow, note=note)

    async def update(self, changes, workflow=PO):
        return await server.osc_prepare_changes(self.job_id, changes, workflow)

    def attachment(self, name="RFI.msg"):
        path = Path(self.folder.name) / name
        path.write_bytes(b"synthetic certifier email")
        return str(path)

    def log_lines(self, role="permit-officer"):
        path = Path(self.logs.name) / role / "logs" / "osc-writes.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    async def assert_refused(self, out, words):
        self.assertFalse(out["ok"], out)
        self.assertIsNone(out["confirmation_code"])
        self.assertTrue(out["confirmation_text"].startswith("Nothing was changed in OnSite Companion."))
        self.assertIn(words, out["confirmation_text"])
        self.assertEqual(self.fake.writes, [])


class OneConfirmationTests(PermitOfficerTestCase):
    async def test_rfi_received_is_one_confirmation_and_one_yes(self):
        out = await self.update([
            self.complete(RFI_IN),
            {"method": "POST", "path": f"/api/JobActivities/{self.a[RFI_IN]}/Messages",
             "form": {"Subject": "RFI RECEIVED", "Body": "RFI received from the certifier, 6 items.",
                      "Documents[0].description": "RFI"},
             "files": {"Documents[0].file": self.attachment()}},
        ])
        self.assertTrue(out["ok"], out)
        text = out["confirmation_text"]
        self.assertIn("Job: 26998 - LOT 40 SAMPLE ROAD, TESTVILLE NSW 2000", text)
        self.assertIn("2 changes, made in this order:", text)
        self.assertIn('1. Activity 61 "Receive RFI from Certifier" is marked complete\n'
                      "   - Completion date: now empty, will be 20 Oct 2026", text)
        self.assertIn(f"   Note: {EMAIL_NOTE}", text)
        self.assertIn("   Note: this date is 3 days before today (23 Oct 2026). The BA report shows it as "
                      "Received RFI.", text)
        self.assertIn('2. A message is added to activity 61 "Receive RFI from Certifier"', text)
        self.assertIn("- Attachment: RFI.msg (1 KB)", text)
        self.assertNotIn("Warning", text)
        self.assertIn('Reply "yes" to make all 2 changes', text)
        self.assertEqual(self.fake.writes, [], "preparing must never write")

        result = await server.osc_confirm_write(out["confirmation_code"], "Yes")
        self.assertTrue(result["ok"], result)
        self.assertEqual([c["state"] for c in result["changes"]], ["verified", "verified"])
        self.assertEqual([w["path"].rsplit("/", 1)[-1] for w in self.fake.writes], ["Complete", "Messages"])
        self.assertEqual(self.fake.activities[self.a[RFI_IN]]["completionDate"], "2026-10-20")

        [entry] = self.log_lines()
        self.assertEqual((entry["workflow"], entry["reply"], entry["sent"], entry["state"]),
                         (PO, "Yes", True, "verified"))
        self.assertEqual(entry["job"], "26998 - LOT 40 SAMPLE ROAD, TESTVILLE NSW 2000")
        self.assertEqual(len(entry["asked"]), 2)
        self.assertEqual(entry["asked"][0]["fields"], [["Completion date", None, "2026-10-20"]])

    async def test_a_tick_earlier_in_the_update_counts_as_the_step_before(self):
        await self.assert_refused(await self.tick(RFI_OUT, note="the sent email of 21 Oct 2026"),
                                  'Activity 61 "Receive RFI from Certifier" comes first and is not complete yet')
        reversed_ = await self.update([self.complete(RFI_OUT), self.complete(RFI_IN)])
        await self.assert_refused(reversed_, "Change 1: Activity 61")
        out = await self.update([self.complete(RFI_IN), self.complete(RFI_OUT, day="2026-10-21"),
                                 self.complete(BA_IN, day="2026-10-23", note="the approval email of today")])
        self.assertTrue(out["ok"], out)
        self.assertNotIn("still open", out["confirmation_text"])
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(self.fake.writes), 3)

    async def test_borderline_cases_are_warnings_inside_the_same_confirmation(self):
        out = await self.tick(LEVY, day="2026-10-23", note="the levy receipt filed today")
        self.assertTrue(out["ok"], out)
        self.assertIn("Warning: say yes only if this has been paid.", out["confirmation_text"])
        self.assertNotIn("before today", out["confirmation_text"])
        out = await self.tick(BA_IN, day="2026-10-22", note="the approval email of 22 Oct 2026")
        self.assertTrue(out["ok"], out)
        self.assertIn('Warning: "Return RFI Information to Certifier" is still open on this job.',
                      out["confirmation_text"])
        out = await self.tick(RFI_IN, day="2026-09-10")
        self.assertTrue(out["ok"], out)
        self.assertIn("Warning: this date is 43 days before today (23 Oct 2026). The BA report shows it as "
                      "Received RFI. Check it is the day it happened.", out["confirmation_text"])

    async def test_a_later_change_that_moved_is_asked_again_under_the_same_workflow(self):
        f = self.fake
        write = f._write

        def someone_ticks_return_rfi(*args):
            answer = write(*args)
            f.activities[self.a[RFI_OUT]]["completionDate"] = "2026-10-21T00:00:00Z"
            return answer
        f._write = someone_ticks_return_rfi
        out = await self.update([self.complete(RFI_IN), self.complete(RFI_OUT, day="2026-10-21"),
                                 self.complete(BA_IN, day="2026-10-22", note="the approval email")])
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertEqual(result["state"], "stopped", result)
        self.assertIn("1 change, made in this order", result["confirmation_text"])
        self.assertIn('1. Activity 88 "h) Building Approval Received from Certifier" is marked complete',
                      result["confirmation_text"])
        rest = await server.osc_confirm_write(result["confirmation_code"], "yes")
        self.assertTrue(rest["ok"], rest)
        self.assertEqual([e["state"] for e in self.log_lines()], ["stopped", "verified"])


class RefusalTests(PermitOfficerTestCase):
    async def test_each_workflow_keeps_to_its_own_changes(self):
        f = self.fake
        await self.assert_refused(await server.osc_prepare_write(
            "PATCH", f"/api/Jobs/{self.job_id}", self.job_id, body={"startDate": "2026-11-01"}, workflow=PO),
            "The Permit Officer workflow does not change a job")
        await self.assert_refused(await server.osc_prepare_write(
            "POST", "/api/Jobs", "", body={"clientID": f.client_id}, workflow=PO),
            "does not change a new job")
        await self.assert_refused(await self.tick(RFI_IN, workflow="intake"), "not one of the intake activities")
        intake_step = f.add_activity(self.job_id, 1, "Initial Contact")
        await self.assert_refused(await server.osc_prepare_write(
            "POST", f"/api/JobActivities/{intake_step}/Complete", self.job_id,
            body={"completionDate": "2026-10-20"}, workflow=PO, note=EMAIL_NOTE),
            "not one of the Permit Officer's building-approval activities")
        for name in (RFI_REVIEW, LODGED, "Gas Mains Check"):  # left off the list on purpose
            with self.subTest(name=name):
                await self.assert_refused(await self.tick(name), "not one of the Permit Officer's")
        await self.assert_refused(await self.tick(RFI_IN, workflow="sales"), "not a workflow that can change")
        await self.assert_refused(await server.osc_prepare_write(
            "POST", f"/api/JobActivities/{self.a[RFI_IN]}/NotApplicable", self.job_id,
            body={"shouldNotNALinkedActivities": True}, workflow=PO), "not one of the approved")

    async def test_nsw_jobs_in_pre_construction_only(self):
        self.osc_job["siteAddress"]["state"] = "QLD"
        await self.assert_refused(await self.tick(RFI_IN), "not an NSW job (QLD)")
        await self.assert_refused(await server.osc_prepare_write(
            "POST", f"/api/Jobs/{self.job_id}/Messages", self.job_id, form={"Subject": "RFI RECEIVED"},
            workflow=PO), "not an NSW job")
        self.osc_job["siteAddress"]["state"] = "NSW"
        self.osc_job["workflowStatusName"] = "8. Cancelled"
        await self.assert_refused(await self.tick(RFI_IN), 'is in "8. Cancelled", not 3. Pre-Construction')
        self.osc_job["workflowStatusName"] = "20. Test Job"
        self.assertTrue((await self.tick(RFI_IN))["ok"])

    async def test_dates_that_would_be_wrong(self):
        cases = (("2026-10-24", "is after today (23 Oct 2026 in Sydney)"),
                 ("2026-10-20T00:00:00Z", "written YYYY-MM-DD"),
                 ("2026-02-30", "(YYYY-MM-DD) is needed"),
                 ("2026-05-30", "before the job was created in OnSite Companion (1 Jun 2026)"),
                 ("2026-09-01", 'before "Submit Documents to Private Certifier for Building Approval '
                                'Application" was completed (4 Sep 2026)'))
        for day, words in cases:
            with self.subTest(day=day):
                await self.assert_refused(await self.tick(RFI_IN, day=day), words)
        await self.assert_refused(await self.tick(RFI_IN, note=""), "Say where the completion date comes from")

    async def test_completion_questions_and_twin_activities_stay_with_a_person(self):
        await self.assert_refused(await self.tick(INSURANCES), "has completion questions")
        self.fake.add_activity(self.job_id, 64, RFI_IN)  # a second RFI step from an appended template
        await self.assert_refused(await self.tick(RFI_IN), 'has 2 open activities called "Receive RFI from Certifier"')

    async def test_a_not_applicable_step_before_counts_as_done(self):
        self.fake.activities[self.a[COVENANT_IN]].update(isNotApplicable=True, completionDate="2026-10-25T00:00:00Z")
        out = await self.tick(COVENANT_OK, note="the developer's approval email of 20 Oct 2026")
        self.assertTrue(out["ok"], out)  # an N/A step's date is not a completion, so it is not compared

    async def test_messages_only_on_the_listed_activities(self):
        await self.assert_refused(await server.osc_prepare_write(
            "POST", f"/api/JobActivities/{self.a[RFI_REVIEW]}/Messages", self.job_id,
            form={"Subject": "RFI ITEM SENT"}, workflow=PO), "not one of the Permit Officer's")
        out = await server.osc_prepare_write("POST", f"/api/Jobs/{self.job_id}/Messages", self.job_id,
                                             form={"Subject": "ENERGY REPORT SENT", "Body": "Sent 22 Oct 2026."},
                                             workflow=PO)
        self.assertTrue(out["ok"], out)


class WriteLogTests(PermitOfficerTestCase):
    async def test_every_answer_is_logged_with_the_reply_as_typed(self):
        for reply, state in (("no", "cancelled"), ("yes but not the date", "not_sent")):
            out = await self.tick(RFI_IN)
            result = await server.osc_confirm_write(out["confirmation_code"], reply)
            self.assertFalse(result["sent"])
            self.assertEqual(self.log_lines()[-1]["state"], state)
            self.assertEqual(self.log_lines()[-1]["reply"], reply)
        self.assertEqual(self.fake.writes, [])
        intake = await server.osc_prepare_write("POST", f"/api/JobActivities/{self.fake.act1}/Complete",
                                                self.fake.job_id, body={"completionDate": "2026-10-13"})
        self.assertTrue((await server.osc_confirm_write(intake["confirmation_code"], "yes"))["ok"])
        self.assertEqual(self.log_lines("contract-admin")[-1]["workflow"], "intake")
        self.assertEqual(len(self.log_lines()), 2, "each workflow logs to its own role folder")

    async def test_a_log_that_cannot_be_written_is_said_so(self):
        blocker = Path(self.logs.name) / "not-a-folder"
        blocker.write_text("x")
        self.use_config(log_root=str(blocker))
        out = await self.tick(RFI_IN)
        result = await server.osc_confirm_write(out["confirmation_code"], "yes")
        self.assertTrue(result["ok"], result)
        self.assertIn("not logged", result["log_error"])


class SydneyTimeTests(unittest.TestCase):
    def test_daylight_saving_without_a_time_zone_database(self):
        cases = (("2026-10-03T15:59:00", "2026-10-04 01:59"),   # last minute of AEST
                 ("2026-10-03T16:00:00", "2026-10-04 03:00"),   # 2 am AEST becomes 3 am AEDT
                 ("2026-04-04T15:59:00", "2026-04-05 02:59"),   # last minute of AEDT
                 ("2026-04-04T16:00:00", "2026-04-05 02:00"),   # 3 am AEDT becomes 2 am AEST
                 ("2026-10-22T14:00:00", "2026-10-23 01:00"),   # a morning tick reads as the evening before in UTC
                 ("2026-07-01T13:59:00", "2026-07-01 23:59"))
        for utc, local in cases:
            with self.subTest(utc=utc):
                moment = datetime.fromisoformat(utc).replace(tzinfo=timezone.utc)
                self.assertEqual(sydney_time(moment).strftime("%Y-%m-%d %H:%M"), local)


if __name__ == "__main__":
    unittest.main()
