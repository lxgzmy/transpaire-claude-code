"""Request building: kinds, template, recipients, carry or flag, size, duplicates, body."""
import base64
import copy
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import draft
from docusign_upload.draft import Stop
from docusign_upload.pdfcheck import PdfFile
from support import make_pdf, nsw_company_template, qld_single_template, qld_single_template_tabs, readback_for


def pdf(name, pages, size=1000):
    return PdfFile(path="/synthetic/" + name, name=name, bytes=size, pages=pages)


def build_plan(folder):
    """A QLD Single Buyer plan over real synthetic PDFs: contract and inclusions carry, plans flag."""
    template = draft.parse_template(qld_single_template())
    files = []
    for kind, pages in (("BUILD CONTRACT", 37), ("INCLUSIONS", 15), ("PLANS", 5)):
        name = f"{kind}_LOT 1_TESTVILLE_EXAMPLE.pdf"
        path = make_pdf(os.path.join(folder, name), pages)
        files.append((kind, PdfFile(path=path, name=name, bytes=os.path.getsize(path), pages=pages)))
    sent = draft.check_recipients(
        [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}], template)
    return draft.Plan(template, sent, draft.plan_documents(files, template),
                      "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE", "Dear Alex,", "00001")


class KindAndTemplateTests(unittest.TestCase):
    def test_kind_of_matches_by_name(self):
        self.assertEqual(draft.kind_of("BUILD CONTRACT _LOT 0_SYNTHETIC.pdf"), "BUILD CONTRACT")
        self.assertEqual(draft.kind_of("EXECUTED-PRELIMINARY AGREEMENT_LOT 0.pdf"), "PRELIMINARY AGREEMENT")
        self.assertEqual(draft.kind_of("plans_lot 0.pdf"), "PLANS")
        self.assertIsNone(draft.kind_of("SITE PHOTOS.pdf"))
        self.assertIsNone(draft.kind_of("INCLUSIONS AND PLANS.pdf"))

    def test_pick_template_is_exact_after_trimming(self):
        found = [{"name": "QLD Build _ Single Buyer (old)"}, {"name": "QLD Build _ Single Buyer "}]
        self.assertEqual(draft.pick_template(found, "QLD Build _ Single Buyer")["name"],
                         "QLD Build _ Single Buyer ")

    def test_pick_template_stops_on_zero_or_several(self):
        with self.assertRaisesRegex(Stop, "matched 0 templates.*QLD Build _ 2 Buyer"):
            draft.pick_template([{"name": "QLD Build _ 2 Buyer"}], "QLD Build _ 2 Buyers")
        with self.assertRaisesRegex(Stop, "matched 2 templates"):
            draft.pick_template([{"name": "X "}, {"name": " X"}], "X")
        with self.assertRaisesRegex(Stop, "nothing"):
            draft.pick_template([], "X")

    def test_parse_template_reads_documents_and_roles(self):
        t = draft.parse_template(nsw_company_template())
        self.assertEqual(t.name, "NSW Build _ Company")
        self.assertEqual([(d.kind, d.document_id, d.pages) for d in t.documents],
                         [("BUILD CONTRACT", "1", 45), ("INCLUSIONS", "2", 18),
                          ("PRELIMINARY AGREEMENT", "4", 3), ("PLANS", "3", 5)])
        self.assertIn(draft.TemplateRole("Builder", "2", "2", "signers"), t.roles)

    def test_an_unknown_template_document_stops_without_naming_it(self):
        raw = qld_single_template()
        raw["documents"].append({"documentId": "77", "name": "SITE PHOTOS_SOMEONE.pdf", "pages": "2"})
        with self.assertRaises(Stop) as cm:
            draft.parse_template(raw)
        self.assertIn("77", str(cm.exception))
        self.assertNotIn("SOMEONE", str(cm.exception))

    def test_a_repeated_template_kind_stops(self):
        raw = qld_single_template()
        raw["documents"].append({"documentId": "78", "name": "PLANS_SECOND.pdf", "pages": "2"})
        with self.assertRaisesRegex(Stop, "more than one PLANS"):
            draft.parse_template(raw)


