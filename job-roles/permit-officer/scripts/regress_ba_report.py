#!/usr/bin/env python3
"""Regression for the BA report draft pipeline — synthetic data only.

Builds a synthetic last-week report and per-job OSC snapshots in a temp
folder (fake job numbers, fake names — org rule: no real data in the repo
or in tests), runs the parse + draft + compare steps, and asserts:

  1. carry-forward: rows and officer-entered values survive untouched
  2. date columns fill from complete OSC activities (with evidence)
  3. an item with fresh completion evidence is RESOLVED: shown once on a
     RESOLVED line with date + frozen business days, then dropped next run
  4. an item with only pre-existing (older) evidence is kept and flagged
  5. an item with no evidence is kept and flagged
  6. a pending BA-relevant activity with no carried item is proposed-add
  7. ageing v0.2: business days from DATE SUBMITTED; tier from who the item
     is with (officer text > "(W/O X)" > OSC owner > item type); YELLOW at or
     under the tier threshold, RED over; "(assumed)" when the date is guessed
  8. officer-typed Assigned-to / Date submitted win and stick across runs
  9. L-O lines that do not line up with G are ignored and flagged
 10. all items resolved -> G becomes the Return-RFI date (or blank + flag)
 11. --jobs: non-pilot rows carry forward verbatim with L-O blank; a pilot
     job missing from the base is noted, never fabricated
 12. a job without a snapshot is carried forward untouched and flagged
 13. v0.1 state (ISO string per item) upgrades to the v0.2 dict shape
 14. business_days boundaries and NSW holidays
 15. the draft round-trips through ba_report_parse and compare_ba_report

Usage:  python regress_ba_report.py            (exit 0 = all pass)
"""
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min
from ba_report_draft import TIERS, build_draft, load_state, submitted_evidence
from ba_report_parse import EPOCH, parse_report
from compare_ba_report import compare
from nsw_holidays import business_days

ASOF = "2026-09-07"          # the Monday being drafted
PREV = "2026-08-31"          # last week's report date (in the filename)
ASOF2 = "2026-09-14"         # the following Monday
S = xlsx_min.S_WRAP
HEADER = ["Job No.", "Marketer", "Job Address", "Submit for BA",
          "Received RFI", "Received Covenant Approval",
          "Submit all RFI Items", "BA Received", "Deposit Paid",
          "Nominate Site Start", "Site Start (Physical)"]
ITEM_HEADER = ["Assigned to", "Date submitted", "Date resolved", "Days outstanding"]


def serial(iso):
    return (date.fromisoformat(iso) - EPOCH).days


def synth_prev_report(path):
    rows = [
        [(h, xlsx_min.S_HEADER) for h in HEADER],
        # complete job — everything dated, must carry through untouched
        [("90001", S), ("SYNTH CO", S), ("Lot 1, 1 Example St, NOWHERE NSW 0000", S),
         (serial("2026-06-01"), S), (serial("2026-06-20"), S), (serial("2026-06-15"), S),
         (serial("2026-08-01"), S), (serial("2026-08-02"), S), (serial("2026-08-05"), S),
         (serial("2026-08-10"), S), (serial("2026-08-20"), S)],
        # in-flight job: fresh-evidence, old-evidence, none (waiting on council)
        [("90002", S), ("SYNTH CO", S), ("Lot 2, 2 Example St, NOWHERE NSW 0000", S),
         (serial("2026-07-01"), S), (serial("2026-07-20"), S), ("", S),
         ("PENDING ENGINEERING (REVIEW), ENERGY REPORT, CONTRIBUTIONS PAYABLE (W/O COUNCIL)", S),
         ("", S), ("", S), ("", S), ("", S)],
        # in-flight job whose snapshot is missing
        [("90003", S), ("SYNTH CO", S), ("Lot 3, 3 Example St, NOWHERE QLD 0000", S),
         (serial("2026-07-10"), S), ("AWAITING RFI", S), ("", S),
         ("PENDING COVENANT APPROVAL", S), ("", S), ("", S), ("", S), ("", S)],
        # non-pilot in-flight job — must carry forward verbatim under --jobs
        [("90004", S), ("SYNTH CO", S), ("Lot 4, 4 Example St, NOWHERE NSW 0000", S),
         (serial("2026-07-12"), S), (serial("2026-08-01"), S), ("", S),
         ("PENDING S68 APPLICATION", S), ("", S), ("", S), ("", S), ("", S)],
        # all items resolve this week -> G becomes the Return RFI date
        [("90005", S), ("SYNTH CO", S), ("Lot 5, 5 Example St, NOWHERE NSW 0000", S),
         (serial("2026-07-15"), S), (serial("2026-08-03"), S), ("", S),
         ("PENDING COVENANT APPROVAL", S), ("", S), ("", S), ("", S), ("", S)],
    ]
    xlsx_min.write_xlsx(path, rows)


