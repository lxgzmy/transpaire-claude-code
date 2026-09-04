#!/usr/bin/env python3
"""Regression for the BA report draft pipeline — synthetic data only.

Builds a synthetic last-week report and per-job OSC snapshots in a temp
folder (fake job numbers, fake names — org rule: no real data in the repo
or in tests), runs the parse + draft steps, and asserts the core rules:

  1. carry-forward: rows and officer-entered values survive untouched
  2. date columns fill from complete OSC activities (with evidence)
  3. an outstanding item with fresh completion evidence is dropped
  4. an item with only pre-existing (older) evidence is kept and flagged
  5. an item with no evidence is kept and flagged
  6. a pending BA-relevant activity with no carried item is proposed-add
  7. ageing: first-seen persists in state; days/flags computed vs asof
  8. a job without a snapshot is carried forward untouched and flagged

Usage:  python regress_ba_report.py            (exit 0 = all pass)
"""
import json
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min
from ba_report_draft import build_draft
from ba_report_parse import EPOCH, parse_report

ASOF = "2026-09-07"          # the Monday being drafted
PREV = "2026-08-31"          # last week's report date (in the filename)
S = xlsx_min.S_WRAP


def serial(iso):
    return (date.fromisoformat(iso) - EPOCH).days


def synth_prev_report(path):
    header = ["Job No.", "Marketer", "Job Address", "Submit for BA",
              "Received RFI", "Received Covenant Approval",
              "Submit all RFI Items", "BA Received", "Deposit Paid",
              "Nominate Site Start", "Site Start (Physical)"]
    rows = [
        [(h, xlsx_min.S_HEADER) for h in header],
        # complete job — everything dated, must carry through untouched
        [("90001", S), ("SYNTH CO", S), ("Lot 1, 1 Example St, NOWHERE NSW 0000", S),
         (serial("2026-06-01"), S), (serial("2026-06-20"), S), (serial("2026-06-15"), S),
         (serial("2026-08-01"), S), (serial("2026-08-02"), S), (serial("2026-08-05"), S),
         (serial("2026-08-10"), S), (serial("2026-08-20"), S)],
        # in-flight job with three items: fresh-evidence, old-evidence, none
        [("90002", S), ("SYNTH CO", S), ("Lot 2, 2 Example St, NOWHERE NSW 0000", S),
         (serial("2026-07-01"), S), (serial("2026-07-20"), S), ("", S),
         ("PENDING ENGINEERING (REVIEW), ENERGY REPORT, CONTRIBUTIONS PAYABLE", S),
         ("", S), ("", S), ("", S), ("", S)],
        # in-flight job whose snapshot is missing
        [("90003", S), ("SYNTH CO", S), ("Lot 3, 3 Example St, NOWHERE QLD 0000", S),
         (serial("2026-07-10"), S), ("AWAITING RFI", S), ("", S),
         ("PENDING COVENANT APPROVAL", S), ("", S), ("", S), ("", S), ("", S)],
    ]
    xlsx_min.write_xlsx(path, rows)


def synth_snapshot_90002():
    def act(seq, desc, done=None, na=False, user=None, sp=None):
        return {"sequence": seq, "description": desc,
                "completionDate": f"{done}T00:00:00Z" if done else None,
                "isNotApplicable": na, "serviceProvider": sp,
                "user": user, "hasAlerts": False}
    return {
        "retrievedAtUtc": f"{ASOF}T00:00:00Z",
        "contractNumber": "90002", "jobID": "00000000-0000-0000-0000-000000000002",
        "clientName": "Synthetic Client", "state": "NSW",
        "workflowStatusName": "3. Pre-Construction",
        "activities": [
            act(52, "Submit Documents to Private Certifier for Building Approval Application", done="2026-07-01"),
            act(60, "Receive RFI from Certifier", done="2026-07-20"),
            # covenant complete AFTER the prev report -> column F should fill
            act(58, "Receive Covenant Approval & Upload to OSC", done="2026-09-02"),
            # engineering chain complete this week -> item dropped w/ evidence
            act(53, "Receive Engineering - Piers, Footings & Slab Design", done="2026-09-01"),
            act(54, "Review Engineering - Piers, Footings & Slab Design", done="2026-09-02"),
            act(56, "Forward Engineers Footing/Slab Design to Private Certiifier", done="2026-09-03"),
            # insurances pending -> proposed-add with owner
            act(72, "Pay Q Leave / Long Service Levy", user="Synthetic Admin"),
            act(76, "Email Copy of Relevant Insurances to Certifier", user="Synthetic Admin"),
            act(62, "Return RFI Information to Certifier"),
        ],
        "alerts": [],
        "documents": [
            # energy report attached BEFORE the prev report -> kept + flagged
            {"documentID": "00000000-0000-0000-0000-00000000d001",
             "description": "ENERGY REPORT - LOT 2", "extension": ".pdf",
             "version": 1, "attachedOnUtc": "2026-08-15T00:00:00Z"},
        ],
    }