class ArgumentTests(unittest.TestCase):
    def setUp(self):
        self.template = draft.parse_template(qld_single_template())

    def test_text_args(self):
        draft.check_text_args("26045", "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE",
                              "Dear Alex,")
        # "00001\n" matters: a trailing newline slipped past the duplicate search (final review)
        for job_no in ("", "00001&status=any", "26045 ", "x" * 21, "00001\n"):
            with self.subTest(job_no=job_no), self.assertRaisesRegex(Stop, "job_no"):
                draft.check_text_args(job_no, "s", "b")
        with self.assertRaisesRegex(Stop, "email_subject is empty"):
            draft.check_text_args("1", "  ", "b")
        with self.assertRaisesRegex(Stop, "allows 100"):
            draft.check_text_args("1", "s" * 101, "b")
        with self.assertRaisesRegex(Stop, "allows 10000"):
            draft.check_text_args("1", "s", "b" * 10001)

    def test_kinds(self):
        self.assertEqual(draft.check_kinds([" build contract", "Plans"]), ["BUILD CONTRACT", "PLANS"])
        with self.assertRaisesRegex(Stop, "unknown document kind: SPEC"):
            draft.check_kinds(["BUILD CONTRACT", "SPEC"])
        with self.assertRaisesRegex(Stop, "given twice: PLANS"):
            draft.check_kinds(["BUILD CONTRACT", "PLANS", "plans"])
        with self.assertRaisesRegex(Stop, "no BUILD CONTRACT"):
            draft.check_kinds(["INCLUSIONS"])

    def test_recipients_take_the_template_ids(self):
        (r, t), = draft.check_recipients(
            [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}], self.template)
        self.assertEqual((r.role, r.name, t.recipient_id, t.routing_order),
                         ("Buyer", "Alex EXAMPLE", "1", "1"))

    def test_role_case_mismatch_stops_with_the_role_list(self):
        # QLD 2 Buyer spells its first role "BUYER 1" and NSW "Buyer 1": no silent second recipient
        with self.assertRaises(Stop) as cm:
            draft.check_recipients([{"role": "buyer", "name": "A", "email": "a@example.com"}],
                                   self.template)
        self.assertIn("Builder, Buyer", str(cm.exception))
        self.assertIn("capitals", str(cm.exception))

    def test_recipient_stops(self):
        raw = qld_single_template()
        raw["recipients"]["carbonCopies"] = [{"roleName": "Office copy", "recipientId": "9",
                                              "routingOrder": "3"}]
        template = draft.parse_template(raw)
        one = {"role": "Buyer", "name": "A", "email": "a@example.com"}
        cases = [
            ([], "no recipients"),
            ([one, one], "given twice"),
            ([dict(one, role="Office copy")], "not a signer"),
            ([dict(one, name=" ")], "has no name"),
            ([dict(one, email="not-an-email")], "malformed email"),
        ]
        for recipients, needle in cases:
            with self.subTest(needle=needle), self.assertRaisesRegex(Stop, needle):
                draft.check_recipients(recipients, template)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.qld = draft.parse_template(qld_single_template())

    def test_carry_when_pages_match_and_flag_otherwise_in_envelope_order(self):
        files = [("PLANS", pdf("PLANS_X.pdf", 5)), ("BUILD CONTRACT", pdf("BUILD CONTRACT_X.pdf", 37)),
                 ("INCLUSIONS", pdf("INCLUSIONS_X.pdf", 15)),
                 ("PRELIMINARY AGREEMENT", pdf("PRELIMINARY AGREEMENT_X.pdf", 3))]
        planned = draft.plan_documents(files, self.qld)
        self.assertEqual([(d.kind, d.carry, d.template_document_id) for d in planned],
                         [("BUILD CONTRACT", True, "1"), ("INCLUSIONS", True, "86092972"),
                          ("PRELIMINARY AGREEMENT", False, None), ("PLANS", False, "3")])
        self.assertEqual(planned[2].reason, "the template has no PRELIMINARY AGREEMENT document")
        self.assertEqual(planned[3].reason, "5 pages, the template's has 4")

    def test_the_contract_must_carry(self):
        with self.assertRaisesRegex(Stop, "BUILD CONTRACT: 36 pages, the template's has 37.*fixed form"):
            draft.plan_documents([("BUILD CONTRACT", pdf("B.pdf", 36))], self.qld)
        with self.assertRaisesRegex(Stop, "no BUILD CONTRACT"):
            draft.plan_documents([("PLANS", pdf("P.pdf", 4))], self.qld)

    def test_size_limit_names_the_largest_document(self):
        planned = draft.plan_documents([("BUILD CONTRACT", pdf("B.pdf", 37, size=3_000_000)),
                                        ("PLANS", pdf("P.pdf", 4, size=9_000_000))], self.qld)
        draft.check_size(planned)
        with patch.object(draft, "MAX_BODY_BYTES", 10_000_000):
            with self.assertRaisesRegex(Stop, "largest: PLANS"):
                draft.check_size(planned)

    def test_find_duplicate(self):
        def env(status, value="26045", fields=True):
            e = {"envelopeId": f"env-{status}", "status": status}
            if fields:
                e["customFields"] = {"textCustomFields": [{"name": "JobNo", "value": value}]}
            return e
        self.assertIsNone(draft.find_duplicate([env("voided"), env("Declined"), env("deleted")], "26045"))
        self.assertEqual(draft.find_duplicate([env("voided"), env("created")], "26045")["envelopeId"],
                         "env-created")
        self.assertIsNone(draft.find_duplicate([env("sent", value="26046")], "26045"))
        self.assertEqual(draft.find_duplicate([env("sent", fields=False)], "26045")["envelopeId"],
                         "env-sent")


class BodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plan = build_plan(self.tmp.name)
        self.body = draft.build_body(self.plan)

    def test_top_level(self):
        self.assertEqual(self.body["status"], "created")
        self.assertEqual(set(self.body), {"status", "emailSubject", "emailBlurb", "compositeTemplates"})

    def test_carried_documents_replace_the_template_documents(self):
        c1, c2, _ = self.body["compositeTemplates"]
        self.assertEqual(c1["serverTemplates"], [{"sequence": "1", "templateId": "tmpl-qld-single"}])
        self.assertEqual(c1["inlineTemplates"][0]["sequence"], "2")
        self.assertEqual((c1["document"]["documentId"], c2["document"]["documentId"]), ("1", "86092972"))
        self.assertEqual((c1["document"]["name"], c1["document"]["fileExtension"]),
                         ("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf", "pdf"))
        with open(self.plan.documents[0].file.path, "rb") as fh:
            self.assertEqual(base64.b64decode(c1["document"]["documentBase64"]), fh.read())

    def test_a_flagged_document_has_no_server_template_and_a_fresh_id(self):
        c3 = self.body["compositeTemplates"][2]
        self.assertNotIn("serverTemplates", c3)
        self.assertEqual(c3["inlineTemplates"][0]["sequence"], "1")
        self.assertEqual(c3["document"]["documentId"], "9001")

    def test_buyers_only_and_job_no_in_the_first_inline_template(self):
        for comp in self.body["compositeTemplates"]:
            self.assertEqual(comp["inlineTemplates"][0]["recipients"]["signers"],
                             [{"recipientId": "1", "roleName": "Buyer", "routingOrder": "1",
                               "name": "Alex EXAMPLE", "email": "alex@example.com"}])
        first, *rest = self.body["compositeTemplates"]
        self.assertEqual(first["inlineTemplates"][0]["customFields"]["textCustomFields"],
                         [{"name": "JobNo", "value": "00001", "show": "false", "required": "false"}])
        self.assertTrue(all("customFields" not in c["inlineTemplates"][0] for c in rest))

    def test_plan_view(self):
        view = draft.plan_view(self.plan)
        self.assertEqual(view["roles_left_as_template_defaults"], ["Builder"])
        self.assertEqual([d["tabs"] for d in view["documents"]],
                         ["carried from the template", "carried from the template",
                          "none, flagged: 5 pages, the template's has 4"])
        self.assertEqual((view["template_documents_left_out"], view["status"]), ([], "created"))


class ReadBackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plan = build_plan(self.tmp.name)
        self.rb = readback_for(draft.build_body(self.plan), qld_single_template_tabs())
        self.template_tabs = draft.tab_counts(qld_single_template_tabs())

    def sent_envelope(self, **changes):
        envelope = {"status": "created", "emailSubject": self.plan.email_subject,
                    "emailBlurb": self.plan.email_blurb}
        envelope.update(changes)
        return envelope

    def check(self, **overrides):
        parts = {"envelope": self.sent_envelope(), "documents": self.rb["documents"],
                 "recipients": self.rb["recipients"], "custom_fields": self.rb["custom_fields"]}
        parts.update(overrides)
        return draft.read_back(self.plan, template_tabs=self.template_tabs, **parts)

    def test_tab_counts(self):
        counts = draft.tab_counts({"signers": [{"roleName": "Buyer", "tabs": {
            "signHereTabs": [{"documentId": "1", "pageNumber": "3"}, {"documentId": "1", "pageNumber": "3"}],
            "initialHereTabs": [{"documentId": "2", "pageNumber": "1"}]}}], "recipientCount": "1"})
        self.assertEqual(counts, {"1": {("Buyer", 3): 2}, "2": {("Buyer", 1): 1}})

    def test_a_draft_that_matches_the_plan_has_no_findings(self):
        out = self.check()
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["check"], "the draft matches the plan")
        self.assertEqual([(d["kind"], d["tabs"]) for d in out["documents"]],
                         [("BUILD CONTRACT", "carried"), ("INCLUSIONS", "carried"),
                          ("PLANS", "none, flagged")])
        self.assertEqual(out["documents"][1]["tab_pages_by_role"]["Builder"], [13])
        self.assertEqual(out["roles_without_tabs"], [])

    def test_findings(self):
        docs = self.rb["documents"]["envelopeDocuments"]
        signers = self.rb["recipients"]["signers"]
        tagged_plans = copy.deepcopy(self.rb["recipients"])
        tagged_plans["signers"][0]["tabs"].setdefault("signHereTabs", []).append(
            {"documentId": "3", "pageNumber": "1"})
        cases = [
            ({"envelope": self.sent_envelope(status="sent")}, "status is 'sent'"),
            # the template's own subject names a past job: flag it, never echo it
            ({"envelope": self.sent_envelope(emailSubject="BUILD CONTRACT_ Lot 116, PAST JOB")},
             "email subject in the draft is not the one sent"),
            ({"envelope": self.sent_envelope(emailBlurb="Dear PAST JOB,")},
             "email message in the draft is not the one sent"),
            ({"documents": {"envelopeDocuments": docs + [
                {"documentId": "9", "name": "PLANS_PAST JOB.pdf", "type": "content"}]}},
             "not one of the job's files (id 9)"),
            ({"documents": {"envelopeDocuments": docs[:2]}}, "PLANS: not in the draft"),
            ({"recipients": {"signers": signers + [
                {"roleName": "Buyer", "email": "alex@example.com", "tabs": {}}]}},
             "role 'Buyer' appears 2 times"),
            ({"recipients": {"signers": [dict(s, email="someone@example.com") if s["roleName"] == "Buyer"
                                         else s for s in signers]}}, "different email"),
            ({"recipients": tagged_plans}, "PLANS: 1 tabs in the draft, expected 0"),
            ({"custom_fields": {"textCustomFields": []}}, "JobNo"),
        ]
        for overrides, needle in cases:
            with self.subTest(needle=needle):
                out = self.check(**overrides)
                self.assertTrue(any(needle in f for f in out["findings"]), out["findings"])
                self.assertNotIn("PAST JOB", " ".join(out["findings"]))
                self.assertEqual(out["check"], "a person should look at the findings before sending")
