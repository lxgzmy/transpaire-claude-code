#!/usr/bin/env python3
"""Draft the Monday BA report from last week's report + OSC snapshots (v0.2).

Deterministic merge (no network): reads last week's report (carry-forward
base, PO-10), per-job OSC snapshot JSONs saved by the MCP read step, and a
per-item state file for ageing; writes a draft .xlsx plus an evidence bundle
to the output folder. Every change carries its evidence; anything
low-confidence is kept and flagged, never silently applied (org HITL rule).

Ageing model (PO-11, confirmed on issue #29, 10 Sep 2026): per outstanding
item, ASSIGNED TO, DATE SUBMITTED, DATE RESOLVED and DAYS OUTSTANDING in
NSW business days; the flag is YELLOW at or under the tier threshold and RED
over it, where the tier follows who the item is with (TIERS below). A
resolved item is shown once (the Monday after it resolves) with its date and
frozen count, then drops. Six defaults are assumed until the owner confirms
them on #29 — see ASSIGNEE_TIER and rules/approval-workflow.md.

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
                            [--jobs 26029,26052,26001]

--jobs restricts ageing, snapshot expectations and evidence detail to the
pilot rows; every other row is carried forward verbatim with L-O blank.
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min
from ba_report_parse import EPOCH, ITEM_HEADERS, parse_report, serial_to_iso, text_to_iso
from nsw_holidays import business_days

# ------------------------------------------------------------------ ageing config
# Business-day thresholds per tier: YELLOW while days <= threshold, RED after.
TIERS = {"INTERNAL": 10, "ENERGY": 10, "EXTERNAL": 20, "COUNCIL": 30}

# Who an item is with -> tier. Matched case-insensitively against the
# Assigned-to text (officer-typed, "(W/O X)" hint, or the OSC owner name).
# Lines marked ASSUMED are the #29 clarifications, defaults until confirmed.
ASSIGNEE_TIER = [
    (r"\b(DRAFT\w*|GM|GENERAL MANAGER|CONTRACTS?|ADMIN\w*|ESTIMAT\w*|SALES|TRANSPIRE|INTERNAL)\b", "INTERNAL"),
    (r"\b(CLIENT|OWNERS?|CUSTOMER)\b", "INTERNAL"),                       # ASSUMED (#29 q1)
    (r"\b(ENERGY|BASIX|NATHERS|ASSESSOR)\b", "ENERGY"),
    (r"\b(CERTIFIER|PCA|PRIVATE CERT\w*)\b", "EXTERNAL"),                 # ASSUMED (#29 q1)
    (r"\b(ENGINEER\w*|SURVEY\w*|CONSULT\w*|HYDRAULIC|STRUCTURAL|GEOTECH\w*)\b", "EXTERNAL"),
    (r"\b(COUNCIL|SHIRE|CITY OF)\b", "COUNCIL"),
    (r"\b(SYDNEY WATER|ALTOGETHER|HUNTER WATER|WATER AUTHORITY|TAP.?IN)\b", "COUNCIL"),  # ASSUMED (#29 q2)
]

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
# pending one's assigned user / service provider is "who it is with".
# submitted_docs: order/application/receipt documents whose OLDEST attach
# date evidences DATE SUBMITTED (verify grade — .msg files are dragged into
# OSC after the send, PO-9).
# tier: default tier when nothing better says who the item is with.
FAMILIES = [
    {"key": "ENGINEERING", "tier": "EXTERNAL",
     "match": r"\bENG(INEERING)?\b",
     "done_activities": [r"Receive Engineering", r"Review Engineering", r"Forward Engineers"],
     "pending_activities": [r"Receive Engineering", r"Review Engineering",
                            r"Amend Working Drawings to Suit", r"Forward Engineers"],
     "done_docs": [], "submitted_docs": []},
    {"key": "COVENANT", "tier": "EXTERNAL",
     "match": r"\bCOV(ENANT)?\b",
     "done_activities": [r"Receive Covenant Approval"],
     "pending_activities": [r"Submit Covenant Application", r"Receive Covenant Approval",
                            r"Forward Covenant Application Approval"],
     "done_docs": [r"COVENANT.*APPROV"],
     "submitted_docs": [r"COVENANT.*(APPLICATION|SUBMI)"]},
    {"key": "INSURANCES", "tier": "INTERNAL",
     "match": r"\bINSURANCE(S)?\b",
     "done_activities": [r"Pay Q Leave", r"Pay QBCC", r"Pay Construction Works Insurance",
                         r"Email Copy of Relevant Insurances"],
     "pending_activities": [r"Pay Q Leave", r"Pay QBCC", r"Pay Construction Works Insurance",
                            r"Email Copy of Relevant Insurances"],
     "done_docs": [], "submitted_docs": []},
    {"key": "ENERGY", "tier": "ENERGY",
     "match": r"\b(ENERGY|NATHERS)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"ENERGY REPORT", r"NATHERS (REPORT|CERT)"],
     "submitted_docs": [r"ENERGY.*(APPLICATION|REQUEST|ORDER)", r"NATHERS.*(APPLICATION|REQUEST|ORDER)"]},
    {"key": "BASIX", "tier": "ENERGY",
     "match": r"\bBASIX\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"BASIX (REPORT|CERT)"],
     "submitted_docs": [r"BASIX.*(APPLICATION|REQUEST|ORDER)"]},
    {"key": "S10.7", "tier": "COUNCIL",
     "match": r"10\.7",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"10\.7(?!.*(APPLICATION|REQUEST|RECEIPT))"],
     "submitted_docs": [r"10\.7.*(APPLICATION|REQUEST|RECEIPT)"]},
    {"key": "SYDNEY WATER", "tier": "COUNCIL",
     "match": r"\b(SYDNEY WATER|TAP.?IN)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"SYDNEY WATER.*APPROV", r"TAP.?IN.*APPROV"],
     "submitted_docs": [r"(SYDNEY WATER|TAP.?IN).*(APPLICATION|RECEIPT)"]},
    {"key": "ALTOGETHER", "tier": "COUNCIL",
     "match": r"\bALTOGETHER\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"ALTOGETHER.*APPROV"],
     "submitted_docs": [r"ALTOGETHER.*(APPLICATION|RECEIPT)"]},
    {"key": "WATER METER", "tier": "COUNCIL",
     "match": r"\bWATER METER\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"WATER METER.*APPROV"],
     "submitted_docs": [r"WATER METER.*(APPLICATION|RECEIPT)"]},
    {"key": "PLUMBING", "tier": "COUNCIL",
     "match": r"\bPLUMBING\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"PLUMBING.*APPROV", r"APPROVAL - PLUMBING"],
     "submitted_docs": [r"PLUMBING.*(APPLICATION|RECEIPT)"]},
    {"key": "DRIVEWAY", "tier": "COUNCIL",
     "match": r"\b(DRIVEWAY|DWY)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"DRIVEWAY.*APPROV", r"APPROVAL - DRIVEWAY"],
     "submitted_docs": [r"DRIVEWAY.*(APPLICATION|RECEIPT)"]},
    {"key": "S68", "tier": "COUNCIL",
     "match": r"\bS(ECTION )?68\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"(APPROVAL - S(ECTION )?68|S(ECTION )?68.*APPROV)"],
     "submitted_docs": [r"S(ECTION )?68.*(APPLICATION|RECEIPT)"]},
    {"key": "S307", "tier": "COUNCIL",
     "match": r"\bS(ECTION )?307\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"S(ECTION )?307.*(APPROV|CERT)"],
     "submitted_docs": [r"S(ECTION )?307.*(APPLICATION|RECEIPT)"]},
    {"key": "CONTRIBUTIONS", "tier": "COUNCIL",
     "match": r"\b(CONTRIBUTIONS?|S64|S7\.1[12]|HPC)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"(CONTRIBUTION.*(RECEIPT|PAID)|HPC.*RECEIPT|7\.1[12].*RECEIPT|S64.*(RECEIPT|PAID))"],
     "submitted_docs": []},
    # Families first seen on the pilot jobs (issue #29 run, 11 Sep 2026)
    {"key": "LANDSCAPE", "tier": "COUNCIL",
     "match": r"\bLANDSCAPE\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"LANDSCAPE.*APPROV"],
     "submitted_docs": [r"LANDSCAPE.*APPLICATION"]},
    {"key": "SEWER PUMP", "tier": "COUNCIL",
     "match": r"\b(SEW(AGE|ER)?\s*EJECT\w*|PUMP\s*STATION)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"(SEWAGE|SEWER|PUMP).*APPROV"],
     "submitted_docs": [r"(SEWAGE|SEWER|PUMP).*APPLICATION"]},
    {"key": "WASTE MANAGEMENT", "tier": "INTERNAL",
     "match": r"\bWASTE\s*MAN\w*\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"WASTE\s*MANAGEMENT\s*PLAN(?!.*(APPLICATION|REQUEST))"],
     "submitted_docs": []},
    {"key": "LODGEMENT", "tier": "INTERNAL",
     "match": r"\b(LODGEMENT|LODGE)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [], "submitted_docs": []},
]

# Pending activities that justify PROPOSING a new outstanding item when no
# carried item already covers the family.
PROPOSE_FROM_PENDING = {"ENGINEERING", "COVENANT", "INSURANCES"}

ITEM_COLUMN_LETTERS = ["L", "M", "N", "O"]


def _iso_day(s):
    return (s or "")[:10]


def _ddmmyyyy(iso):
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return d.strftime("%d/%m/%Y")


def family_of(item_name):
    for fam in FAMILIES:
        if re.search(fam["match"], item_name.upper()):
            return fam
    return None


def item_key(item_name):
    fam = family_of(item_name)
    return fam["key"] if fam else item_name.upper()


def tier_for(text):
    """Tier from Assigned-to text via ASSIGNEE_TIER, or None."""
    if not text:
        return None
    up = text.upper()
    for pattern, tier in ASSIGNEE_TIER:
        if re.search(pattern, up):
            return tier
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


def doc_evidence(snapshot, patterns, since_iso, oldest=False):
    """Newest (or oldest) document matching any pattern; (doc, is_new_since)."""
    best = None
    for d in snapshot.get("documents", []):
        desc = (d.get("description") or "").upper()
        if any(re.search(p, desc) for p in patterns):
            when = d.get("attachedOnUtc") or ""
            if best is None:
                best = d
            elif oldest and when < (best.get("attachedOnUtc") or ""):
                best = d
            elif not oldest and when > (best.get("attachedOnUtc") or ""):
                best = d
    if best is None:
        return None, False
    return best, _iso_day(best.get("attachedOnUtc")) >= (since_iso or "")


def _owner_of(activity):
    """(owner_name, field) from a pending activity — field says which."""
    if activity.get("user"):
        return activity["user"], "user"
    if activity.get("serviceProvider"):
        return activity["serviceProvider"], "serviceProvider"
    return None, None


def check_item(item, snapshot, since_iso):
    """Classify one carried item against the snapshot.

    Returns (verdict, evidence, owner, owner_field, evidence_date):
      verdict in {"complete", "complete-old-evidence", "active", "unknown"}.
    """
    fam = family_of(item["name"])
    if fam is None:
        return "unknown", "no evidence rule for this item", None, None, None
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
            verdict = "complete" if newest >= (since_iso or "") else "complete-old-evidence"
            return verdict, ev, None, None, newest or None
    if fam["done_docs"]:
        doc, is_new = doc_evidence(snapshot, fam["done_docs"], since_iso)
        if doc:
            ev = (f"document \"{doc.get('description')}\" v{doc.get('version')} "
                  f"attached {_iso_day(doc.get('attachedOnUtc'))}")
            return ("complete" if is_new else "complete-old-evidence"), ev, None, None, _iso_day(doc.get("attachedOnUtc"))
    for p in fam.get("pending_activities", []):
        matched, _, first_pending = activity_state(snapshot, p)
        if matched and first_pending:
            owner, field = _owner_of(first_pending)
            return "active", f"OSC activity \"{first_pending.get('description')}\" pending", owner, field, None
    if acts_seen:
        return "unknown", "activities matched but state unclear", None, None, None
    return "unknown", "no completion evidence found", None, None, None


def propose_new_items(snapshot, carried_family_keys):
    """Pending BA-relevant activities with no carried item -> proposals."""
    proposals = []
    for fam in FAMILIES:
        if fam["key"] not in PROPOSE_FROM_PENDING or fam["key"] in carried_family_keys:
            continue
        for p in fam.get("pending_activities", []):
            matched, _, first_pending = activity_state(snapshot, p)
            if matched and first_pending:
                owner, field = _owner_of(first_pending)
                proposals.append({
                    "name": fam["key"],
                    "state": "PROPOSED",
                    "owner": owner,
                    "owner_field": field,
                    "evidence": f"OSC activity \"{first_pending.get('description')}\" pending",
                })
                break
    return proposals


def submitted_evidence(item, snapshot, lodged_iso=None):
    """Best OSC evidence for DATE SUBMITTED: (iso_date, description) or (None, None).

    Order: oldest order/application/receipt document for the family; for
    activity-backed families the matching Order/Request step or the
    same-chain predecessor of the first pending activity; an alert whose
    subject matches the family — alerts only count from lodgement
    (``lodged_iso``, column D) onwards, because pre-lodgement alerts such
    as "LODGE FOR CC" are instructions, not RFI-item handovers. Documents
    and activities may legitimately predate lodgement (items ordered early,
    PO-5) and are not floored.
    """
    fam = family_of(item["name"])
    if fam is None:
        return None, None
    if fam.get("submitted_docs"):
        doc, _ = doc_evidence(snapshot, fam["submitted_docs"], None, oldest=True)
        if doc:
            return _iso_day(doc.get("attachedOnUtc")), f"document \"{doc.get('description')}\" attached"
    for p in fam.get("pending_activities", []):
        matched, _, first_pending = activity_state(snapshot, p)
        if matched and first_pending:
            desc = first_pending.get("description") or ""
            seq = first_pending.get("sequence") or 0
            acts = snapshot.get("activities", [])
            # (a) the matching Order/Request/Submit step for the same item
            #     ("Receive Engineering - X" <- "Order Engineering - X")
            if " - " in desc:
                suffix = desc.split(" - ", 1)[1].strip().upper()
                for a in acts:
                    d = (a.get("description") or "")
                    if a.get("completionDate") and " - " in d and \
                            d.split(" - ", 1)[1].strip().upper() == suffix and \
                            re.match(r"^(Order|Request|Submit|Send)\b", d, re.I):
                        return _iso_day(a["completionDate"]), f"\"{d}\" completed"
            # (b) the immediately preceding step, only if it belongs to the
            #     same item chain (any family activity pattern)
            chain = fam.get("pending_activities", []) + fam.get("done_activities", [])
            for a in acts:
                if (a.get("sequence") or 0) == seq - 1 and a.get("completionDate") and \
                        any(re.search(q, a.get("description") or "", re.I) for q in chain):
                    return _iso_day(a["completionDate"]), f"preceding step \"{a.get('description')}\" completed"
            break
    hits = [a for a in snapshot.get("alerts", [])
            if re.search(fam["match"], (a.get("subject") or "").upper())
            and (not lodged_iso or _iso_day(a.get("createdOnUtc")) >= lodged_iso)]
    if hits:
        oldest = min(hits, key=lambda a: a.get("createdOnUtc") or "")
        return _iso_day(oldest.get("createdOnUtc")), f"alert \"{oldest.get('subject')}\" raised"
    return None, None


def iso_to_serial(iso):
    return (date.fromisoformat(iso) - EPOCH).days


# ------------------------------------------------------------------ state
def _normalise_entry(v):
    """v0.1 stored an ISO string (first seen); v0.2 stores a dict."""
    if isinstance(v, str):
        return {"first_seen": v}
    return dict(v or {})


def load_state(state_dir):
    p = Path(state_dir) / "ba-items-first-seen.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {job: {k: _normalise_entry(v) for k, v in (items or {}).items()}
            for job, items in raw.items()}


def save_state(state_dir, state):
    p = Path(state_dir) / "ba-items-first-seen.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _resolve_sticky(report_value, entry, ai_key, val_key, src_key):
    """Officer-override detection for one per-item field.

    Returns (value, source) where source is "officer" when the officer typed
    it (report value differs from what the AI wrote last time, or the state
    already marks it officer-set) or None when derivation should proceed.
    """
    ai_prev = entry.get(ai_key)
    if report_value:
        if ai_prev is None or report_value != ai_prev:
            entry[val_key] = report_value
            entry[src_key] = "officer"
            return report_value, "officer"
        if entry.get(src_key) == "officer":
            return entry.get(val_key) or report_value, "officer"
        return report_value, None  # AI-written value echoed back; may re-derive
    if entry.get(src_key) == "officer" and entry.get(val_key):
        return entry[val_key], "officer"
    return None, None


# ------------------------------------------------------------------ ageing
def age_item(item, entry, snapshot, asof, since, submit_for_ba_iso):
    """Fill assigned_to / tier / date_submitted / days / flag on one item.

    ``entry`` is the state dict for the item (mutated). ``item`` carries any
    officer values read back from last week's L-O columns.
    """
    fam = family_of(item["name"])
    flags = []

    # ---- assigned to
    assigned, src = _resolve_sticky(item.get("assigned_to"), entry,
                                    "ai_assigned_to", "assigned_to", "assigned_source")
    fallback_echo = assigned if (assigned and src is None) else None
    if src != "officer":
        assigned, src = None, None
        wo = re.match(r"^W/?O\s+(.+)$", (item.get("state") or "").strip(), re.I)
        if wo:
            assigned, src = wo.group(1).strip(), "report (W/O)"
        elif item.get("owner"):
            assigned, src = item["owner"], f"osc {item.get('owner_field') or 'activity'}"
        elif fallback_echo:
            assigned, src = fallback_echo, "carried"
    tier = None
    if src == "officer" or src == "report (W/O)" or src == "carried":
        tier = tier_for(assigned)
    elif src and src.startswith("osc"):
        tier = "INTERNAL" if item.get("owner_field") == "user" else (fam["tier"] if fam else None)
        tier = tier or tier_for(assigned)
    if tier is None:
        if fam:
            tier = fam["tier"]
            if assigned:
                flags.append(f"assignee \"{assigned}\" not recognised — tier from item type ({tier})")
        else:
            tier = "INTERNAL"
            flags.append("no assignee and no item rule — tier INTERNAL (strictest)")
    if not assigned:
        flags.append("assigned-to unknown")

    # ---- date submitted
    submitted, dsrc = _resolve_sticky(item.get("date_submitted"), entry,
                                      "ai_date_submitted", "date_submitted", "date_source")
    echo = submitted if (submitted and dsrc is None) else None
    if dsrc != "officer":
        submitted, dsrc = None, None
        if snapshot:
            ev_date, ev_desc = submitted_evidence(item, snapshot, submit_for_ba_iso)
            if ev_date:
                submitted, dsrc = ev_date, f"osc: {ev_desc}"
        if not submitted and echo:
            submitted, dsrc = echo, "carried"
        if not submitted:
            first_seen = entry.setdefault("first_seen", since)
            submitted, dsrc = first_seen, "assumed (first seen in report)"
            flags.append("date submitted assumed from first report sighting — officer to correct")
    entry.setdefault("first_seen", since)

    # ---- days + flag
    end = item.get("date_resolved") if item.get("resolved") else asof
    days = business_days(submitted, end) if end else 0
    if item.get("resolved"):
        flag = ""
    else:
        flag = "YELLOW" if days <= TIERS[tier] else "RED"

    item.update({"assigned_to": assigned, "assigned_source": src, "tier": tier,
                 "threshold": TIERS[tier], "date_submitted": submitted,
                 "date_source": dsrc, "days": days, "flag": flag,
                 "assumed": dsrc.startswith("assumed") if dsrc else False})
    item["age_flags"] = flags
    if flags:
        item["flagged"] = True

    # remember what the AI wrote so next week's echo is recognisable
    entry["ai_assigned_to"] = assigned
    entry["ai_date_submitted"] = submitted
    if src != "officer":
        entry["assigned_to"] = assigned
        entry["assigned_source"] = src
    if dsrc != "officer":
        entry["date_submitted"] = submitted
        entry["date_source"] = dsrc
    return item


# ------------------------------------------------------------------ draft
def build_draft(prev_path, snapshot_dir, out_dir, asof=None, state_dir=None, jobs=None):
    asof = asof or date.today().isoformat()
    prev = parse_report(prev_path)
    prev_date = None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", str(prev_path))
    if m:
        prev_date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    since = prev_date or (date.fromisoformat(asof) - timedelta(days=7)).isoformat()
    pilot = set(str(j).strip() for j in jobs) if jobs else None

    state = load_state(state_dir) if state_dir else {}
    evidence = {"asof": asof, "prev_report": str(prev_path), "since": since,
                "pilot_jobs": sorted(pilot) if pilot else None,
                "jobs": [], "notes": list(prev.get("header_warnings", []))}
    header = ["Job No.", "Marketer", "Job Address", "Submit for BA",
              "Received RFI", "Received Covenant Approval", "Submit all RFI Items",
              "BA Received", "Deposit Paid", "Nominate Site Start",
              "Site Start (Physical)"] + ITEM_HEADERS
    out_rows = [[(h, xlsx_min.S_HEADER) for h in header]]
    seen_jobs = set()

    for row in prev["rows"]:
        job_no = str(row["job_no"])
        seen_jobs.add(job_no)
        in_scope = pilot is None or job_no in pilot
        job_ev = {"job_no": job_no, "pilot": in_scope, "changes": [], "flags": []}
        snap_path = Path(snapshot_dir) / f"{job_no}.json"
        snapshot = None
        if in_scope:
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
        items_out = []      # open items, in G order
        resolved_out = []   # items resolved this cycle (shown once)
        had_items = False
        if in_scope and g["pending"] and (values["submit_all_rfi_items"] in (None, "") or g["raw"]):
            filled_by_osc = values["submit_all_rfi_items"] not in (None, "") and \
                values["submit_all_rfi_items"] != g["raw"]
            if not filled_by_osc:
                had_items = bool(g["items"])
                if g.get("item_cols_misaligned"):
                    job_ev["flags"].append("L-O lines do not line up with the G item list — officer values ignored")
                    for it in g["items"]:
                        for k in ("assigned_to", "date_submitted", "date_resolved", "days_outstanding"):
                            it.pop(k, None)
                if g.get("resolved"):
                    job_ev["changes"].append(
                        {"item": ", ".join(i["name"] for i in g["resolved"]),
                         "action": "resolved-line-dropped",
                         "evidence": "shown last cycle as RESOLVED; not carried"})
                carried_keys = set()
                for item in g["items"]:
                    fam = family_of(item["name"])
                    if fam:
                        carried_keys.add(fam["key"])
                    if snapshot:
                        verdict, ev, owner, owner_field, ev_date = check_item(item, snapshot, since)
                    else:
                        verdict, ev, owner, owner_field, ev_date = "unknown", "no snapshot", None, None, None
                    entry = {"name": item["name"], "state": item["state"],
                             "owner": owner, "owner_field": owner_field,
                             "assigned_to": item.get("assigned_to"),
                             "date_submitted": item.get("date_submitted"),
                             "evidence": ev, "flagged": False, "resolved": False}
                    if verdict == "complete":
                        entry.update({"resolved": True, "date_resolved": ev_date or asof})
                        job_ev["changes"].append(
                            {"item": item["name"], "action": "resolved", "evidence": ev})
                        resolved_out.append(entry)
                        continue
                    entry["flagged"] = verdict in ("unknown", "complete-old-evidence")
                    if verdict == "complete-old-evidence":
                        job_ev["flags"].append(
                            f"item \"{item['name']}\": completion evidence predates {since} ({ev}) — kept, verify")
                    items_out.append(entry)
                if snapshot:
                    for prop in propose_new_items(snapshot, carried_keys):
                        items_out.append({**prop, "flagged": True, "resolved": False})
                        job_ev["changes"].append(
                            {"item": prop["name"], "action": "proposed-add",
                             "evidence": prop["evidence"]})

        # ---- ageing (pilot rows only)
        jstate = state.setdefault(job_no, {}) if in_scope else {}
        submit_iso = row["submit_for_ba"]["date"]
        for item in items_out + resolved_out:
            entry = jstate.setdefault(item_key(item["name"]), {})
            age_item(item, entry, snapshot, asof, since, submit_iso)
            for f in item.get("age_flags", []):
                job_ev["flags"].append(f"item \"{item['name']}\": {f}")
        for item in resolved_out:
            jstate.pop(item_key(item["name"]), None)
        if in_scope and not items_out and not resolved_out and job_no in state and g["date"]:
            state.pop(job_no, None)

        # ---- G text
        all_resolved_now = had_items and not items_out and resolved_out
        for key in date_keys:
            val = values[key]
            if key == "submit_all_rfi_items" and items_out:
                text = "PENDING " + ", ".join(
                    i["name"] + (f" ({i['state']})" if i["state"] else "")
                    for i in items_out)
                if resolved_out:
                    text += "\nRESOLVED " + ", ".join(
                        f"{i['name']} ({_ddmmyyyy(i['date_resolved'])})" for i in resolved_out)
                cells.append((text, xlsx_min.S_RED))
            elif key == "submit_all_rfi_items" and all_resolved_now:
                matched, complete, _ = activity_state(snapshot or {}, COLUMN_ACTIVITY[key])
                comp = [_iso_day(a["completionDate"]) for a in (snapshot or {}).get("activities", [])
                        if re.search(COLUMN_ACTIVITY[key], a.get("description") or "", re.I)
                        and a.get("completionDate")]
                if matched and complete and comp:
                    cells.append((float(iso_to_serial(max(comp))), xlsx_min.S_DATE))
                    job_ev["changes"].append({"column": key, "action": "filled", "value": max(comp),
                                              "evidence": "all items resolved; OSC Return RFI activity complete"})
                else:
                    cells.append(("", xlsx_min.S_FLAGGED))
                    job_ev["flags"].append("all items resolved but OSC has no Return RFI completion — G left blank")
            elif isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
                cells.append((float(val), xlsx_min.S_DATE))
            else:
                cells.append((val, xlsx_min.S_WRAP))

        # ---- L-O per-item columns
        ordered = items_out + resolved_out
        if ordered:
            worst = ""
            for i in items_out:
                if i["flag"] == "RED":
                    worst = "RED"
                elif i["flag"] == "YELLOW" and worst != "RED":
                    worst = "YELLOW"
            fill = {"RED": xlsx_min.S_REDFILL, "YELLOW": xlsx_min.S_YELLOW}.get(worst, xlsx_min.S_WRAP)
            if fill == xlsx_min.S_WRAP and any(i.get("flagged") for i in ordered):
                fill = xlsx_min.S_FLAGGED
            col_l = "\n".join(("⚠ " if i.get("flagged") else "") + (i.get("assigned_to") or "?") for i in ordered)
            col_m = "\n".join(_ddmmyyyy(i.get("date_submitted")) for i in ordered)
            col_n = "\n".join(_ddmmyyyy(i.get("date_resolved")) if i.get("resolved") else "" for i in ordered)
            col_o = "\n".join(
                f"{i['days']} RESOLVED" if i.get("resolved")
                else f"{i['days']} {i['flag']}" + (" (assumed)" if i.get("assumed") else "")
                for i in ordered)
            cells += [(col_l, fill), (col_m, fill), (col_n, fill), (col_o, fill)]
        else:
            cells += [("", xlsx_min.S_WRAP)] * 4

        out_rows.append(cells)
        job_ev["outstanding"] = items_out
        job_ev["resolved"] = resolved_out
        evidence["jobs"].append(job_ev)

    if pilot:
        for j in sorted(pilot - seen_jobs):
            evidence["notes"].append(
                f"pilot job {j} is not a row in the base report (not yet lodged / not in the "
                "BA-lodged export) — no row fabricated; it joins once the export lists it")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.fromisoformat(asof).strftime("%d.%m.%Y")
    draft_path = out_dir / f"BA REPORT DRAFT - {stamp}.xlsx"
    widths = {"A": 9, "B": 16, "C": 34, "D": 11, "E": 11, "F": 12, "G": 44,
              "H": 11, "I": 11, "J": 11, "K": 11,
              "L": 22, "M": 13, "N": 13, "O": 18}
    xlsx_min.write_xlsx(draft_path, out_rows, sheet_name="Sheet 1", col_widths=widths)

    ev_json = out_dir / f"BA REPORT DRAFT - {stamp}-evidence.json"
    ev_json.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    ev_md = out_dir / f"BA REPORT DRAFT - {stamp}-evidence.md"
    lines = [f"# BA report draft evidence — {stamp}",
             "",
             f"Base: `{prev_path}` (changes evidenced since {since}). Draft only —",
             "the permit officer reviews, corrects and distributes. Flagged rows",
             "need human eyes; nothing flagged was changed automatically.",
             "",
             "Ageing: NSW business days from DATE SUBMITTED; YELLOW at or under the",
             "tier threshold, RED over it — " +
             ", ".join(f"{k} {v}" for k, v in TIERS.items()) + ".",
             ""]
    if pilot:
        lines += [f"Pilot rows: {', '.join(sorted(pilot))} — other rows carried forward verbatim.", ""]
    for n in evidence["notes"]:
        lines.append(f"- ℹ {n}")
    if evidence["notes"]:
        lines.append("")
    for j in evidence["jobs"]:
        if not j["changes"] and not j["flags"] and not j["outstanding"] and not j["resolved"]:
            continue
        lines.append(f"## Job {j['job_no']}")
        for c in j["changes"]:
            what = c.get("column") or c.get("item")
            lines.append(f"- **{c['action']}** {what} — {c['evidence']}")
        for f in j["flags"]:
            lines.append(f"- ⚠ {f}")
        for i in j["outstanding"]:
            mark = " ⚠" if i.get("flagged") else ""
            lines.append(
                f"- outstanding: {i['name']} — with {i.get('assigned_to') or '?'} "
                f"[{i.get('tier')} ≤{i.get('threshold')}] — submitted {i.get('date_submitted')} "
                f"({i.get('date_source')}) — {i.get('days')} business days {i.get('flag')}{mark} "
                f"({i.get('evidence', '')})")
        for i in j["resolved"]:
            lines.append(
                f"- resolved: {i['name']} — with {i.get('assigned_to') or '?'} — submitted "
                f"{i.get('date_submitted')} — resolved {i.get('date_resolved')} after {i.get('days')} "
                f"business days ({i.get('evidence', '')})")
        lines.append("")
    ev_md.write_text("\n".join(lines), encoding="utf-8")

    if state_dir:
        save_state(state_dir, state)
    return draft_path, ev_md, evidence


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prev", required=True, help="last week's report .xlsx (BA REPORT - dd.mm.yyyy.xlsx)")
    ap.add_argument("--snapshots", required=True, help="folder of <jobno>.json OSC snapshots")
    ap.add_argument("--out", required=True, help="output folder (runtime only)")
    ap.add_argument("--asof", help="draft date YYYY-MM-DD (default today)")
    ap.add_argument("--state", help="state folder for per-item ageing")
    ap.add_argument("--jobs", help="comma-separated pilot job numbers; other rows carry forward verbatim")
    args = ap.parse_args(argv)
    jobs = [j for j in (args.jobs or "").split(",") if j.strip()] or None
    draft, ev_md, evidence = build_draft(
        args.prev, args.snapshots, args.out,
        asof=args.asof, state_dir=args.state, jobs=jobs)
    n_changes = sum(len(j["changes"]) for j in evidence["jobs"])
    n_flags = sum(len(j["flags"]) for j in evidence["jobs"])
    print(f"draft: {draft}")
    print(f"evidence: {ev_md}")
    print(f"{len(evidence['jobs'])} jobs, {n_changes} evidenced changes, {n_flags} flags")
    for n in evidence["notes"]:
        print(f"note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