def main():
    tmp = Path(tempfile.mkdtemp(prefix="ba-regress-"))
    failures = []

    def check(name, cond, detail=""):
        print(("PASS  " if cond else "FAIL  ") + name + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    try:
        prev = tmp / f"BA REPORT - 31.08.2026.xlsx"
        synth_prev_report(prev)

        parsed = parse_report(prev)
        check("parse: 3 job rows", len(parsed["rows"]) == 3)
        r2 = parsed["rows"][1]
        check("parse: item split", [i["name"] for i in r2["submit_all_rfi_items"]["items"]]
              == ["AMENDED", "ENERGY REPORT", "CONTRIBUTIONS PAYABLE"]
              or [i["name"] for i in r2["submit_all_rfi_items"]["items"]]
              == ["ENGINEERING", "ENERGY REPORT", "CONTRIBUTIONS PAYABLE"],
              str(r2["submit_all_rfi_items"]["items"]))

        snaps = tmp / "snaps"
        snaps.mkdir()
        (snaps / "90002.json").write_text(json.dumps(synth_snapshot_90002()), encoding="utf-8")
        out = tmp / "out"
        state_dir = tmp / "state"

        draft_path, ev_md, ev = build_draft(prev, snaps, out, asof=ASOF, state_dir=state_dir)
        jobs = {j["job_no"]: j for j in ev["jobs"]}

        j1 = jobs["90001"]
        check("complete job untouched", not j1["changes"] and not j1["outstanding"])

        j2 = jobs["90002"]
        actions = {(c.get("item") or c.get("column")): c["action"] for c in j2["changes"]}
        check("engineering dropped (fresh evidence)", actions.get("ENGINEERING") == "dropped",
              str(actions))
        check("covenant date filled", actions.get("received_covenant") == "filled", str(actions))
        kept = {i["name"]: i for i in j2["outstanding"]}
        check("energy kept + flagged (old evidence)",
              "ENERGY REPORT" in kept and kept["ENERGY REPORT"]["flagged"])
        check("contributions kept + flagged (no evidence)",
              "CONTRIBUTIONS PAYABLE" in kept and kept["CONTRIBUTIONS PAYABLE"]["flagged"])
        check("insurances proposed-add", actions.get("INSURANCES") == "proposed-add", str(actions))
        check("proposed item has owner", kept.get("INSURANCES", {}).get("owner") == "Synthetic Admin")
        days = {i["name"]: i["days"] for i in j2["outstanding"]}
        check("ageing from prev report date", days.get("ENERGY REPORT") == 7, str(days))
        check("ageing red flag past threshold",
              kept["ENERGY REPORT"]["flag"] == "RED", str(kept.get("ENERGY REPORT")))

        j3 = jobs["90003"]
        check("no-snapshot job flagged", any("no snapshot" in f for f in j3["flags"]))
        check("no-snapshot items carried", [i["name"] for i in j3["outstanding"]] == ["COVENANT APPROVAL"])

        state = json.loads((state_dir / "ba-items-first-seen.json").read_text(encoding="utf-8"))
        check("first-seen persisted", state.get("90002", {}).get("ENERGY REPORT") == PREV, str(state))

        # second run a week later: ageing must grow from persisted first-seen
        _, _, ev2 = build_draft(draft_path, snaps, out, asof="2026-09-14", state_dir=state_dir)
        j2b = {j["job_no"]: j for j in ev2["jobs"]}["90002"]
        days2 = {i["name"]: i["days"] for i in j2b["outstanding"]}
        check("ageing accumulates across runs", days2.get("ENERGY REPORT") == 14, str(days2))

        reparsed = parse_report(draft_path)
        check("draft is itself parseable", len(reparsed["rows"]) == 3)
        g2 = [r for r in reparsed["rows"] if r["job_no"] == "90002"][0]["submit_all_rfi_items"]
        check("draft G column readable as items",
              g2["pending"] and "INSURANCES" in [i["name"] for i in g2["items"]],
              str(g2["items"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
