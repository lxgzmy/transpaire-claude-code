#!/usr/bin/env python3
"""Draft the Monday BA report from last week's report + OSC snapshots.

Deterministic merge (no network): reads last week's report (carry-forward
base, PO-10), per-job OSC snapshot JSONs saved by the MCP read step, and a
first-seen state file for ageing; writes a draft .xlsx plus an evidence
bundle to the output folder. Every change carries its evidence; anything
low-confidence is kept and flagged, never silently applied (org HITL rule).

Snapshot JSON shape (one file per job, ``<jobno>.json``, saved by the
workflow's MCP read step — see workflows/ba-weekly-report.md):

  {
    "retrievedAtUtc": "...", "contractNumber": "<jobno>", "jobID": "<guid>",
    "clientName": "...", "state": "NSW", "workflowStatusName": "...",
    "activities": [{"sequence", "description", "completionDate",
                    "isNotApplicable", "serviceProvider", "user", "hasAlerts"}],
    "alerts":     [{"alertID", "subject", "createdBy", "createdOnUtc"}],
    "documents":  [{"documentID", "description", "extension", "version",
                    "attachedOnUtc"}]
  }

Usage:
  python ba_report_draft.py --prev PREV.xlsx --snapshots DIR --out DIR
                            [--asof YYYY-MM-DD] [--state DIR]
                            [--amber-days 5] [--red-days 5]

Ageing default per discovery (PO-11, unconfirmed): amber while <= 5 days,
red beyond 5. The added ageing column is a PROPOSAL pending business
confirmation of the template.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min
from ba_report_parse import EPOCH, parse_report, serial_to_iso

# Report column -> OSC activity description (verified in
# reference/osc-field-map.md; substring match, case-insensitive).
COLUMN_ACTIVITY = {
    "submit_for_ba": "Submit Documents to Private Certifier for Building Approval",
    "received_rfi": "Receive RFI from Certifier",
    "received_covenant": "Receive Covenant Approval & Upload to OSC",
    "submit_all_rfi_items": "Return RFI Information to Certifier",
    "ba_received": "Building Approval Received from Certifier",
    "deposit_paid": "Receive Deposit Claim Payment",
    "nominate_site_start": "Nominate Site Start Date",
}

# Outstanding-item families: how a report item name maps to OSC evidence.
# done_activities: ALL must be complete/N-A for activity-based completion.
# done_docs: ANY document description match counts as completion evidence.
# pending_activities: any of these pending -> the item is active; the first
# pending one's assigned user is "who it is with".
FAMILIES = [
    {"key": "ENGINEERING",
     "match": r"\bENG(INEERING)?\b",
     "done_activities": [r"Receive Engineering", r"Review Engineering", r"Forward Engineers"],
     "pending_activities": [r"Receive Engineering", r"Review Engineering",
                            r"Amend Working Drawings to Suit", r"Forward Engineers"],
     "done_docs": []},
    {"key": "COVENANT",
     "match": r"\bCOV(ENANT)?\b",
     "done_activities": [r"Receive Covenant Approval"],
     "pending_activities": [r"Submit Covenant Application", r"Receive Covenant Approval",
                            r"Forward Covenant Application Approval"],
     "done_docs": [r"COVENANT.*APPROV"]},
    {"key": "INSURANCES",
     "match": r"\bINSURANCE(S)?\b",
     "done_activities": [r"Pay Q Leave", r"Pay QBCC", r"Pay Construction Works Insurance",
                         r"Email Copy of Relevant Insurances"],
     "pending_activities": [r"Pay Q Leave", r"Pay QBCC", r"Pay Construction Works Insurance",
                            r"Email Copy of Relevant Insurances"],
     "done_docs": []},
    {"key": "ENERGY",
     "match": r"\b(ENERGY|NATHERS)\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"ENERGY REPORT", r"NATHERS (REPORT|CERT)"]},
    {"key": "BASIX",
     "match": r"\bBASIX\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"BASIX (REPORT|CERT)"]},
    {"key": "S10.7",
     "match": r"10\.7",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"10\.7"]},
    {"key": "SYDNEY WATER",
     "match": r"\b(SYDNEY WATER|TAP.?IN)\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"SYDNEY WATER.*(APPROV|RECEIPT)", r"TAP.?IN.*APPROV"]},
    {"key": "ALTOGETHER",
     "match": r"\bALTOGETHER\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"ALTOGETHER.*APPROV"]},
    {"key": "WATER METER",
     "match": r"\bWATER METER\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"WATER METER.*(APPROV|RECEIPT)"]},
    {"key": "PLUMBING",
     "match": r"\bPLUMBING\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"PLUMBING.*APPROV", r"APPROVAL - PLUMBING"]},
    {"key": "DRIVEWAY",
     "match": r"\b(DRIVEWAY|DWY)\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"DRIVEWAY.*APPROV", r"APPROVAL - DRIVEWAY"]},
    {"key": "S68",
     "match": r"\bS(ECTION )?68\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"(APPROVAL - S(ECTION )?68|S(ECTION )?68.*APPROV)"]},
    {"key": "S307",
     "match": r"\bS(ECTION )?307\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"S(ECTION )?307.*(APPROV|CERT)"]},
    {"key": "CONTRIBUTIONS",
     "match": r"\bCONTRIBUTIONS?\b",
     "done_activities": [],
     "pending_activities": [],
     "done_docs": [r"(CONTRIBUTION.*(RECEIPT|PAID)|HPC.*RECEIPT|7\.1[12].*RECEIPT)"]},
]

# Pending activities that justify PROPOSING a new outstanding item when no
# carried item already covers the family.
PROPOSE_FROM_PENDING = {"ENGINEERING", "COVENANT", "INSURANCES"}


def _iso_day(s):
    return (s or "")[:10]


def family_of(item_name):
    for fam in FAMILIES:
        if re.search(fam["match"], item_name.upper()):
            return fam
    return None


def activity_state(snapshot, pattern):
    """Return (matched, all_complete, first_pending_activity)."""
    matched = [a for a in snapshot.get("activities", [])
               if re.search(pattern, a.get("description") or "", re.I)]
    if not matched:
        return False, False, None
    pending = [a for a in matched
               if not a.get("completionDate") and not a.get("isNotApplicable")]
    return True, not pending, (pending[0] if pending else None)


def doc_evidence(snapshot, patterns, since_iso):
    """Newest document matching any pattern; (doc, is_new_since)."""
    best = None
    for d in snapshot.get("documents", []):
        desc = (d.get("description") or "").upper()
        if any(re.search(p, desc) for p in patterns):
            if best is None or (d.get("attachedOnUtc") or "") > (best.get("attachedOnUtc") or ""):
                best = d
    if best is None:
        return None, False
    return best, _iso_day(best.get("attachedOnUtc")) >= (since_iso or "")


def check_item(item, snapshot, since_iso):
    """Classify one carried item against the snapshot.

    Returns (verdict, evidence, owner):
      verdict in {"complete", "complete-old-evidence", "active", "unknown"}.
    """
    fam = family_of(item["name"])
    if fam is None:
        return "unknown", "no evidence rule for this item", None
    acts_seen = False
    if fam["done_activities"]:
        states = [activity_state(snapshot, p) for p in fam["done_activities"]]
        acts_seen = any(m for m, _, _ in states)
        if acts_seen and all(c for m, c, _ in states if m):
            done_dates = []
            for p in fam["done_activities"]:
                for a in snapshot.get("activities", []):
                    if re.search(p, a.get("description") or "", re.I) and a.get("completionDate"):
                        done_dates.append(_iso_day(a["completionDate"]))
            newest = max(done_dates) if done_dates else ""
            ev = f"all matching OSC activities complete (latest {newest})"
            return ("complete" if newest >= (since_iso or "") else "complete-old-evidence"), ev, None
    if fam["done_docs"]:
        doc, is_new = doc_evidence(snapshot, fam["done_docs"], since_iso)
        if doc:
            ev = (f"document \"{doc.get('description')}\" v{doc.get('version')} "
                  f"attached {_iso_day(doc.get('attachedOnUtc'))}")
            return ("complete" if is_new else "complete-old-evidence"), ev, None
    for p in fam.get("pending_activities", []):
        matched, _, first_pending = activity_state(snapshot, p)
        if matched and first_pending:
            owner = first_pending.get("user") or first_pending.get("serviceProvider")
            return "active", f"OSC activity \"{first_pending.get('description')}\" pending", owner
    if acts_seen:
        return "unknown", "activities matched but state unclear", None
    return "unknown", "no completion evidence found", None


def propose_new_items(snapshot, carried_family_keys):
    """Pending BA-relevant activities with no carried item -> proposals."""
    proposals = []
    for fam in FAMILIES:
        if fam["key"] not in PROPOSE_FROM_PENDING or fam["key"] in carried_family_keys:
            continue
        for p in fam.get("pending_activities", []):
            matched, _, first_pending = activity_state(snapshot, p)
            if matched and first_pending:
                owner = first_pending.get("user") or first_pending.get("serviceProvider")
                proposals.append({
                    "name": fam["key"],
                    "state": "PROPOSED",
                    "owner": owner,
                    "evidence": f"OSC activity \"{first_pending.get('description')}\" pending",
                })
                break
    return proposals


def iso_to_serial(iso):
    return (date.fromisoformat(iso) - EPOCH).days


def load_state(state_dir):
    p = Path(state_dir) / "ba-items-first-seen.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_state(state_dir, state):
    p = Path(state_dir) / "ba-items-first-seen.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def build_draft(prev_path, snapshot_dir, out_dir, asof=None, state_dir=None,
                amber_days=5, red_days=5):
    asof = asof or date.today().isoformat()
    prev = parse_report(prev_path)
    prev_date = None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", str(prev_path))
    if m:
        prev_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    since = prev_date or (date.fromisoformat(asof) - timedelta(days=7)).isoformat()

    state = load_state(state_dir) if state_dir else {}
    evidence = {"asof": asof, "prev_report": str(prev_path), "since": since,
                "jobs": [], "notes": []}
    header = ["Job No.", "Marketer", "Job Address", "Submit for BA",
              "Received RFI", "Received Covenant Approval", "Submit all RFI Items",
              "BA Received", "Deposit Paid", "Nominate Site Start",
              "Site Start (Physical)",
              "OUTSTANDING — WITH WHOM / DAYS (proposed, confirm template)"]
    out_rows = [[(h, xlsx_min.S_HEADER) for h in header]]

    for row in prev["rows"]:
        job_no = str(row["job_no"])
        snap_path = Path(snapshot_dir) / f"{job_no}.json"
        job_ev = {"job_no": job_no, "changes": [], "flags": []}
        snapshot = None
        if snap_path.exists():
            snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
        else:
            job_ev["flags"].append("no snapshot — row carried forward untouched")

        cells = [(job_no, xlsx_min.S_WRAP),
                 (row["marketer"], xlsx_min.S_WRAP),
                 (row["address"], xlsx_min.S_WRAP)]

        date_keys = ["submit_for_ba", "received_rfi", "received_covenant",
                     "submit_all_rfi_items", "ba_received", "deposit_paid",
                     "nominate_site_start", "site_start_physical"]
        values = {}
        for key in date_keys:
            cur = row[key]
            values[key] = cur["raw"]
            if snapshot and key in COLUMN_ACTIVITY:
                matched, complete, _ = activity_state(snapshot, COLUMN_ACTIVITY[key])
                if matched and complete:
                    comp_dates = [
                        _iso_day(a["completionDate"])
                        for a in snapshot["activities"]
                        if re.search(COLUMN_ACTIVITY[key], a.get("description") or "", re.I)
                        and a.get("completionDate")]
                    if comp_dates:
                        osc_date = max(comp_dates)
                        if cur["raw"] in (None, ""):
                            values[key] = iso_to_serial(osc_date)
                            job_ev["changes"].append(
                                {"column": key, "action": "filled",
                                 "value": osc_date,
                                 "evidence": f"OSC activity complete {osc_date}"})
                        elif cur["date"] and cur["date"] != osc_date:
                            job_ev["flags"].append(
                                f"{key}: report says {cur['date']}, OSC activity says {osc_date} — kept report value")

        g = row["submit_all_rfi_items"]
        items_out = []
        if g["pending"] and (values["submit_all_rfi_items"] in (None, "") or g["raw"]):
            filled_by_osc = values["submit_all_rfi_items"] not in (None, "") and \
                values["submit_all_rfi_items"] != g["raw"]
            if not filled_by_osc:
                carried_keys = set()
                for item in g["items"]:
                    fam = family_of(item["name"])
                    if fam:
                        carried_keys.add(fam["key"])
                    if snapshot:
                        verdict, ev, owner = check_item(item, snapshot, since)
                    else:
                        verdict, ev, owner = "unknown", "no snapshot", None
                    if verdict == "complete":
                        job_ev["changes"].append(
                            {"item": item["name"], "action": "dropped", "evidence": ev})
                        continue
                    flagged = verdict in ("unknown", "complete-old-evidence")
                    if verdict == "complete-old-evidence":
                        job_ev["flags"].append(
                            f"item \"{item['name']}\": completion evidence predates {since} ({ev}) — kept, verify")
                    items_out.append({"name": item["name"], "state": item["state"],
                                      "owner": owner, "flagged": flagged,
                                      "evidence": ev})
                if snapshot:
                    for prop in propose_new_items(snapshot, carried_keys):
                        items_out.append({**prop, "flagged": True})
                        job_ev["changes"].append(
                            {"item": prop["name"], "action": "proposed-add",
                             "evidence": prop["evidence"]})

        ageing_lines = []
        worst = ""
        jstate = state.setdefault(job_no, {})
        for item in items_out:
            key = item["name"].upper()
            first_seen = jstate.setdefault(key, since)
            days = (date.fromisoformat(asof) - date.fromisoformat(first_seen)).days
            flag = "RED" if days > red_days else ("AMBER" if days >= amber_days else "")
            if flag == "RED":
                worst = "RED"
            elif flag == "AMBER" and worst != "RED":
                worst = "AMBER"
            item["days"] = days
            item["flag"] = flag
            owner = item.get("owner") or (f"({item['state']})" if item.get("state") else "?")
            ageing_lines.append(f"{item['name']} — {owner} — {days}d{(' ' + flag) if flag else ''}")
        # completed jobs keep their history in state until the row drops off
        if not items_out and job_no in state and g["date"]:
            state.pop(job_no, None)

        for key in date_keys:
            val = values[key]
            if key == "submit_all_rfi_items" and items_out:
                text = "PENDING " + ", ".join(
                    i["name"] + (f" ({i['state']})" if i["state"] else "")
                    for i in items_out)
                cells.append((text, xlsx_min.S_RED))
            elif isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
                cells.append((float(val), xlsx_min.S_DATE))
            else:
                cells.append((val, xlsx_min.S_WRAP))
        age_style = {"RED": xlsx_min.S_REDFILL, "AMBER": xlsx_min.S_AMBER}.get(worst, xlsx_min.S_WRAP)
        if any(i.get("flagged") for i in items_out) and age_style == xlsx_min.S_WRAP:
            age_style = xlsx_min.S_FLAGGED
        cells.append(("\n".join(ageing_lines), age_style))

        out_rows.append(cells)
        job_ev["outstanding"] = items_out
        evidence["jobs"].append(job_ev)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.fromisoformat(asof).strftime("%d.%m.%Y")
    draft_path = out_dir / f"BA REPORT DRAFT - {stamp}.xlsx"
    widths = {"A": 9, "B": 16, "C": 34, "D": 11, "E": 11, "F": 12, "G": 44,
              "H": 11, "I": 11, "J": 11, "K": 11, "L": 46}
    xlsx_min.write_xlsx(draft_path, out_rows, sheet_name="Sheet 1", col_widths=widths)

    ev_json = out_dir / f"BA REPORT DRAFT - {stamp}-evidence.json"
    ev_json.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    ev_md = out_dir / f"BA REPORT DRAFT - {stamp}-evidence.md"
    lines = [f"# BA report draft evidence — {stamp}",
             "",
             f"Base: `{prev_path}` (changes evidenced since {since}). Draft only —",
             "the permit officer reviews, corrects and distributes. Flagged rows",
             "need human eyes; nothing flagged was changed automatically.", ""]
    for j in evidence["jobs"]:
        if not j["changes"] and not j["flags"] and not j["outstanding"]:
            continue
        lines.append(f"## Job {j['job_no']}")
        for c in j["changes"]:
            what = c.get("column") or c.get("item")
            lines.append(f"- **{c['action']}** {what} — {c['evidence']}")
        for f in j["flags"]:
            lines.append(f"- ⚠ {f}")
        for i in j["outstanding"]:
            owner = i.get("owner") or "?"
            age = f"{i.get('days', '?')}d" + (f" {i['flag']}" if i.get("flag") else "")
            mark = " ⚠" if i.get("flagged") else ""
            lines.append(f"- outstanding: {i['name']} — with {owner} — {age}{mark} ({i.get('evidence', '')})")
        lines.append("")
    ev_md.write_text("\n".join(lines), encoding="utf-8")

    if state_dir:
        save_state(state_dir, state)
    return draft_path, ev_md, evidence


def main(argv):
    args = {}
    it = iter(argv)
    for a in it:
        if a in ("-h", "--help"):
            print(__doc__)
            return 0
        if a.startswith("--"):
            args[a[2:]] = next(it, None)
    missing = [k for k in ("prev", "snapshots", "out") if k not in args]
    if missing:
        print(f"missing required args: {', '.join('--' + m for m in missing)}")
        return 2
    draft, ev_md, evidence = build_draft(
        args["prev"], args["snapshots"], args["out"],
        asof=args.get("asof"), state_dir=args.get("state"),
        amber_days=int(args.get("amber-days", 5)),
        red_days=int(args.get("red-days", 5)))
    n_changes = sum(len(j["changes"]) for j in evidence["jobs"])
    n_flags = sum(len(j["flags"]) for j in evidence["jobs"])
    print(f"draft: {draft}")
    print(f"evidence: {ev_md}")
    print(f"{len(evidence['jobs'])} jobs, {n_changes} evidenced changes, {n_flags} flags")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
