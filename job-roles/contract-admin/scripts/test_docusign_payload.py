r"""Self-test for docusign_payload.py (CD-10, 13 Oct 2026).

    python test_docusign_payload.py

Synthetic values only. No DocuSign call is ever made by the module under
test; this checks the template pick, recipient mapping, subject and message,
the custom field, the stop conditions and the files written.
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
    print("  template pick: ok")


def check_recipients():
    t, _ = dp.pick_template("NSW", TWO)
    roles, sources = dp.recipients_for(t, TWO)
    assert roles == [{"roleName": "Buyer 1", "name": "Alex EXAMPLE", "email": "alex@example.com"},
                     {"roleName": "Buyer 2", "name": "Sam SAMPLE", "email": "sam@example.com"}], roles
    assert sources == ["Buyer 1: owner_1 + owner_email", "Buyer 2: owner_2 + owner_2_email"], sources
    t, _ = dp.pick_template("QLD", TWO)
    roles, _ = dp.recipients_for(t, TWO)
    assert [r["roleName"] for r in roles] == ["BUYER 1", "Buyer 2"]
    t, _ = dp.pick_template("QLD", COMPANY)
    roles, sources = dp.recipients_for(t, COMPANY)
    assert roles == [{"roleName": "Buyer - Company Guarantor", "name": "Casey SIGNER",
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


def check_build_envelope():
    env = dp.build_envelope("NSW", TWO, "docusign-demo")
    d = env["envelopeDefinition"]
    assert d["status"] == "created"
    assert d["templateId"] == ""
    assert d["emailSubject"] == dp.subject_for(TWO)
    assert d["customFields"] == {"textCustomFields": [
        {"name": "JobNo", "value": "26099", "show": "false", "required": "false"}]}
    assert [r["roleName"] for r in d["templateRoles"]] == ["Buyer 1", "Buyer 2"]
    assert env["templateName"] == "NSW Build _ 2 Buyers"
    assert env["defaultRoles"] == ["Builder", "Builder Witness", "Signer 1"]
    assert env["server"] == "docusign-demo"
    assert any("placeholder" in s for s in env["staffBeforeSending"]), env["staffBeforeSending"]
    assert "remoteUrl" not in json.dumps(d) and '"sent"' not in json.dumps(d)
    env = dp.build_envelope("NSW", SINGLE, "docusign-demo")
    assert any("Buyer Witness" in s for s in env["staffBeforeSending"])
    try:
        dp.build_envelope("NSW", dict(TWO, job_no=""), "docusign-demo")
    except dp.PayloadStop as e:
        assert "job_no" in str(e)
    else:
        raise AssertionError("no stop for missing job_no")
    print("  build_envelope: ok")


def check_cli_files():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "job.json").write_text(json.dumps(TWO), encoding="utf-8")
        (wd / "routes.txt").write_text("INCLUSIONS\tTEST\tZ:\\t\nBUILD CONTRACT\tPRODUCTION\tZ:\\p\n",
                                       encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "NSW", "--server", "docusign-demo"])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is True and env["templateName"] == "NSW Build _ 2 Buyers"
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert "CALL: yes" in txt and "Buyer 1: owner_1 + owner_email" in txt and "Signer 1" in txt
        # TEST route -> files written, no call
        (wd / "routes.txt").write_text("BUILD CONTRACT\tTEST\tZ:\\t\n", encoding="utf-8")
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["call"] is False and env["server"] == "docusign-demo"
        assert "CALL: no" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        # no routes.txt -> stop
        (wd / "routes.txt").unlink()
        rc = dp.main(["--job", str(wd / "job.json"), "--region", "QLD"])
        assert rc == 2
        assert "routes.txt" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
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


if __name__ == "__main__":
    check_template_pick()
    check_recipients()
    check_subject_and_message()
    check_build_envelope()
    check_cli_files()
    print("docusign_payload self-test: all ok")