def act(seq, desc, done=None, na=False, user=None, sp=None):
    return {"sequence": seq, "description": desc,
            "completionDate": f"{done}T00:00:00Z" if done else None,
            "isNotApplicable": na, "serviceProvider": sp,
            "user": user, "hasAlerts": False}


def doc(i, desc, attached):
    return {"documentID": f"00000000-0000-0000-0000-0000000{i:05d}",
            "description": desc, "extension": ".pdf", "version": 1,
            "attachedOnUtc": f"{attached}T00:00:00Z"}


def synth_snapshot_90002():
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
            # engineering chain complete this week -> item RESOLVED w/ evidence
            act(53, "Receive Engineering - Piers, Footings & Slab Design", done="2026-09-01"),
            act(54, "Review Engineering - Piers, Footings & Slab Design", done="2026-09-02"),
            act(56, "Forward Engineers Footing/Slab Design to Private Certiifier", done="2026-09-03"),
            # insurances pending with an internal owner -> proposed-add, INTERNAL tier
            act(72, "Pay Q Leave / Long Service Levy", user="Synthetic Admin"),
            act(76, "Email Copy of Relevant Insurances to Certifier", user="Synthetic Admin"),
            act(62, "Return RFI Information to Certifier"),
        ],
        "alerts": [],
        "documents": [
            # energy report attached BEFORE the prev report -> kept + flagged
            doc(1, "ENERGY REPORT - LOT 2", "2026-08-15"),
            # energy application ordered 10 Aug -> DATE SUBMITTED evidence
            doc(2, "ENERGY APPLICATION - LOT 2", "2026-08-10"),
        ],
    }


def synth_snapshot_90005():
    return {
        "retrievedAtUtc": f"{ASOF}T00:00:00Z",
        "contractNumber": "90005", "jobID": "00000000-0000-0000-0000-000000000005",
        "clientName": "Synthetic Client", "state": "NSW",
        "workflowStatusName": "3. Pre-Construction",
        "activities": [
            act(52, "Submit Documents to Private Certifier for Building Approval Application", done="2026-07-15"),
            act(60, "Receive RFI from Certifier", done="2026-08-03"),
            act(57, "Submit Covenant Application", done="2026-08-05"),
            act(58, "Receive Covenant Approval & Upload to OSC", done="2026-09-02"),
            act(62, "Return RFI Information to Certifier", done="2026-09-04"),
        ],
        "alerts": [], "documents": [],
    }


