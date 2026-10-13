r"""Self-test for docusign_payload.py (CD-10, 13 Oct 2026; docusign-upload switch the same day).

    python test_docusign_payload.py

Synthetic values only. No DocuSign call is ever made by the module under
test; this checks the template pick, recipient mapping, subject and message,
the JobNo, the tool arguments, the server pick, the stop conditions and the
files written.
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import docusign_payload as dp  # noqa: E402

SINGLE = {"job_no": "26099", "lot_no": "12", "suburb": "Testville NSW",
          "owner_1": "Alex EXAMPLE", "owner_email": "alex@example.com"}
TWO = dict(SINGLE, owner_2="Sam SAMPLE", owner_2_email="sam@example.com")
THREE = dict(TWO, owner_3="Jo THIRD")
COMPANY = {"job_no": "26098", "lot_no": "4", "suburb": "Pallara QLD",
           "owner_1": "EXAMPLE HOLDINGS PTY LTD ATF EXAMPLE FAMILY TRUST",
           "guarantor_name": "Casey SIGNER", "guarantor_email": "casey@example.com"}


def check_template_pick():
    t, flags = dp.pick_template("NSW", SINGLE)
    assert t["name"] == "NSW Build _ Single Buyer" and flags == [], (t, flags)
    t, flags = dp.pick_template("NSW", TWO)
    assert t["name"] == "NSW Build _ 2 Buyers" and flags == []
    t, flags = dp.pick_template("NSW", COMPANY)
    assert t["name"] == "NSW Build _ Company"
    t, flags = dp.pick_template("QLD", SINGLE)
    assert t["name"] == "QLD Build _ Single Buyer"
    t, flags = dp.pick_template("QLD", TWO)
    assert t["name"] == "QLD Build _ 2 Buyer"
    t, flags = dp.pick_template("QLD", COMPANY)
    assert t["name"] == "QLD Build _ Company"
    t, flags = dp.pick_template("NSW", THREE)
    assert t["name"] == "NSW Build _ 2 Buyers"
    assert flags and "owner_3" in flags[0], flags
    # I3: a company_signatory alone selects the Company template
    t, _ = dp.pick_template("NSW", dict(SINGLE, company_signatory="Casey SIGNER"))
    assert t["name"] == "NSW Build _ Company", t
    # I5: owner_3 without owner_2 is a stop
    # deferred minors: unknown state, no owner_1
    for state, vals, needle in (("NSW", dict(SINGLE, owner_3="Jo THIRD"), "owner_2 is blank"),
                                ("VIC", SINGLE, "VIC"),
                                ("NSW", dict(SINGLE, owner_1=""), "owner_1")):
        try:
            dp.pick_template(state, vals)
        except dp.PayloadStop as e:
            assert needle in str(e), (needle, e)
        else:
            raise AssertionError(f"no stop for {state} {needle}")
    print("  template pick: ok")


def check_recipients():
    t, _ = dp.pick_template("NSW", TWO)
    roles, sources = dp.recipients_for(t, TWO)
    # the docusign-upload tools' shape: role, name, email
    assert roles == [{"role": "Buyer 1", "name": "Alex EXAMPLE", "email": "alex@example.com"},
                     {"role": "Buyer 2", "name": "Sam SAMPLE", "email": "sam@example.com"}], roles
    assert sources == ["Buyer 1: owner_1 + owner_email", "Buyer 2: owner_2 + owner_2_email"], sources
    t, _ = dp.pick_template("QLD", TWO)
    roles, _ = dp.recipients_for(t, TWO)
    assert [r["role"] for r in roles] == ["BUYER 1", "Buyer 2"]
    t, _ = dp.pick_template("QLD", COMPANY)
    roles, sources = dp.recipients_for(t, COMPANY)
    assert roles == [{"role": "Buyer - Company Guarantor", "name": "Casey SIGNER",
                      "email": "casey@example.com"}], roles
    # stops
    for bad, needle in ((dict(TWO, owner_2_email=""), "owner_2_email"),
                        (dict(SINGLE, owner_email=None), "owner_email"),
                        (dict(COMPANY, guarantor_email=""), "guarantor_email"),
                        (dict(COMPANY, guarantor_name=""), "guarantor_name")):
        state = "QLD" if "guarantor_name" in bad else "NSW"
        t, _ = dp.pick_template(state, bad)
        try:
            dp.recipients_for(t, bad)
        except dp.PayloadStop as e:
            assert needle in str(e), (needle, e)
        else:
            raise AssertionError(f"no stop for missing {needle}")
    print("  recipients: ok")


def check_subject_and_message():
    assert dp.subject_for(TWO) == "Complete with DocuSign: BUILD CONTRACT - LOT 12, TESTVILLE"
    assert dp.subject_for(dict(SINGLE, suburb="North Kellyville")) == \
        "Complete with DocuSign: BUILD CONTRACT - LOT 12, NORTH KELLYVILLE"
    t, _ = dp.pick_template("NSW", TWO)
    assert dp.message_for(TWO, t) == ("Dear Alex & Sam,\n\n"
                                      "Please find the building contract for review and signing.\n\n"
                                      "Thank you\nSales Admin")
    t, _ = dp.pick_template("QLD", COMPANY)
    assert dp.message_for(COMPANY, t).startswith("Dear Casey,\n")
    print("  subject + message: ok")


DRAFT_ARG_KEYS = {"template_name", "recipients", "email_subject", "email_blurb", "job_no", "documents"}


def check_build_envelope():
    env = dp.build_envelope("NSW", TWO, dp.PRODUCTION_SERVER)
    a = env["draftArgs"]
    # exactly the arguments docusign_draft_preview and docusign_create_draft take
    assert set(a) == DRAFT_ARG_KEYS, sorted(a)
    assert a["template_name"] == env["templateName"] == "NSW Build _ 2 Buyers"
    assert a["email_subject"] == dp.subject_for(TWO)
    assert a["email_blurb"].startswith("Dear Alex & Sam,")
    assert a["job_no"] == "26099"
    assert [r["role"] for r in a["recipients"]] == ["Buyer 1", "Buyer 2"]
    assert a["documents"] == []
    assert env["defaultRoles"] == ["Builder", "Builder Witness", "Signer 1"]
    assert env["server"] == "docusign-upload-prod"
    # the hosted createEnvelope body is gone: nothing here can be passed to createEnvelope
    assert "envelopeDefinition" not in env
    dumped = json.dumps(env)
    assert "remoteUrl" not in dumped and '"sent"' not in dumped and "templateRoles" not in dumped
    # the draft carries the job's own PDFs, so staff no longer replace placeholders
    staff = env["staffBeforeSending"]
    assert not any("placeholder" in s.lower() for s in staff), staff
    assert any("flags" in s and "tabs" in s for s in staff), staff
    env = dp.build_envelope("NSW", SINGLE, dp.PRODUCTION_SERVER)
    assert any("Buyer Witness" in s for s in env["staffBeforeSending"])
    try:
        dp.build_envelope("NSW", dict(TWO, job_no=""), dp.PRODUCTION_SERVER)
    except dp.PayloadStop as e:
        assert "job_no" in str(e)
    else:
        raise AssertionError("no stop for missing job_no")
    print("  build_envelope: ok")


def check_server_for():
    """A synthetic job under runtime/docusign-sandbox goes to the sandbox server; every other
    job folder is a real job's and goes to the production server (CD-10.1)."""
    sandbox_job = dp.SANDBOX_DIR / "26001 LOT 1 SYNTHETIC" / "CONTRACT DOCUMENTATION"
    assert dp.server_for(str(sandbox_job)) == dp.SANDBOX_SERVER == "docusign-upload"
    assert dp.server_for(str(dp.SANDBOX_DIR)) == dp.SANDBOX_SERVER
    for real in (r"Z:\PROJECTS\SYDNEY\26099\CONTRACT\CONTRACT DOCUMENTATION",
                 str(dp.SANDBOX_DIR.parent / "docusign-sandbox-old" / "x"),   # a lookalike folder
                 str(dp.SANDBOX_DIR.parent / "contract-admin" / "outputs" / "x"),
                 None, ""):
        assert dp.server_for(real) == dp.PRODUCTION_SERVER == "docusign-upload-prod", real
    print("  server_for: ok")


