"""Regression test: extract_eoi.py against fixtures/eoi-sample-01.md.

Expected values come from fixtures/eoi-sample-01-expected.md (each cites the
JD rule that forces it). Run:  python test_extract_eoi.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_eoi import extract  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "fixtures", "eoi-sample-01.md")


def main():
    with open(FIXTURE, encoding="utf-8") as f:
        result = extract(f.read())
    job, flags = result["job"], result["flags"]
    failures = []

    def check(label, actual, expected):
        if actual != expected:
            failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    # JD-1 creation defaults
    check("region (JD-1.1)", job["region"], "SEQ1")
    check("template (JD-1.3)", job["initial_template"], "Pre Sales Investor v1")
    check("client name (JD-1.4)", job["client_name"], "WEI CHEN")

    # JD-2 site address
    check("address1 (JD-2.1)", job["address1"], "New Road")
    check("address2 (JD-2.3)", job["address2"], "(Scenic Rise Estate)")
    check("suburb CAPS (JD-2.4)", job["suburb"], "KARANA DOWNS")
    check("state (JD-2.5)", job["state"], "QLD")
    check("job name (JD-2.7)", job["job_name"],
          "LOT 42.(New Road).KARANA DOWNS <postcode>")
    check("land_registered", job["land_registered"], False)

    # JD-3 details
    check("stage (JD-3.1)", job["stage"], "3")
    check("design type (JD-3.2)", job["design_type"], "Standard")
    check("design name (JD-3.3)", job["design_name"], "Aspen 24")
    check("facade (JD-3.3)", job["facade"], "Coastal")
    check("investment (JD-3.4)", job["investment"], True)
    check("certifier (JD-3.6)", job["private_certifier"], "Buildable")
    check("marketer company CAPS (JD-3.9)", job["marketer_company"],
          "SUNRISE PROPERTY MARKETING")
    check("marketer contact (JD-3.9)", job["marketer_contact"], "Jordan BLAKE")

    # JD-4/5 constants
    check("activities (JD-4.1)", job["activities_to_complete"], [1, 2, 6])
    check("subject (JD-5)", job["attachment_subject"], "NEW JOB")

    # JD-6 price
    check("price (JD-6.1)", job["contract_price"], "438750")
    check("price incl GST", job["price_gst"], True)

    # JD-7 contacts
    check("client addr suburb CAPS (JD-7.1)",
          (job["client_address"] or {}).get("suburb"), "CHERMSIDE")
    check("client mobile (JD-7.2)", job["client_mobile"], "0400 000 001")
    check("client email (JD-7.2)", job["client_email"], "wei.chen@example.test")
    check("primary comm (JD-7.2)", job["primary_comm"], "Email")
    check("purchaser slot (JD-7.3)", job["purchaser_slot"], "Primary")
    check("sales relationship (JD-7.4)", job["sales_relationship"], "SALES")
    check("marketer relationship (JD-7.5)", job["marketer_relationship"],
          "MARKETER_ cc in all emails")
    check("sales consultant", job["sales_consultant"], "Priya Nair")

    # Mandatory verification flags (never asserted from memory)
    for needle, rule in [("postcode", "JD-2.6"), ("Council", "JD-3.7"),
                         ("PLAN", "JD-2.1")]:
        if not any(needle.lower() in f.lower() for f in flags):
            failures.append(f"missing flag containing {needle!r} ({rule})")

    if failures:
        print(f"FAIL - {len(failures)} mismatch(es):")
        for f in failures:
            print("  -", f)
        return 1
    print(f"PASS - all checks OK ({len(flags)} human-attention flags raised)")
    return 0


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
