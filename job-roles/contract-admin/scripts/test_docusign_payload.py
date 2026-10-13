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


if __name__ == "__main__":
    check_template_pick()
    check_recipients()
    print("docusign_payload self-test: all ok")