def synth_officer_report_week2(path):
    """The officer's corrected copy of the week-1 draft, with L-O typed in.

    Row 90002 keeps ENERGY REPORT and CONTRIBUTIONS; the officer types
    "Drafting" against energy (INTERNAL tier) and moves the contributions
    submitted date to 20/08/2026. Row 90003 has L-O lines that do not line
    up with G (three lines, one item).
    """
    rows = [
        [(h, xlsx_min.S_HEADER) for h in HEADER + ITEM_HEADER],
        [("90002", S), ("SYNTH CO", S), ("Lot 2, 2 Example St, NOWHERE NSW 0000", S),
         (serial("2026-07-01"), S), (serial("2026-07-20"), S), (serial("2026-09-02"), S),
         ("PENDING ENERGY REPORT, CONTRIBUTIONS PAYABLE (W/O COUNCIL), INSURANCES (PROPOSED)", S),
         ("", S), ("", S), ("", S), ("", S),
         ("Drafting\nCouncil\nSynthetic Admin", S),
         ("10/08/2026\n20/08/2026\n03/09/2026", S),
         ("\n\n", S),
         ("20 RED\n5 YELLOW\n2 YELLOW", S)],
        [("90003", S), ("SYNTH CO", S), ("Lot 3, 3 Example St, NOWHERE QLD 0000", S),
         (serial("2026-07-10"), S), ("AWAITING RFI", S), ("", S),
         ("PENDING COVENANT APPROVAL", S), ("", S), ("", S), ("", S), ("", S),
         ("Developer\nSomeone\nElse", S), ("01/08/2026\n\n", S), ("\n\n", S), ("9 YELLOW\n\n", S)],
    ]
    xlsx_min.write_xlsx(path, rows)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="ba-regress-"))
    failures = []

    def check(name, cond, detail=""):
        print(("PASS  " if cond else "FAIL  ") + name + (f" — {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    try:
        # ---- 14. business days
        check("bdays: Monday to next Monday = 5", business_days("2026-08-31", "2026-09-07") == 5)
        check("bdays: two weeks = 10 (edge of INTERNAL tier)", business_days("2026-08-24", "2026-09-07") == 10)
        check("bdays: Labour Day 5 Oct excluded", business_days("2026-09-28", "2026-10-12") == 9)
        check("bdays: same day / reversed = 0",
              business_days("2026-09-07", "2026-09-07") == 0 and business_days("2026-09-08", "2026-09-07") == 0)

        prev = tmp / f"BA REPORT - {PREV[8:]}.{PREV[5:7]}.{PREV[:4]}.xlsx"
        synth_prev_report(prev)
        parsed = parse_report(prev)
        check("parse: 5 job rows", len(parsed["rows"]) == 5)
        r2 = parsed["rows"][1]
        names = [i["name"] for i in r2["submit_all_rfi_items"]["items"]]
        check("parse: item split", names == ["ENGINEERING", "ENERGY REPORT", "CONTRIBUTIONS PAYABLE"], str(names))
        check("parse: W/O state kept", r2["submit_all_rfi_items"]["items"][2]["state"] == "W/O COUNCIL")
        check("parse: no L-O on an export", r2["submit_all_rfi_items"].get("item_cols_present") is False)

        # ---- 13. v0.1 state upgrade
        state_dir = tmp / "state"
        state_dir.mkdir()
        (state_dir / "ba-items-first-seen.json").write_text(
            json.dumps({"90002": {"ENERGY REPORT": "2026-08-24"}}), encoding="utf-8")
        st = load_state(state_dir)
        check("state: v0.1 string upgrades to dict", st["90002"]["ENERGY REPORT"] == {"first_seen": "2026-08-24"})

        snaps = tmp / "snaps"
        snaps.mkdir()
        (snaps / "90002.json").write_text(json.dumps(synth_snapshot_90002()), encoding="utf-8")
        (snaps / "90005.json").write_text(json.dumps(synth_snapshot_90005()), encoding="utf-8")
        out = tmp / "out"
        pilot = ["90001", "90002", "90003", "90005", "90099"]

        draft_path, ev_md, ev = build_draft(prev, snaps, out, asof=ASOF, state_dir=state_dir, jobs=pilot)
        jobs = {j["job_no"]: j for j in ev["jobs"]}

        j1 = jobs["90001"]
        check("complete job untouched", not j1["changes"] and not j1["outstanding"] and not j1["resolved"])

        j2 = jobs["90002"]
        actions = {(c.get("item") or c.get("column")): c["action"] for c in j2["changes"]}
        check("engineering resolved (fresh evidence)", actions.get("ENGINEERING") == "resolved", str(actions))
        check("covenant date filled", actions.get("received_covenant") == "filled", str(actions))
        res = {i["name"]: i for i in j2["resolved"]}
        check("resolved carries date + frozen days",
              res.get("ENGINEERING", {}).get("date_resolved") == "2026-09-03"
              and res["ENGINEERING"]["flag"] == "" and isinstance(res["ENGINEERING"]["days"], int),
              str(res.get("ENGINEERING")))
        kept = {i["name"]: i for i in j2["outstanding"]}
        check("energy kept + flagged (old evidence)",
              "ENERGY REPORT" in kept and kept["ENERGY REPORT"]["flagged"])
        check("contributions kept + flagged (no evidence)",
              "CONTRIBUTIONS PAYABLE" in kept and kept["CONTRIBUTIONS PAYABLE"]["flagged"])
        check("insurances proposed-add", actions.get("INSURANCES") == "proposed-add", str(actions))

        # ---- 7. ageing v0.2
        en = kept.get("ENERGY REPORT", {})
        check("energy: date submitted from ENERGY APPLICATION doc",
              en.get("date_submitted") == "2026-08-10" and (en.get("date_source") or "").startswith("osc"),
              str(en))
        check("energy: tier ENERGY from item type, 20 business days RED",
              en.get("tier") == "ENERGY" and en.get("days") == 20 and en.get("flag") == "RED", str(en))
        co = kept.get("CONTRIBUTIONS PAYABLE", {})
        check("contributions: assigned COUNCIL from (W/O COUNCIL), tier COUNCIL",
              co.get("assigned_to") == "COUNCIL" and co.get("tier") == "COUNCIL", str(co))
        check("contributions: date assumed from first sighting, 5 days YELLOW (assumed)",
              co.get("date_submitted") == PREV and co.get("days") == 5 and co.get("flag") == "YELLOW"
              and co.get("assumed") is True, str(co))
        ins = kept.get("INSURANCES", {})
        check("insurances: OSC user -> INTERNAL tier, owner named",
              ins.get("assigned_to") == "Synthetic Admin" and ins.get("tier") == "INTERNAL", str(ins))
        check("insurances: no handover evidence -> date assumed, flagged",
              ins.get("date_submitted") == PREV and ins.get("assumed") is True and ins.get("flag") == "YELLOW",
              str(ins))
        # date-submitted evidence: Order -> Receive pairing, same-chain predecessor, unrelated ignored
        mini = {"activities": [
            act(46, "Order Engineering - Structural Steel", done="2026-08-20", sp="Synth Eng"),
            act(47, "Complete Colour Selections & Save into OSC", done="2026-09-01"),
            act(53, "Receive Engineering - Structural Steel", sp="Synth Eng"),
        ], "alerts": [], "documents": []}
        d, why = submitted_evidence({"name": "ENGINEERING"}, mini)
        check("date evidence: Receive <- matching Order step", d == "2026-08-20" and "Order" in why, f"{d} {why}")
        mini2 = {"activities": [
            act(57, "Submit Covenant Application", done="2026-08-25"),
            act(58, "Receive Covenant Approval & Upload to OSC"),
        ], "alerts": [], "documents": []}
        d2, why2 = submitted_evidence({"name": "COVENANT"}, mini2)
        check("date evidence: same-chain predecessor", d2 == "2026-08-25", f"{d2} {why2}")
        mini3 = {"activities": [
            act(71, "Create BA & Finance Approved Purchase Orders within Databuild", done="2026-09-01"),
            act(72, "Pay Q Leave / Long Service Levy", user="Synthetic Admin"),
        ], "alerts": [], "documents": []}
        check("date evidence: unrelated predecessor ignored",
              submitted_evidence({"name": "INSURANCES"}, mini3) == (None, None))
        mini4 = {"activities": [], "documents": [], "alerts": [
            {"alertID": "x1", "subject": "LODGE FOR CC", "createdBy": "Synth", "createdOnUtc": "2026-01-28T00:00:00Z"},
            {"alertID": "x2", "subject": "Re: LODGEMENT - amended", "createdBy": "Synth", "createdOnUtc": "2026-08-20T00:00:00Z"},
        ]}
        d4, _ = submitted_evidence({"name": "AMENDED DA LODGEMENT"}, mini4, lodged_iso="2026-06-03")
        check("date evidence: pre-lodgement alerts ignored, later alert used", d4 == "2026-08-20", str(d4))
        check("thresholds are the confirmed tiers",
              TIERS == {"INTERNAL": 10, "ENERGY": 10, "EXTERNAL": 20, "COUNCIL": 30})

        # ---- 12. no snapshot
        j3 = jobs["90003"]
        check("no-snapshot job flagged", any("no snapshot" in f for f in j3["flags"]))
        check("no-snapshot items carried", [i["name"] for i in j3["outstanding"]] == ["COVENANT APPROVAL"])

        # ---- 11. --jobs scope
        j4 = jobs["90004"]
        check("non-pilot row: not aged, not flagged", j4["pilot"] is False and not j4["outstanding"]
              and not j4["flags"] and not j4["changes"])
        check("pilot job missing from base is noted", any("90099" in n for n in ev["notes"]), str(ev["notes"]))

        # ---- 10. all resolved
        j5 = jobs["90005"]
        acts5 = {(c.get("item") or c.get("column")): c for c in j5["changes"]}
        check("all resolved: covenant resolved", acts5.get("COVENANT APPROVAL", {}).get("action") == "resolved")
        check("all resolved: G filled with Return RFI date",
              acts5.get("submit_all_rfi_items", {}).get("value") == "2026-09-04", str(acts5))

        # ---- state persisted in dict shape
        state = load_state(state_dir)
        e = state.get("90002", {}).get("CONTRIBUTIONS", {})
        check("state: dict per item with first_seen + ai_* mirrors",
              e.get("first_seen") == PREV and e.get("ai_assigned_to") == "COUNCIL"
              and e.get("ai_date_submitted") == PREV, str(e))
        check("state: resolved item removed", "ENGINEERING" not in state.get("90002", {}))

        # ---- 15. round trip + workbook shape
        reparsed = parse_report(draft_path)
        check("draft is itself parseable", len(reparsed["rows"]) == 5)
        g2 = [r for r in reparsed["rows"] if r["job_no"] == "90002"][0]["submit_all_rfi_items"]
        check("draft G: pending items readable, RESOLVED line split off",
              g2["pending"] and [i["name"] for i in g2["items"]] == ["ENERGY REPORT", "CONTRIBUTIONS PAYABLE", "INSURANCES"]
              and [i["name"] for i in g2["resolved"]] == ["ENGINEERING"]
              and g2["resolved"][0]["date_resolved"] == "2026-09-03", str(g2))
        check("draft L-O: aligned and read back",
              g2.get("item_cols_misaligned") is False
              and g2["items"][1]["assigned_to"] == "COUNCIL"
              and g2["items"][0]["date_submitted"] == "2026-08-10"
              and g2["items"][0]["days_outstanding"] == 20, str(g2["items"]))
        g4 = [r for r in reparsed["rows"] if r["job_no"] == "90004"][0]["submit_all_rfi_items"]
        check("non-pilot row: L-O blank", g4.get("item_cols_present") is False)
        g5 = [r for r in reparsed["rows"] if r["job_no"] == "90005"][0]["submit_all_rfi_items"]
        check("all resolved: G is a date in the workbook", g5["date"] == "2026-09-04" and not g5["pending"])

        # ---- 3. second run: resolved line dropped, ageing grows in business days
        _, _, ev2 = build_draft(draft_path, snaps, out, asof=ASOF2, state_dir=state_dir, jobs=pilot)
        j2b = {j["job_no"]: j for j in ev2["jobs"]}["90002"]
        acts2 = {(c.get("item") or c.get("column")): c["action"] for c in j2b["changes"]}
        check("run 2: RESOLVED line not carried", acts2.get("ENGINEERING") == "resolved-line-dropped"
              and not any(i["name"] == "ENGINEERING" for i in j2b["outstanding"] + j2b["resolved"]), str(acts2))
        days2 = {i["name"]: i["days"] for i in j2b["outstanding"]}
        check("run 2: energy ageing grows 20 -> 25 business days", days2.get("ENERGY REPORT") == 25, str(days2))

        # ---- 8 + 9. officer overrides and misaligned L-O (week-2 base typed by the officer)
        officer = tmp / f"BA REPORT - 14.09.2026.xlsx"
        synth_officer_report_week2(officer)
        _, _, ev3 = build_draft(officer, snaps, out, asof="2026-09-21", state_dir=state_dir, jobs=pilot)
        j2c = {j["job_no"]: j for j in ev3["jobs"]}["90002"]
        k3 = {i["name"]: i for i in j2c["outstanding"]}
        en3 = k3.get("ENERGY REPORT", {})
        check("officer Assigned-to 'Drafting' wins -> INTERNAL tier",
              en3.get("assigned_to") == "Drafting" and en3.get("assigned_source") == "officer"
              and en3.get("tier") == "INTERNAL", str(en3))
        check("officer-echoed AI date is re-derived, same value",
              en3.get("date_submitted") == "2026-08-10", str(en3))
        co3 = k3.get("CONTRIBUTIONS PAYABLE", {})
        check("officer Date submitted 20/08 wins, business days from it",
              co3.get("date_submitted") == "2026-08-20" and co3.get("date_source") == "officer"
              and co3.get("days") == business_days("2026-08-20", "2026-09-21"), str(co3))
        j3c = {j["job_no"]: j for j in ev3["jobs"]}["90003"]
        check("misaligned L-O ignored + flagged",
              any("do not line up" in f for f in j3c["flags"])
              and j3c["outstanding"][0].get("assigned_source") != "officer", str(j3c["flags"]))

        # ---- sticky across a base that lacks L-O (officer's plain export)
        plain = tmp / f"BA REPORT - 21.09.2026.xlsx"
        synth_prev_report(plain)  # same rows, no L-O
        _, _, ev4 = build_draft(plain, snaps, out, asof="2026-09-28", state_dir=state_dir, jobs=pilot)
        en4 = {i["name"]: i for i in {j["job_no"]: j for j in ev4["jobs"]}["90002"]["outstanding"]}.get("ENERGY REPORT", {})
        check("officer value sticks when the base has no L-O",
              en4.get("assigned_to") == "Drafting" and en4.get("assigned_source") == "officer", str(en4))

        # ---- compare scorecard
        rep = compare(draft_path, officer, ["90002", "90003", "90099"])
        check("compare: matched by family, missed/extra counted",
              rep["officer_items"] == 4 and rep["matched"] == 4 and rep["missed"] == 0, str(rep))
        check("compare: absent pilot job unscored", any(j["job_no"] == "90099" and not j["in_actual"] for j in rep["jobs"]))
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
