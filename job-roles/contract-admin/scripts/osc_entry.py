"""OSC new-job entry — pywinauto SKELETON. NOT RUNNABLE against live OSC yet.

Status per contract-admin/CLAUDE.md: OSC write-automation is deferred until the
technical session confirms the integration surfaces. This file exists so that
session has a concrete starting point. Every control identifier below is a
TODO placeholder that must be captured on the server with OSC open, using:

    python -m pywinauto.print_control_identifiers  (or inspect.exe)

Design (mirrors ../workflows/new-job.md Phase 1):
  - Input is the JSON draft sheet from extract_eoi.py, already human-reviewed.
  - DRY-RUN IS THE DEFAULT: prints what each step would do, touches nothing.
  - Live mode requires --live AND a typed confirmation, and still pauses for
    per-screen human approval (HITL gate before every OSC write).
  - Steps that must stay human are not automated: duplicate lot search result
    judgment, DataBuild email send, price-mismatch resolution.

Usage:
    python osc_entry.py job.json              # dry-run (default)
    python osc_entry.py job.json --live       # blocked until TODOs resolved
"""

import argparse
import json
import sys

# TODO(server): confirm executable path / process name for OnSite Companion.
OSC_EXE = r"TODO\path\to\OnSiteCompanion.exe"

# TODO(server): every string below is a guess from the manual's screenshots.
# Replace with real titles/auto_ids from print_control_identifiers().
CTRL = {
    "main_window": "TODO OnSite main window title re",
    "jobs_nav": "TODO Jobs navigation item",
    "new_job_btn": "TODO green + button auto_id",
    "region_pencil": "TODO region edit pencil",
    "generate_contract_no": "TODO Generate Contract No button",
    "template_pencil": "TODO initial-template pencil",
    "create_job_btn": "TODO Create Job button",
    "address_pencil": "TODO site-address pencil (top left)",
    "save_refresh": "TODO Save and Refresh button",
    "job_activities_tab": "TODO Job Activities tab",
    "contact_details_tab": "TODO Contact Details tab",
    "save_close": "TODO Save and Close button",
}

LIVE = False


def confirm(step):
    """HITL gate: a human approves every screen before it is written."""
    if not LIVE:
        return True
    answer = input(f"  APPROVE '{step}'? [y/N] ").strip().lower()
    return answer == "y"


def act(step, detail):
    """Perform (live) or narrate (dry-run) one UI action."""
    mode = "LIVE" if LIVE else "dry-run"
    print(f"[{mode}] {step}: {detail}")
    if LIVE:
        # TODO(server): real pywinauto calls go here per step, e.g.
        #   app.window(title_re=CTRL["main_window"]) \
        #      .child_window(auto_id=CTRL["new_job_btn"]).click()
        raise NotImplementedError(f"control mapping pending for: {step}")


def run(job):
    # Manual step 2-3: open Jobs, new job. (Step 2's duplicate-search JUDGMENT
    # stays human - the script only reminds.)
    print(f"REMINDER (JD-0.2): human must search OSC for lot {job['lot']} "
          f"({job.get('estate')}) and confirm NO existing job before continuing.")
    if not confirm("duplicate check done, create job"):
        return 1

    # Manual step 4: creation dialog (JD-1)
    act("4a region", f"set Region = {job['region']}")
    act("4b contract no", "click Generate Contract No")
    act("4c template", f"set Initial Template = {job['initial_template']}")
    act("4d client", f"Create New Client = {job['client_name']}")
    if not confirm("Create Job (4e)"):
        return 1
    act("4e create", "click Create Job")

    # Manual step 5: site address (JD-2)
    act("5 address", f"Address1={job['address1']!r}, Address2={job['address2']!r}, "
        f"Suburb={job['suburb']}, State={job['state']}, "
        f"Postcode=<human-verified value>")
    act("save", "Save and Refresh (JD-3.10)")

    # Manual step 6: job details (JD-3)
    act("6 details", f"Stage={job['stage']}, DesignType={job['design_type']}, "
        f"Design={job['design_name']} / {job['facade']}, "
        f"Investment={job['investment']}, Certifier={job['private_certifier']}, "
        f"Council=<human-verified value>, Marketer={job['marketer_company']} / "
        f"{job['marketer_contact']}")
    act("save", "Save and Refresh (JD-3.10)")

    # Manual step 7: activities (JD-4)
    act("7 activities", f"complete items {job['activities_to_complete']} "
        "(1,2: double-click Completion + OK; 6: + tick box in pop-up)")

    # Manual step 8: attach request email (JD-5)
    act("8 attach", f"attach request email at JOB and Item 11, "
        f"Subject={job['attachment_subject']!r}, mark Item 11 complete")

    # Manual step 9 stays fully human: send the DataBuild email (JD-6.1).
    print("HUMAN STEP (JD-6.1): send the drafted DataBuild email "
          "(full project name + contract price). Not automated.")

    # Manual step 10: contact details (JD-7)
    ca = job.get("client_address") or {}
    act("10 contacts", f"client addr={ca}, mobile={job['client_mobile']}, "
        f"email={job['client_email']}, PrimaryComm={job['primary_comm']}, "
        f"slot={job['purchaser_slot']}, sales={job['sales_consultant']} "
        f"[{job['sales_relationship']}], marketer [{job['marketer_relationship']}]")
    act("save", "Save and Close (JD-7.7)")

    print("HUMAN STEP (JD-6.2): on DataBuild confirmation, compare price vs "
          f"request email (expect {job['contract_price']}). Mismatch = stop.")
    return 0


def main():
    global LIVE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("job_json", help="reviewed draft sheet from extract_eoi.py")
    ap.add_argument("--live", action="store_true",
                    help="drive OSC for real (blocked until control mapping done)")
    args = ap.parse_args()

    with open(args.job_json, encoding="utf-8") as f:
        result = json.load(f)
    job, flags = result["job"], result.get("flags", [])

    if flags:
        print(f"{len(flags)} unresolved flag(s) from extraction:")
        for f_ in flags:
            print("  -", f_)
        print("A human must resolve/acknowledge these before entry.\n")

    if args.live:
        try:
            import pywinauto  # noqa: F401
        except ImportError:
            print("pywinauto not installed - live mode unavailable.")
            return 2
        if "TODO" in OSC_EXE:
            print("Control mapping not captured yet - live mode is blocked "
                  "until the technical session (see module docstring).")
            return 2
        typed = input("Type EXACTLY 'approve live entry' to proceed: ")
        if typed != "approve live entry":
            print("Not approved - exiting.")
            return 1
        LIVE = True

    return run(job)


if __name__ == "__main__":
    sys.exit(main())