def check_cli_files():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "job.json").write_text(json.dumps(TWO), encoding="utf-8")
        (wd / "routes.txt").write_text("INCLUSIONS\tTEST\tZ:\\t\nBUILD CONTRACT\tPRODUCTION\tZ:\\p\n",
                                       encoding="utf-8")
        # the hosted placeholder server is not a choice any more
        try:
            dp.main(["--job", str(wd / "job.json"), "--region", "NSW", "--server", "docusign-demo"])
        except SystemExit as e:
            assert e.code == 2, e.code
        else:
            raise AssertionError("--server docusign-demo was accepted")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "NSW", "--server", dp.SANDBOX_SERVER])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["server"] == "docusign-upload"
        assert "SANDBOX" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "NSW"])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is True and env["templateName"] == "NSW Build _ 2 Buyers"
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert "CALL: yes" in txt and "Buyer 1: owner_1 + owner_email" in txt and "Signer 1" in txt
        assert "docusign-upload-prod" in txt and "PRODUCTION" in txt, txt
        # TEST route -> files written, no call
        (wd / "routes.txt").write_text("BUILD CONTRACT\tTEST\tZ:\\t\n", encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is False and env["server"] == "docusign-upload-prod"
        assert "CALL: no" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        # no routes.txt -> stop, and the envelope from the run before is removed
        assert (wd / "docusign_envelope.json").exists()
        (wd / "routes.txt").unlink()
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 2
        assert "routes.txt" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert not (wd / "docusign_envelope.json").exists(), "stale envelope left after a stop"
        # unreadable job JSON -> stop, written to the payload file
        rc = dp.main(["--job", str(wd / "missing.json"), "--region", "NSW"])
        assert rc == 2, rc
        assert "job JSON not readable" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        # --job-dir: the saved build contract PDF must be in the job folder
        jd = wd / "CONTRACT DOCUMENTATION"
        jd.mkdir()
        (wd / "routes.txt").write_text("BUILD CONTRACT\tPRODUCTION\tZ:\\p\n", encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"])
        assert rc == 2, rc
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert "build contract PDF not found in the job folder" in txt, txt
        (jd / "BUILD CONTRACT_LOT 12_TESTVILLE_EXAMPLE&SAMPLE.pdf").write_bytes(b"")
        rc = dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"])
        assert rc == 0, rc
        # region from a job dir path
        assert dp.state_for(r"Z:\PROJECTS\SEQ\26098 LOT 4\CONTRACT\CONTRACT DOCUMENTATION", None) == "QLD"
        assert dp.state_for(r"Z:\PROJECTS\SYDNEY\26099\CONTRACT\CONTRACT DOCUMENTATION", None) == "NSW"
        try:
            dp.state_for(r"Z:\PROJECTS\NOWHERE\x", None)
        except dp.PayloadStop:
            pass
        else:
            raise AssertionError("unknown region did not stop")
    print("  cli + files: ok")


def check_documents_list():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "job.json").write_text(json.dumps(TWO), encoding="utf-8")
        (wd / "routes.txt").write_text("BUILD CONTRACT\tPRODUCTION\tZ:\\p\n", encoding="utf-8")
        jd = wd / "CONTRACT DOCUMENTATION"
        jd.mkdir()
        suffix = "LOT 12_TESTVILLE_EXAMPLE&SAMPLE"
        for kind in ("BUILD CONTRACT", "INCLUSIONS"):
            (jd / f"{kind}_{suffix}.pdf").write_bytes(b"%PDF-1.7 synthetic")
        (jd / "PLANS - house design.pdf").write_bytes(b"%PDF-1.7 synthetic")  # not the CD-7.2 name
        rc = dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert [d["kind"] for d in env["documents"]] == ["BUILD CONTRACT", "INCLUSIONS"], env["documents"]
        assert env["documents"][0]["path"] == str(jd / f"BUILD CONTRACT_{suffix}.pdf")
        assert env["documentsMissing"] == ["PRELIMINARY AGREEMENT", "PLANS"], env["documentsMissing"]
        # the tool arguments carry the same list, so preview and create get the same files
        assert env["draftArgs"]["documents"] == env["documents"]
        missing_item = [s for s in env["staffBeforeSending"] if s.startswith("Not in the draft")]
        assert missing_item and "PRELIMINARY AGREEMENT, PLANS" in missing_item[0], env["staffBeforeSending"]
        assert env["server"] == "docusign-upload-prod"   # a temp folder is not the sandbox folder
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert f"    INCLUSIONS: INCLUSIONS_{suffix}.pdf" in txt, txt
        assert "not in the job folder under the CD-7.2 name: PRELIMINARY AGREEMENT, PLANS" in txt, txt
        (jd / f"PLANS_{suffix}.pdf").write_bytes(b"%PDF-1.7 synthetic")
        assert dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"]) == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert [d["kind"] for d in env["documents"]] == ["BUILD CONTRACT", "INCLUSIONS", "PLANS"]
        # QLD templates hold no preliminary agreement, so staff are not told to add one
        assert dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "QLD"]) == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["documentsMissing"] == ["PRELIMINARY AGREEMENT"]
        assert not any(s.startswith("Not in the draft") for s in env["staffBeforeSending"]), \
            env["staffBeforeSending"]
        # no --job-dir: nothing listed, and the report says why
        assert dp.main(["--job", str(wd / "job.json"), "--region", "NSW"]) == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["documents"] == [] and env["documentsMissing"] == []
        assert env["draftArgs"]["documents"] == []
        assert "none listed (no --job-dir)" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
    print("  documents list: ok")


if __name__ == "__main__":
    check_template_pick()
    check_recipients()
    check_subject_and_message()
    check_build_envelope()
    check_server_for()
    check_cli_files()
    check_documents_list()
    print("docusign_payload self-test: all ok")
