#!/usr/bin/env python3
"""Draft the Monday BA report from last week's report + OSC snapshots (v0.4).

Deterministic merge (no network): reads last week's report (carry-forward
base, PO-10), per-job OSC snapshot JSONs saved by the snapshot step, and a
per-item state file for ageing; writes a draft .xlsx plus an evidence bundle
to the output folder. Every change carries its evidence; anything
low-confidence is kept and flagged, never silently applied (org HITL rule).

Workbook shape (v0.3): the main sheet reproduces the base export column for
column (columns located by header text, so the 28 Sep 2026 template with
its engineering and covenant columns carries through verbatim); the Job No.
cell takes the row's worst-item colour. Per-item values go on a second
sheet, **Items** (one row per item: Job No., Item, Assigned to, Date
submitted, Date resolved, Days outstanding, Flag, Notes, Draft notes), which
is also where the officer types corrections. Her base is a plain export, so
v0.4 reads them from last week's draft as she left it (``--edited``) and
keeps them; Notes is her own column. Engineering and covenant are also
tracked from their export columns (PO-11b), engineering in two stages: design
with the engineer, then Transpire's internal review (PO-11c). The v0.2 L-O
columns are no longer written.

Ageing model (PO-11, confirmed on issue #29, 10 Sep 2026): per outstanding
item, ASSIGNED TO, DATE SUBMITTED, DATE RESOLVED and DAYS OUTSTANDING in
NSW business days; the flag is YELLOW at or under the tier threshold and RED
over it, where the tier follows who the item is with (TIERS below). A
resolved item is shown once (the Monday after it resolves) with its date and
frozen count, then drops. The six defaults asked on #29 were confirmed by the
officer on 17 Sep 2026 — see ASSIGNEE_TIER and rules/approval-workflow.md.

Snapshot JSON shape (one file per job, ``<jobno>.json``, written by
``osc_snapshot.py`` — see workflows/ba-weekly-report.md):

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
pilot rows; every other row is carried forward verbatim with no Items rows.
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xlsx_min
from ba_report_parse import EPOCH, ITEMS_SHEET, ITEMS_SHEET_HEADERS, norm_item, officer_edits, parse_report
from nsw_holidays import LAST_YEAR, business_days, covers, sydney_date

# ------------------------------------------------------------------ ageing config
# Business-day thresholds per tier: YELLOW while days <= threshold, RED after.
TIERS = {"INTERNAL": 10, "ENERGY": 10, "EXTERNAL": 20, "COUNCIL": 30}

# Who an item is with -> tier. Matched case-insensitively against the
# Assigned-to text (officer-typed, "(W/O X)" hint, or the OSC owner name).
# Lines marked #29 were defaults the officer confirmed on 17 Sep 2026.
ASSIGNEE_TIER = [
    (r"\b(DRAFT\w*|GM|GENERAL MANAGER|CONTRACTS?|ADMIN\w*|ESTIMAT\w*|SALES|TRANSPIRE|INTERNAL)\b", "INTERNAL"),
    (r"\b(CLIENT|OWNERS?|CUSTOMER)\b", "INTERNAL"),                       # #29 q1
    (r"\b(ENERGY|BASIX|NATHERS|ASSESSOR)\b", "ENERGY"),
    (r"\b(CERTIFIER|PCA|PRIVATE CERT\w*)\b", "EXTERNAL"),                 # #29 q1
    (r"\b(ENGINEER\w*|SURVEY\w*|CONSULT\w*|HYDRAULIC|STRUCTURAL|GEOTECH\w*)\b", "EXTERNAL"),
    # The officer's own label, e.g. "Water Services Coordinator (External)" (22.10 Items sheet)
    (r"\b(EXTERNAL|WATER SERVICES? CO-?ORDINATOR)\b", "EXTERNAL"),
    (r"\b(COUNCIL|SHIRE|CITY OF)\b", "COUNCIL"),
    (r"\b(SYDNEY WATER|ALTOGETHER|HUNTER WATER|WATER AUTHORITY|TAP.?IN)\b", "COUNCIL"),  # #29 q2
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

# Wording that marks an order, application or receipt rather than the outcome.
# A document described this way never counts as completion ("COVENANT
# APPLICATION FOR APPROVAL", "ENERGY REPORT REQUEST") unless it is filed as an
# approval ("APPROVAL - S68 APPLICATION"). Families whose outcome IS a receipt
# (contributions paid) set done_exclude to None.
NOT_AN_OUTCOME = r"\b(APPLICATION|APPLN|REQUEST|ORDER(ED)?|RECEIPT|SUBMI\w*)\b"

# Engineering in two stages (the officer, correcting her 27 Oct 2026 answer): the
# engineer, an external consultant, takes about 15 business days to design it;
# Transpire's internal review, from receiving the design until it goes to the
# certifier, about 10. A stage is told by who she says has the item, else by the
# item's columns (COLUMN_CYCLES "stage"), else by the OSC slab chain the columns
# follow ("osc": the step that starts the stage is done, the one that ends it is
# not), else it is the stricter. "owner": the OSC step whose person or service
# provider has the item at that stage, when she has not said.
ENGINEERING_STAGES = {
    "design": {"threshold": 15, "tier": "EXTERNAL", "label": "design, with the engineer",
               "osc": (r"^Order Engineering - Piers", r"^Receive Engineering - Piers"),
               "owner": [(r"^Receive Engineering - Piers", "serviceProvider"),
                         (r"^Order Engineering - Piers", "serviceProvider")]},
    "review": {"threshold": 10, "tier": "INTERNAL", "label": "internal review",
               "osc": (r"^Receive Engineering - Piers", r"^Forward Engineers Footing/Slab"),
               "owner": [(r"^Review Engineering - Piers", "user")]},
}

# Outstanding-item families: how a report item name maps to OSC evidence.
# An item name that matches more than one family, or a family's exclude, gets
# no rule: it is kept and flagged for the officer rather than guessed.
# done_activities: ALL must be complete/N-A for activity-based completion.
# done_docs: ANY document description match counts as completion evidence,
# but never while one of the family's done_activities is still open.
# pending_activities: any of these pending -> the item is active; the first
# pending one's assigned user / service provider is "who it is with".
# order_activities: the step that sends the item out (Order Engineering - X);
# with the chain steps, it dates DATE SUBMITTED for the first pending step.
# threshold: business days before RED for this item whoever has it, in place
# of the tier's (the officer, 27 Oct 2026: covenant 10, an amended DA about 60).
# stages: an item whose limit follows the stage it is at (ENGINEERING_STAGES).
# columns: the item is also tracked from the export's own columns, listed or
# not (COLUMN_CYCLES below).
# submitted_docs: order/application/receipt documents whose OLDEST attach
# date evidences DATE SUBMITTED (verify grade — .msg files are dragged into
# OSC after the send, PO-9).
# tier: default tier when nothing better says who the item is with.
FAMILIES = [
    # The structural engineering OSC tracks (slab and structural steel chains).
    # Other disciplines have no OSC steps, so they get no rule.
    {"key": "ENGINEERING", "tier": "EXTERNAL", "stages": ENGINEERING_STAGES, "columns": True,
     "match": r"\bENG(INEERING)?\b",
     "exclude": r"\b(HYDRAULIC|CIVIL|STORMWATER|DRAINAGE|GEOTECH\w*|ELECTRICAL|FIRE|TRAFFIC|ACOUSTIC|BUSHFIRE)\b",
     "done_activities": [r"Receive Engineering", r"Review Engineering", r"Forward Engineers"],
     "pending_activities": [r"Receive Engineering", r"Review Engineering",
                            r"Amend Working Drawings to Suit", r"Forward Engineers"],
     "order_activities": [r"Order Engineering"],
     "done_docs": [], "submitted_docs": []},
    {"key": "COVENANT", "tier": "EXTERNAL", "threshold": 10, "columns": True,
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
    # The report says SYDNEY WATER or SYD WATER; OSC files the approval as
    # "APPROVAL - SYD WATER ..." (observed on a pilot job, 19 Oct 2026 base).
    {"key": "SYDNEY WATER", "tier": "COUNCIL",
     "match": r"\b(SYD(NEY)? WATER|TAP.?IN)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"SYD(NEY)? WATER.*APPROV", r"APPROVAL.*SYD(NEY)? WATER", r"TAP.?IN.*APPROV"],
     "submitted_docs": [r"(SYD(NEY)? WATER|TAP.?IN).*(APPLICATION|RECEIPT)"]},
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
     "done_exclude": None,  # the receipt IS the outcome: contributions paid
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
     "exclude": r"\bAMENDED\s+DA\b",  # lodging an amended DA is part of that item
     "done_activities": [], "pending_activities": [],
     "done_docs": [], "submitted_docs": []},
    # Named by the officer on 27 Oct 2026: both sit with Council. Document
    # patterns follow the house naming (APPROVAL - X, X APPLICATION, X
    # RECEIPT); no ROP or amended-DA document has been seen yet.
    {"key": "ROP", "tier": "COUNCIL",
     "match": r"\b(ROP|ROAD\s+OPENING)\b",
     "done_activities": [], "pending_activities": [],
     "done_docs": [r"(ROP|ROAD\s+OPENING).*(APPROV|PERMIT)", r"APPROVAL\s*-\s*(ROP|ROAD\s+OPENING)"],
     "submitted_docs": [r"(ROP|ROAD\s+OPENING).*(APPLICATION|RECEIPT)"]},
    {"key": "AMENDED DA", "tier": "COUNCIL", "threshold": 60,
     "match": r"\bAMENDED\s+(DA|DEVELOPMENT\s+APPLICATION)\b",
     "done_activities": [], "pending_activities": [],
     # "AMENDED DA - SIGNED CONSENT" is the owner's consent to lodge (filed the day it went in on
     # a pilot job, 28 Sep 2026), so it dates the submission and never counts as the approval.
     "done_docs": [r"AMENDED\s+(DA|DEVELOPMENT).*(APPROV|DETERMINATION)",
                   r"APPROVAL\s*-\s*AMENDED\s+(DA|DEVELOPMENT)"],
     "submitted_docs": [r"AMENDED\s+(DA|DEVELOPMENT).*(APPLICATION|RECEIPT|LODG|SIGNED\s+CONSENT)"]},
]

def _iso_day(s):
    """The Sydney date of an OSC timestamp (documents and alerts carry real UTC times)."""
    return sydney_date(s)


def _date_or_text(val):
    """A main-sheet cell: numeric (an Excel serial) as a date, else text."""
    if val is None or val == "":
        return ("", xlsx_min.S_WRAP)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return (float(val), xlsx_min.S_DATE)
    s = str(val).strip()
    if re.match(r"^\d+(\.\d+)?$", s):
        return (float(s), xlsx_min.S_DATE)
    return (s, xlsx_min.S_WRAP)


def _ddmmyyyy(iso):
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return d.strftime("%d/%m/%Y")


def families_of(item_name):
    """Every family whose match fits the item name (and whose exclude does not)."""
    up = item_name.upper()
    return [fam for fam in FAMILIES
            if re.search(fam["match"], up) and not (fam.get("exclude") and re.search(fam["exclude"], up))]


def family_of(item_name):
    """The one family for an item, or None when none or several fit (the officer decides)."""
    found = families_of(item_name)
    return found[0] if len(found) == 1 else None


def _is_outcome(desc, fam):
    exclude = fam.get("done_exclude", NOT_AN_OUTCOME)
    return not exclude or desc.startswith("APPROVAL") or not re.search(exclude, desc)


def item_key(item_name):
    fam = family_of(item_name)
    return fam["key"] if fam else item_name.upper()


def item_keys(names):
    """State keys for one job's items: the evidence family (so "SEW EJECTION" and "SEWER EJECTION"
    stay one item from week to week), unless two items share a family, when each keeps its own by
    name, so one item's dates never overwrite another's."""
    fams = [item_key(n) for n in names]
    return [f"{k}: {norm_item(n)}" if fams.count(k) > 1 else k for k, n in zip(fams, names)]


def _alike(a, b):
    """Two names mostly made of the same words (at least half of all their words shared):
    "SEW EJECTION PUMP APPROVAL" and "SEWER EJECTION PUMP APPROVAL" are, "S68 APPLICATION" and
    "S68 APPROVAL" are not."""
    wa, wb = (set(re.findall(r"[A-Z0-9]+(?:\.[A-Z0-9]+)*", re.sub(r"\([^)]*\)", "", s.upper()))) for s in (a, b))
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.5


def _edit_text(e):
    parts = []
    if e.get("note"):
        parts.append(f"note \"{e['note'][:80]}{'...' if len(e['note']) > 80 else ''}\"")
    if "assigned_to" in e:
        parts.append(f"assigned to \"{e['assigned_to']}\"" if e["assigned_to"] else "assigned-to cleared")
    if "date_submitted" in e:
        parts.append(f"date submitted {_ddmmyyyy(e['date_submitted'])}" if e["date_submitted"]
                     else "date submitted emptied (not yet submitted)")
    if e.get("date_resolved"):
        parts.append(f"resolved {_ddmmyyyy(e['date_resolved'])}")
    if "note" in e and not e["note"]:
        parts.append("note cleared")
    return "your Items sheet: " + ", ".join(parts)


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


def doc_evidence(snapshot, patterns, since_iso, oldest=False, keep=None):
    """Newest (or oldest) document matching any pattern; (doc, is_new_since).

    ``keep``, when given, is a further test on the description (outcome documents only).
    """
    best = None
    for d in snapshot.get("documents", []):
        desc = (d.get("description") or "").upper()
        if any(re.search(p, desc) for p in patterns) and (keep is None or keep(desc)):
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
      verdict in {"complete", "complete-old-evidence", "active", "conflict", "unknown"}.
    "conflict": an outcome document is on the job while the family's OSC step
    is still open, so the item is kept and flagged, never resolved.
    """
    fam = family_of(item["name"])
    if fam is None:
        several = families_of(item["name"])
        if several:
            return ("unknown", "the item name fits more than one evidence rule ("
                    + ", ".join(f["key"] for f in several) + ") — officer to say which", None, None, None)
        return "unknown", "no evidence rule for this item", None, None, None
    acts_seen = False
    open_step = None
    if fam["done_activities"]:
        states = [activity_state(snapshot, p) for p in fam["done_activities"]]
        acts_seen = any(m for m, _, _ in states)
        open_step = next((p for m, c, p in states if m and not c), None)
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
        doc, is_new = doc_evidence(snapshot, fam["done_docs"], since_iso, keep=lambda d: _is_outcome(d, fam))
        if doc:
            ev = (f"document \"{doc.get('description')}\" v{doc.get('version')} "
                  f"attached {_iso_day(doc.get('attachedOnUtc'))}")
            if open_step:
                owner, field = _owner_of(open_step)
                return ("conflict", f"{ev}, but OSC activity \"{open_step.get('description')}\" is still open",
                        owner, field, None)
            return ("complete" if is_new else "complete-old-evidence"), ev, None, None, _iso_day(doc.get("attachedOnUtc"))
    for p in fam.get("pending_activities", []):
        matched, _, first_pending = activity_state(snapshot, p)
        if matched and first_pending:
            owner, field = _owner_of(first_pending)
            return "active", f"OSC activity \"{first_pending.get('description')}\" pending", owner, field, None
    if acts_seen:
        return "unknown", "activities matched but state unclear", None, None, None
    return "unknown", "no completion evidence found", None, None, None


# The engineering and covenant columns the export gained on 28 Sep 2026, aged
# like RFI items (the officer, 27 Oct 2026; engineering by stage since her
# correction, ENGINEERING_STAGES). Each is a chain of steps: in flight from its
# latest dated step until the closing step is dated on or after it.
# Engineering goes round again when a revision is received or reviewed after
# the last forward, which OSC does not re-date, so the officer's Date resolved
# closes a cycle too. "stage": the stage the latest dated step starts (ordered:
# the engineer is designing; received or reviewed: Transpire is reviewing, as
# she dated the pilot jobs on 22 Oct 2026). Header text is matched by its
# start ("Review Engineering - <reviewer>"); OSC's own closing step is read as
# well, being fresher than the base export.
COLUMN_CYCLES = {
    "ENGINEERING": {"steps": {"engineering ordered": "ordered", "receive engineering": "received",
                              "review engineering": "reviewed"},
                    "stage": {"ordered": "design", "received": "review", "reviewed": "review"},
                    "closing": "forward engineering", "closed": "forwarded to the certifier",
                    "closing_activity": r"^Forward Engineers Footing/Slab Design", "label": "engineering columns"},
    "COVENANT": {"steps": {"covenant ordered": "ordered"}, "closing": "received covenant approval",
                 "closed": "approved", "closing_activity": r"^Receive Covenant Approval",
                 "label": "covenant columns"},
}


def _column_date(row, header_start):
    """(ISO date or None, raw text) of the base column whose header starts with ``header_start``."""
    if header_start == "received covenant approval":
        cell = row["received_covenant"]
        return cell["date"], cell["raw"]
    for header, cell in row["extra"].items():
        if " ".join(header.lower().split()).startswith(header_start):
            return cell["date"], cell["raw"]
    return None, None


def column_cycle(key, row, snapshot):
    """The tracked chain behind an item's columns: {since, done_on, detail} or None when never started."""
    spec = COLUMN_CYCLES[key]
    steps = [(word, _column_date(row, name)[0]) for name, word in spec["steps"].items()]
    dated = [(d, word) for word, d in steps if d]
    if not dated:
        return None
    since, step = max(dated)
    closed, closed_raw = _column_date(row, spec["closing"])
    not_applicable = bool(re.match(r"^\s*(N/?A|NOT APPLICABLE)\b", str(closed_raw or ""), re.I))
    if snapshot:
        steps_osc = [a for a in snapshot.get("activities", [])
                     if re.search(spec["closing_activity"], a.get("description") or "", re.I)]
        osc = [_iso_day(a["completionDate"]) for a in steps_osc
               if a.get("completionDate") and not a.get("isNotApplicable")]
        closed = max([d for d in [closed] + osc if d], default=None)
        not_applicable = not_applicable or (bool(steps_osc) and all(a.get("isNotApplicable") for a in steps_osc))
    if not_applicable:
        return {"since": since, "done_on": since, "not_applicable": True,
                "detail": f"{spec['label']}: {step} {_ddmmyyyy(since)}, marked not applicable"}
    done_on = closed if closed and closed >= since else None
    if done_on:
        after = f"{spec['closed']} {_ddmmyyyy(done_on)}"
    elif closed:
        after = f"not {spec['closed']} since (last {_ddmmyyyy(closed)})"
    else:
        after = f"not {spec['closed']} yet" + (f" ({str(closed_raw).strip()})" if str(closed_raw or "").strip() else "")
    return {"since": since, "done_on": done_on, "stage": spec.get("stage", {}).get(step),
            "detail": f"{spec['label']}: {step} {_ddmmyyyy(since)}, {after}"}


def _first_step(snapshot, pattern):
    """The first OSC activity whose description matches ``pattern``, or None."""
    return next((a for a in (snapshot or {}).get("activities", [])
                 if re.search(pattern, a.get("description") or "", re.I)), None)


def _step_done(activity):
    return bool(activity and activity.get("completionDate") and not activity.get("isNotApplicable"))


def _osc_stage(fam, snapshot):
    """The stage OSC shows for an item with stages: the step that starts it done, the one that ends
    it neither done nor marked not applicable. None when OSC says neither."""
    for stage, spec in fam["stages"].items():
        start, end = (_first_step(snapshot, p) for p in spec["osc"])
        if _step_done(start) and end and not end.get("completionDate") and not end.get("isNotApplicable"):
            return stage
    return None


def _names_provider(text, fam, snapshot):
    """Her Assigned to names the service provider OSC holds for the item's outside stage (the
    engineering firm on the order and receive steps), so it sits with that outside party."""
    generic = {"CONSULTING", "CONSULTANTS", "ENGINEERS", "ENGINEERING", "GROUP", "SERVICES", "AUSTRALIA"}
    said = set(re.findall(r"[A-Z]{4,}", (text or "").upper())) - generic
    if not said:
        return False
    steps = [p for spec in fam["stages"].values() for p, field in spec["owner"] if field == "serviceProvider"]
    return any(said & (set(re.findall(r"[A-Z]{4,}", a["serviceProvider"].upper())) - generic)
               for a in (snapshot or {}).get("activities", [])
               if a.get("serviceProvider") and any(re.search(p, a.get("description") or "", re.I) for p in steps))


def item_stage(fam, item, snapshot):
    """(stage, how) for an item with stages before the officer's say: its columns, else OSC, else the
    stricter stage. None for other items."""
    stages = (fam or {}).get("stages")
    if not stages:
        return None, None
    if item.get("column_stage"):
        return item["column_stage"], "columns"
    found = _osc_stage(fam, snapshot) if snapshot else None
    if found:
        return found, "osc"
    return min(stages, key=lambda s: stages[s]["threshold"]), "default"


def _stage_owner(fam, stage, snapshot):
    """(name, field) of whoever OSC says has the item at this stage, or (None, None)."""
    for pattern, field in fam["stages"][stage]["owner"]:
        step = _first_step(snapshot, pattern)
        if step and step.get(field):
            return step[field], field
    return None, None


def _stage_words(item):
    """The stage after an item's limit, as " (internal review)", with how it was told when not by
    its own columns or OSC."""
    fam = family_of(item["name"]) if item.get("stage") else None
    if not fam or not fam.get("stages"):
        return ""
    how = {"assigned": ": from your Assigned to", "rfi list": ": from the RFI list",
           "default": ": assumed, the stricter"}.get(item.get("stage_how"), "")
    return f" ({fam['stages'][item['stage']]['label']}{how})"


def _since_last_week(item, last, have_last):
    """What changed on a row since the draft she checked last week, so she can pass over the rest:
    the flag, the date submitted or who has it (days going up is not news). None when there was no
    earlier draft to compare with, or for a resolved row, which is news by itself."""
    if item.get("resolved") or not have_last:
        return None
    if last is None:
        return "new this week"
    said = []
    if item["flag"] != last["flag"]:
        said.append(f"now {item['flag']} (was {last['flag'] or 'blank'})"
                    + (" after your change" if last.get("hers") else ""))
    if (item.get("date_submitted") or None) != (last["date_submitted"] or None):
        said.append(f"date submitted now {_ddmmyyyy(item.get('date_submitted')) or 'empty'} "
                    f"(was {_ddmmyyyy(last['date_submitted']) or 'empty'})")
    if (item.get("assigned_to") or "") != (last["assigned_to"] or ""):
        said.append(f"assigned to now {item.get('assigned_to') or '?'} (was {last['assigned_to'] or '?'})")
    return ("since last week: " + "; ".join(said)) if said else "no change since last week"


def _last_row(job_no, name, last_rows, now_names):
    """Last week's row for an item: the same name, else (renamed on her report, "SEW EJECTION" to
    "SEWER EJECTION") the one row of the same evidence family and a similar name that is gone this week."""
    found = last_rows.get((job_no, norm_item(name)))
    if found:
        return found
    alike = [v for (job, key), v in last_rows.items() if job == job_no and key not in now_names
             and item_key(v["item"]) == item_key(name) and _alike(v["item"], name)]
    return alike[0] if len(alike) == 1 else None


def _note_days(note, limit):
    """Day counts her note gives that differ from the row's limit ("HBCF takes 10 days"): a rule she
    has written down that the draft may not be applying."""
    said = {int(n) for n in re.findall(r"\b(\d{1,3})\s*(?:business\s+|working\s+)?days?\b", note or "", re.I)}
    return sorted(said - {limit})


def _limits_text():
    """Each family's own limits, for the evidence note."""
    out = []
    for f in FAMILIES:
        if f.get("stages"):
            out.append(f"{f['key']} " + " / ".join(f"{s['threshold']} {s['label']}" for s in f["stages"].values()))
        elif f.get("threshold"):
            out.append(f"{f['key']} {f['threshold']}")
    return ", ".join(out)


def _chain_of(desc):
    """Which item chain a step belongs to. Every job carries two engineering chains, slab and
    structural steel, and OSC misspells some of their steps ("Strucutral"), so the chain is told
    by its subject words, not by the exact text after " - "."""
    up = (desc or "").upper()
    if re.search(r"SLAB|FOOTING|PIER", up):
        return "SLAB"
    if re.search(r"STEEL", up):
        return "STEEL"
    return ""


def submitted_evidence(item, snapshot, lodged_iso=None):
    """Best OSC evidence for DATE SUBMITTED: (iso_date, description) or (None, None).

    Order: oldest order/application/receipt document for the family; for
    activity-backed families the last completed step before the first
    pending one in the same chain (so a pending Receive step dates from its
    Order step, and a pending Review step from the Receive step); an alert whose
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
    chain = fam.get("order_activities", []) + fam.get("pending_activities", []) + fam.get("done_activities", [])
    for p in fam.get("pending_activities", []):
        matched, _, first_pending = activity_state(snapshot, p)
        if matched and first_pending:
            seq = first_pending.get("sequence") or 0
            mine = _chain_of(first_pending.get("description"))
            before = [a for a in snapshot.get("activities", [])
                      if a.get("completionDate") and not a.get("isNotApplicable")
                      and (a.get("sequence") or 0) < seq
                      and _chain_of(a.get("description")) == mine
                      and any(re.search(q, a.get("description") or "", re.I) for q in chain)]
            if before:
                last = max(before, key=lambda a: a.get("sequence") or 0)
                return _iso_day(last["completionDate"]), f"step before \"{last.get('description')}\" completed"
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


STATE_FILE = "ba-items-first-seen.json"
STATE_PREVIOUS = "ba-items-first-seen.prev.json"


class StateError(RuntimeError):
    pass


class DraftInputError(RuntimeError):
    pass


def load_state(state_dir):
    p = Path(state_dir) / STATE_FILE
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        # Never start afresh: officer values carried through plain-export weeks live only here.
        raise StateError(f"{p} is not readable JSON ({exc}). Nothing was drafted. The run before last is in "
                         f"{STATE_PREVIOUS} beside it; restore it with a person's check.") from exc
    return {job: {k: _normalise_entry(v) for k, v in (items or {}).items()}
            for job, items in raw.items()}


def save_state(state_dir, state):
    """Write to a temp file and swap it in, so a cut-off write (an SMB drop) never leaves half a file;
    the state before this run is kept as STATE_PREVIOUS."""
    p = Path(state_dir) / STATE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    if p.exists():
        shutil.copyfile(p, p.with_name(STATE_PREVIOUS))
    os.replace(tmp, p)


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
    officer values read back from last week's Items sheet (or v0.2 L-O columns).
    """
    fam = family_of(item["name"])
    flags = []
    column_since = item.get("column_since")
    stage, stage_how = item_stage(fam, item, snapshot)

    # ---- assigned to (hers belongs to the cycle current when she gave it, like her date below:
    # a newer step in the item's columns means it has moved on, so it is worked out again)
    if column_since and entry.get("assigned_source") == "officer":
        if column_since > entry.setdefault("assigned_cycle", column_since):
            entry.update(assigned_to=None, assigned_source=None, ai_assigned_to=None)
            entry.pop("assigned_cycle", None)
    assigned, src = _resolve_sticky(item.get("assigned_to"), entry,
                                    "ai_assigned_to", "assigned_to", "assigned_source")
    fallback_echo = assigned if (assigned and src is None) else None
    wo = re.match(r"^W/?O\s+(.+)$", (item.get("state") or "").strip(), re.I)
    if src != "officer":
        assigned, src = None, None
        stage_owner, stage_field = _stage_owner(fam, stage, snapshot) if stage else (None, None)
        if wo:
            assigned, src = wo.group(1).strip(), "report (W/O)"
        elif stage_owner:
            assigned, src = stage_owner, f"osc {stage_field}"
        elif item.get("owner"):
            assigned, src = item["owner"], f"osc {item.get('owner_field') or 'activity'}"
        elif fallback_echo:
            assigned, src = fallback_echo, "carried"
    tier = None
    if stage:
        # who she says has it decides the stage (the engineer: design; Transpire: review), on the
        # Items sheet, else as "(W/O X)" on her RFI list; a person's name says neither, so the
        # columns or OSC decide
        for text, how in ((assigned if src == "officer" else None, "assigned"),
                          (wo.group(1) if wo else None, "rfi list")):
            said = tier_for(text) or ("EXTERNAL" if _names_provider(text, fam, snapshot) else None)
            told = [s for s, spec in fam["stages"].items() if spec["tier"] == said]
            if told:
                stage, stage_how = told[0], how
                break
        tier = fam["stages"][stage]["tier"]
    elif src == "officer" or src == "report (W/O)" or src == "carried":
        tier = tier_for(assigned)
    elif src and src.startswith("osc"):
        tier = "INTERNAL" if item.get("owner_field") == "user" else (fam["tier"] if fam else None)
        tier = tier or tier_for(assigned)
    if tier is None:
        if fam:
            tier = fam["tier"]
            # A person's name the officer typed is hers to give; it just has no tier of its own.
            if assigned and src != "officer":
                flags.append(f"assignee \"{assigned}\" not recognised — tier from item type ({tier})")
        else:
            tier = "INTERNAL"
            flags.append("no assignee and no item rule — tier INTERNAL (strictest)")
    if not assigned:
        flags.append("assigned-to unknown")

    # ---- date submitted: the officer's date (or her "not yet submitted"), else the item's
    # columns, else OSC evidence, else last week's value, else the first sighting (assumed)
    if item.get("date_submitted"):
        entry.pop("not_submitted", None)
    if column_since and entry.get("date_source") == "officer":
        # Her date (or "not yet submitted") belongs to the cycle current when she gave it; only a
        # newer step in the item's columns starts a new cycle and replaces it.
        if column_since > entry.setdefault("date_cycle", column_since):
            entry.update(date_source=None, date_submitted=None)
            entry.pop("not_submitted", None)
            entry.pop("date_cycle", None)
    if entry.get("not_submitted"):
        submitted, dsrc = None, "officer: not yet submitted"
    else:
        submitted, dsrc = _resolve_sticky(item.get("date_submitted"), entry,
                                          "ai_date_submitted", "date_submitted", "date_source")
    echo = submitted if (submitted and dsrc is None) else None
    if not (dsrc or "").startswith("officer"):
        submitted, dsrc = None, None
        if column_since:
            submitted, dsrc = column_since, item.get("column_detail")
        elif snapshot:
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

    # ---- days + flag (an item not yet submitted counts no days)
    threshold = fam["stages"][stage]["threshold"] if stage else ((fam or {}).get("threshold") or TIERS[tier])
    end = item.get("date_resolved") if item.get("resolved") else asof
    days = business_days(submitted, end) if (end and submitted) else None
    if item.get("resolved"):
        flag = ""
    elif days is None:
        flag = "NOT SUBMITTED"
    else:
        flag = "YELLOW" if days <= threshold else "RED"

    entry["item"] = norm_item(item["name"])  # which item a shared-family entry belongs to
    item.update({"assigned_to": assigned, "assigned_source": src, "tier": tier, "stage": stage,
                 "stage_how": stage_how, "threshold": threshold, "date_submitted": submitted,
                 "date_source": dsrc, "days": days, "flag": flag,
                 "assumed": dsrc.startswith("assumed") if dsrc else False})
    item["age_flags"] = flags
    if (item.get("flagged") and item.get("verdict") == "unknown" and (dsrc or "").startswith("officer")
            and item.get("evidence") in ("no completion evidence found", "no evidence rule for this item")):
        item["flagged"] = False  # she has dated the item herself; OSC having no evidence yet is no news
    if flags:
        item["flagged"] = True

    # remember what the AI wrote so next week's echo is recognisable, and the cycle the draft shows
    entry["ai_assigned_to"] = assigned
    entry["ai_date_submitted"] = submitted
    if column_since:
        entry["since_shown"] = column_since
    else:
        entry.pop("since_shown", None)
    if src != "officer":
        entry["assigned_to"] = assigned
        entry["assigned_source"] = src
    if not (dsrc or "").startswith("officer"):
        entry["date_submitted"] = submitted
        entry["date_source"] = dsrc
    return item


def apply_officer_edit(entry, edit, source):
    """Fold one Items-sheet edit (ba_report_parse.officer_edits) into the item's state: her values
    stick until she changes them again."""
    # Her values belong to the cycle on the draft she edited, which may have moved on since.
    shown = entry.get("since_shown")
    if "assigned_to" in edit:
        if shown:
            entry["assigned_cycle"] = shown
        else:
            entry.pop("assigned_cycle", None)  # set from the item's columns when it is aged
        if edit["assigned_to"]:
            entry.update(assigned_to=edit["assigned_to"], assigned_source="officer")
        else:  # cleared: back to what the evidence says
            entry.update(assigned_to=None, assigned_source=None, ai_assigned_to=None)
    if "date_submitted" in edit:
        if shown:
            entry["date_cycle"] = shown
        else:
            entry.pop("date_cycle", None)
        if edit["date_submitted"]:
            entry.update(date_submitted=edit["date_submitted"], date_source="officer")
            entry.pop("not_submitted", None)
        else:  # she emptied the date: the item has not gone out yet
            entry.update(date_submitted=None, date_source="officer", not_submitted=True)
    if edit.get("date_resolved"):
        entry["officer_resolved"] = edit["date_resolved"]
        entry.pop("resolved_shown", None)
    if "note" in edit:
        if edit["note"]:
            entry["officer_note"] = edit["note"]
        else:
            entry.pop("officer_note", None)
    entry["edited_in"] = source


def claim_state(jstate, listed):
    """Keep an item's state when its key changes because a second item of its evidence family joins
    or leaves the list ("ENERGY" <-> "ENERGY: ENERGYREPORT"): the entry follows the item it belongs to."""
    keys = {k for _, k in listed}
    for item, key in listed:
        if key in jstate:
            continue
        fam, want = item_key(item["name"]), norm_item(item["name"])
        sharing = sum(1 for i, _ in listed if item_key(i["name"]) == fam)
        for old in (fam, f"{fam}: {want}"):
            owner = (jstate.get(old) or {}).get("item")
            if old != key and old in jstate and old not in keys and (owner == want or (owner is None and sharing == 1)):
                jstate[key] = jstate.pop(old)
                break


# ------------------------------------------------------------------ draft
def build_draft(prev_path, snapshot_dir, out_dir, asof=None, state_dir=None, jobs=None, edited=None, drafted=None):
    """``edited``: last week's draft as the officer left it (her Items-sheet changes are read from it,
    compared with ``drafted``, the same draft as written; default: that file in ``out_dir``)."""
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
    if not covers(asof):
        evidence["notes"].append(f"the NSW holiday table in nsw_holidays.py ends in {LAST_YEAR}, so business-day "
                                 f"counts in {asof[:4]} miss that year's public holidays — add them first")
    # The officer's base is a plain export with no Items sheet; what she typed last week lives in
    # the draft she edited, so it is read from there and kept in the state from now on.
    edits_by_job, edit_source, last_names, last_rows = {}, None, {}, {}
    if edited:
        name = re.sub(r"\s*\(officer-edited\)", "", Path(edited).name)
        # the copy kept when it was delivered (a later re-run of that Monday may have replaced the other)
        drafted = Path(drafted) if drafted else next(
            (c for c in (Path(out_dir) / "delivered" / name, Path(out_dir) / name) if c.exists()),
            Path(out_dir) / name)
        if not drafted.exists():
            raise DraftInputError(f"the draft as written ({drafted}) is needed to tell the officer's changes from "
                                  "the draft's own values; pass --drafted")
        found = officer_edits(edited, drafted)
        for e in found["edits"]:
            edits_by_job.setdefault(e["job_no"], []).append(e)
        last_names, last_rows = found["drafted_names"], found["last_rows"]
        edit_source = Path(edited).name
        evidence["notes"].append(f"the officer's Items-sheet changes read from {edit_source}: "
                                 f"{len(found['edits'])} row(s) changed")
        for u in found["unmatched"]:
            evidence["notes"].append(f"edited Items row {u['row']} ({u['job_no']} \"{u['item']}\") matches no "
                                     "drafted row — not used")
    # The draft reproduces the base's columns exactly (located by header
    # text); v0.2's per-item columns L-O are dropped from the main sheet in
    # favour of the Items sheet.
    columns = [c for c in prev["columns"] if c["key"] != "legacy_item_col"]
    if len(columns) != len(prev["columns"]):
        evidence["notes"].append("v0.2 per-item columns on the base's main sheet are not carried; "
                                 "per-item values now live on the Items sheet")
    out_rows = [[(c["header"], xlsx_min.S_HEADER) for c in columns]]
    items_rows = [[(h, xlsx_min.S_HEADER) for h in ITEMS_SHEET_HEADERS]]
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
                # A snapshot step that stopped part-way leaves last week's files beside fresh ones.
                taken = _iso_day(snapshot.get("retrievedAtUtc"))
                if str(snapshot.get("contractNumber") or job_no) != job_no:
                    job_ev["flags"].append(f"snapshot {snap_path.name} is for job {snapshot.get('contractNumber')} — "
                                           "not used, row carried forward untouched")
                    snapshot = None
                elif not taken or taken < since:
                    job_ev["flags"].append(f"snapshot taken {taken or 'at an unknown time'}, before the base report "
                                           f"({since}) — not used, row carried forward untouched; re-run the "
                                           "snapshot step")
                    snapshot = None
            else:
                job_ev["flags"].append("no snapshot — no fresh OSC evidence this week; items aged from the report "
                                       "and your Items sheet only")

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
        if in_scope and g.get("other_text"):
            job_ev["flags"].append(f"the RFI-items cell reads \"{g['raw']}\", not a PENDING list — carried verbatim")
        jstate = state.setdefault(job_no, {}) if in_scope else {}
        items_out = []      # open RFI items, in the cell's order
        resolved_out = []   # RFI items resolved this cycle (shown once)
        col_out = []        # open items tracked from their columns only (Items sheet, never the RFI cell)
        col_resolved = []
        listed = []         # (item, state key) for the RFI cell's items
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
                for um in row.get("items_unmatched", []):
                    job_ev["flags"].append(
                        f"Items sheet row \"{um['item']}\" matches no item in the PENDING list — "
                        "not used; add the item to the main sheet or correct the name")
                if g.get("resolved"):
                    job_ev["changes"].append(
                        {"item": ", ".join(i["name"] for i in g["resolved"]),
                         "action": "resolved-line-dropped",
                         "evidence": "shown last cycle as RESOLVED; not carried"})
                keys = item_keys([i["name"] for i in g["items"]])
                listed = list(zip(g["items"], keys))
                if in_scope:
                    claim_state(jstate, listed)
                for k in sorted({k.split(": ")[0] for k in keys if ": " in k}):
                    job_ev["changes"].append({"item": k, "action": "shared-rule",
                                              "evidence": f"two or more items share the {k} evidence rule; "
                                                          "each keeps its own dates"})

        # ---- the engineering and covenant columns (PO-11b; engineering by stage, PO-11c)
        cycles = {}
        if in_scope and not row["ba_received"]["date"]:
            for fkey in COLUMN_CYCLES:
                cyc = column_cycle(fkey, row, snapshot)
                if cyc:
                    cycles[fkey] = cyc
        listed_families = {item_key(i["name"]) for i, _ in listed}
        unlisted = [fkey for fkey in cycles if fkey not in listed_families]

        # ---- the officer's edits from last week's draft, matched by name, else by evidence family
        targets = [(i["name"], k) for i, k in listed] + [(fkey, fkey) for fkey in unlisted]
        this_week = {norm_item(n) for n, _ in targets}
        for e in edits_by_job.get(job_no, []) if in_scope else []:
            e = dict(e)
            hit = [k for n, k in targets if norm_item(n) == norm_item(e["item"])]
            renamed = None
            if not hit and norm_item(e["item"]) not in this_week:
                # A rename ("SEW" -> "SEWER EJECTION"): the only item of the same evidence family that
                # is new this week. Never another item that was already on last week's draft.
                fam = [(n, k) for n, k in targets if item_key(n) == item_key(e["item"])
                       and norm_item(n) not in last_names.get(job_no, set()) and _alike(n, e["item"])]
                if len(fam) == 1:
                    renamed, hit = fam[0][0], [fam[0][1]]
            for field in ("date_submitted_unreadable", "date_resolved_unreadable"):
                if e.get(field):
                    label = "Date submitted" if field.startswith("date_submitted") else "Date resolved"
                    job_ev["flags"].append(f"your {label} \"{e[field]}\" on \"{e['item']}\" could not be read as a "
                                           "date, so it was not used — please type it as dd/mm/yyyy")
            if len(hit) != 1:
                closed = (e["was_resolved"] or e.get("date_resolved") or not g["pending"]
                          or row["ba_received"]["date"])
                if closed:  # history: the item, its list or the approval stage had already closed
                    job_ev["changes"].append({"item": e["item"], "action": "officer-edit-noted",
                                              "evidence": _edit_text(e) + " (closed, kept for the record)"})
                else:
                    job_ev["flags"].append(f"your Items-sheet change to \"{e['item']}\" was not used: the item is "
                                           "no longer on the report")
                continue
            if renamed and e.pop("date_resolved", None):
                job_ev["flags"].append(f"your Date resolved on \"{e['item']}\" was not carried to \"{renamed}\" "
                                       "(a different name this week) — type it again if that item is finished")
            apply_officer_edit(jstate.setdefault(hit[0], {}), e, edit_source)
            job_ev["changes"].append({"item": e["item"] + (f" -> {renamed}" if renamed else ""),
                                      "action": "officer-edit", "evidence": _edit_text(e)})

        for item, key in listed:
            st = jstate.setdefault(key, {})
            fam = family_of(item["name"])
            cyc = cycles.get(fam["key"]) if fam and fam.get("columns") else None
            off = st.get("officer_resolved")
            if off and (st.get("resolved_shown") or (cyc and off < cyc["since"])):
                st.pop("officer_resolved", None)  # an old resolution: shown already, or for an earlier cycle
            if st.get("officer_resolved"):
                verdict, ev, owner, owner_field, ev_date = (
                    "complete", f"resolved on your Items sheet ({_ddmmyyyy(st['officer_resolved'])})",
                    None, None, st["officer_resolved"])
            elif snapshot:
                verdict, ev, owner, owner_field, ev_date = check_item(item, snapshot, since)
            else:
                verdict, ev, owner, owner_field, ev_date = "unknown", "no snapshot", None, None, None
            if cyc and cyc["done_on"] and verdict != "complete":
                if verdict in ("active", "conflict"):
                    verdict, ev = "conflict", f"{cyc['detail']}, but {ev}"
                else:
                    verdict = "complete" if cyc["done_on"] >= since else "complete-old-evidence"
                    ev, ev_date = cyc["detail"], cyc["done_on"]
            rec = {"name": item["name"], "state": item["state"], "key": key, "verdict": verdict,
                   "owner": owner, "owner_field": owner_field,
                   "assigned_to": item.get("assigned_to"),
                   "date_submitted": item.get("date_submitted"),
                   "evidence": ev, "flagged": False, "resolved": False}
            if cyc and not cyc["done_on"]:
                rec.update(column_since=cyc["since"], column_detail=cyc["detail"], column_stage=cyc.get("stage"),
                           evidence=f"{cyc['detail']}; {ev}")
            if verdict == "complete":
                rec.update({"resolved": True, "date_resolved": ev_date or asof})
                job_ev["changes"].append({"item": item["name"], "action": "resolved", "evidence": ev})
                resolved_out.append(rec)
                continue
            rec["flagged"] = verdict in ("unknown", "complete-old-evidence", "conflict")
            if verdict == "complete-old-evidence":
                job_ev["flags"].append(
                    f"item \"{item['name']}\": completion evidence predates {since} ({ev}) — kept, verify")
            elif verdict == "conflict":
                job_ev["flags"].append(f"item \"{item['name']}\": {ev} — kept, verify")
            items_out.append(rec)

        for fkey in unlisted:
            cyc, st = cycles[fkey], jstate.get(fkey) or {}
            if not st.get("cycle_since") or cyc["since"] > st["cycle_since"]:
                # first sight, or a step dated later than the cycle on record: a new cycle. (A step
                # whose date turns to text moves "since" back; that is still the same cycle.)
                for k in ("officer_resolved", "closed_on"):
                    if (st.get(k) or "") < cyc["since"]:
                        st.pop(k, None)
                if not (st.get("officer_resolved") or st.get("closed_on")):
                    st.pop("resolved_shown", None)
                    st.pop("tracking", None)
                st["cycle_since"] = cyc["since"]
            since_on = st["cycle_since"]
            closed_on = st.get("officer_resolved") or st.get("closed_on") or cyc["done_on"]
            if closed_on and (st.get("resolved_shown") or not (st.get("tracking") or st.get("officer_resolved"))):
                if st.get("tracking") or st.get("officer_resolved") or st.get("closed_on"):
                    jstate[fkey] = st
                continue  # already shown as resolved, or finished before it was ever tracked
            st = jstate.setdefault(fkey, st)
            rec = {"name": fkey, "state": "", "key": fkey, "column": True, "flagged": False, "resolved": False,
                   "column_since": since_on, "column_detail": cyc["detail"], "column_stage": cyc.get("stage"),
                   "evidence": cyc["detail"]}
            if closed_on:
                how = ("resolved on your Items sheet" if st.get("officer_resolved")
                       else "marked not applicable" if cyc.get("not_applicable")
                       else f"closed in the {COLUMN_CYCLES[fkey]['label']}")
                rec.update(resolved=True, date_resolved=closed_on, evidence=f"{how} ({_ddmmyyyy(closed_on)})")
                st.update(resolved_shown=True, closed_on=closed_on)
                job_ev["changes"].append({"item": fkey, "action": "resolved", "evidence": rec["evidence"]})
                col_resolved.append(rec)
                continue
            st["tracking"] = True
            if snapshot:
                _, _, rec["owner"], rec["owner_field"], _ = check_item({"name": fkey}, snapshot, since)
            job_ev["changes"].append({"item": fkey, "action": "tracked-from-columns", "evidence": cyc["detail"]})
            col_out.append(rec)

        # ---- ageing (pilot rows only)
        submit_iso = row["submit_for_ba"]["date"]
        for item in items_out + resolved_out + col_out + col_resolved:
            entry = jstate.setdefault(item["key"], {})
            age_item(item, entry, snapshot, asof, since, submit_iso)
            item["officer_note"] = entry.get("officer_note")
            for f in item.get("age_flags", []):
                job_ev["flags"].append(f"item \"{item['name']}\": {f}")
        for item in resolved_out:
            jstate.pop(item["key"], None)
            if item["key"] in COLUMN_CYCLES and in_scope:
                # its columns may never show the close (OSC does not re-date a forward), so the
                # closed cycle is remembered and the item is not tracked again until a newer step
                cyc = cycles.get(item["key"])
                jstate[item["key"]] = {"cycle_since": cyc["since"] if cyc else None, "resolved_shown": True,
                                       "closed_on": item["date_resolved"]}
        if in_scope and g["date"] and not items_out:
            for k in [k for k in jstate if k not in COLUMN_CYCLES]:
                jstate.pop(k)  # the RFI list has closed; column items keep their history
        if in_scope and row["ba_received"]["date"]:
            for k in [k for k in jstate if k in COLUMN_CYCLES]:
                jstate.pop(k)  # building approval received: the column history is finished with
        if in_scope and not jstate:
            state.pop(job_no, None)

        # ---- OSC says the RFI response went back, yet items are still listed:
        # the officer decides whether the list should close (PO-13), so flag it.
        key = "submit_all_rfi_items"
        if snapshot and items_out:
            returned = [_iso_day(a["completionDate"]) for a in snapshot.get("activities", [])
                        if re.search(COLUMN_ACTIVITY[key], a.get("description") or "", re.I)
                        and a.get("completionDate")]
            if returned and max(returned) >= since:
                job_ev["flags"].append(
                    f"OSC activity \"Return RFI Information to Certifier\" completed {max(returned)} "
                    f"but {len(items_out)} item(s) still listed — review whether the PENDING list should close")

        # ---- the RFI-items cell (G on the old export, L since 28 Sep 2026)
        all_resolved_now = had_items and not items_out and resolved_out
        if items_out:
            text = "PENDING " + ", ".join(
                i["name"] + (f" ({i['state']})" if i["state"] else "")
                for i in items_out)
            if resolved_out:
                text += "\nRESOLVED " + ", ".join(
                    f"{i['name']} ({_ddmmyyyy(i['date_resolved'])})" for i in resolved_out)
            g_cell = (text, xlsx_min.S_RED)
        elif all_resolved_now:
            matched, complete, _ = activity_state(snapshot or {}, COLUMN_ACTIVITY[key])
            comp = [_iso_day(a["completionDate"]) for a in (snapshot or {}).get("activities", [])
                    if re.search(COLUMN_ACTIVITY[key], a.get("description") or "", re.I)
                    and a.get("completionDate")]
            if matched and complete and comp and max(comp) >= since:
                g_cell = (float(iso_to_serial(max(comp))), xlsx_min.S_DATE)
                job_ev["changes"].append({"column": key, "action": "filled", "value": max(comp),
                                          "evidence": "all items resolved; OSC Return RFI activity complete"})
            else:
                g_cell = ("RESOLVED " + ", ".join(f"{i['name']} ({_ddmmyyyy(i['date_resolved'])})"
                                                  for i in resolved_out), xlsx_min.S_FLAGGED)
                job_ev["flags"].append("all items resolved, but OSC shows no Return RFI date this week — the cell "
                                       "lists what resolved; type the date the response went back")
        else:
            g_cell = _date_or_text(values[key])

        # ---- row fill: the worst open item (PO-11a, row-level colour per #29)
        open_items = items_out + col_out
        ordered = items_out + col_out + resolved_out + col_resolved
        worst = ""
        for i in open_items:
            if i["flag"] == "RED":
                worst = "RED"
            elif i["flag"] == "YELLOW" and worst != "RED":
                worst = "YELLOW"
        row_fill = {"RED": xlsx_min.S_REDFILL, "YELLOW": xlsx_min.S_YELLOW}.get(worst, xlsx_min.S_WRAP)
        if row_fill == xlsx_min.S_WRAP and any(i.get("flagged") for i in ordered):
            row_fill = xlsx_min.S_FLAGGED

        # ---- main-sheet cells, in the base's column order
        cells = []
        for c in columns:
            k = c["key"]
            if k == "job_no":
                cells.append((job_no, row_fill))
            elif k in ("marketer", "address"):
                cells.append((row[k], xlsx_min.S_WRAP))
            elif k == "submit_all_rfi_items":
                cells.append(g_cell)
            elif k in values:
                cells.append(_date_or_text(values[k]))
            else:  # extra column: carried verbatim
                cells.append(_date_or_text(row["extra"].get(c["header"], {}).get("raw")))
        out_rows.append(cells)

        # ---- Items sheet: one row per item, coloured by its own flag; Notes are the officer's own
        now_names = {norm_item(i["name"]) for i in ordered}
        for i in ordered:
            if i.get("resolved"):
                fill, flag_text = xlsx_min.S_WRAP, "RESOLVED"
            else:
                fill = {"RED": xlsx_min.S_REDFILL, "YELLOW": xlsx_min.S_YELLOW}.get(i["flag"], xlsx_min.S_WRAP)
                flag_text = i["flag"]
            notes = []
            change = _since_last_week(i, _last_row(job_no, i["name"], last_rows, now_names), bool(last_rows))
            if change:
                notes.append(change)
            if i.get("column") and not i.get("resolved"):
                notes.append("tracked from its columns, not on the RFI list")
            if i.get("assumed"):
                notes.append("date submitted assumed — please correct")
            if i["flag"] == "NOT SUBMITTED":
                notes.append("not yet submitted (from your Items sheet) — type the date once it goes out")
            if i.get("flagged") and not i.get("resolved"):
                notes.append("verify")
            if i.get("evidence"):
                notes.append(str(i["evidence"]))
            if not i.get("resolved"):
                notes.append(f"limit {i['threshold']} business days" + _stage_words(i))
                other = _note_days(i.get("officer_note"), i["threshold"])
                if other:
                    days_said = ", ".join(str(n) for n in other)
                    notes.append(f"your note mentions {days_said} days but this row uses {i['threshold']}: "
                                 "tell us if the limit should change")
                    job_ev["flags"].append(f"item \"{i['name']}\": her note mentions {days_said} days, the limit "
                                           f"used is {i['threshold']} — check the rule with her")
            items_rows.append([
                (job_no, fill),
                (i["name"], fill),
                (("⚠ " if i.get("flagged") and not i.get("resolved") else "") + (i.get("assigned_to") or "?"), fill),
                (_ddmmyyyy(i.get("date_submitted")), fill),
                (_ddmmyyyy(i.get("date_resolved")) if i.get("resolved") else "", fill),
                (int(i["days"]) if i.get("days") is not None else "", fill),
                (flag_text, fill),
                (i.get("officer_note") or "", xlsx_min.S_WRAP),
                ("; ".join(notes), xlsx_min.S_FLAGGED if i.get("flagged") else xlsx_min.S_WRAP),
            ])
        job_ev["outstanding"] = items_out + col_out
        job_ev["resolved"] = resolved_out + col_resolved
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
    width_by_key = {"job_no": 9, "marketer": 16, "address": 34, "submit_all_rfi_items": 44}
    widths = {}
    for n, c in enumerate(columns, 1):
        widths[xlsx_min._col_letter(n)] = width_by_key.get(c["key"], 12)
    items_widths = {"A": 9, "B": 34, "C": 22, "D": 14, "E": 13, "F": 10, "G": 14, "H": 40, "I": 48}
    xlsx_min.write_workbook(draft_path, [
        (prev.get("sheet_name") or "Sheet 1", out_rows, widths),
        (ITEMS_SHEET, items_rows, items_widths, 1),
    ])

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
             ", ".join(f"{k} {v}" for k, v in TIERS.items()) + "; whoever has them, " + _limits_text() + ".",
             "Engineering and covenant are also tracked from their columns when not on the RFI list.",
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
                f"- outstanding{' (from its columns)' if i.get('column') else ''}: {i['name']} — "
                f"with {i.get('assigned_to') or '?'} "
                f"[{i.get('tier')} ≤{i.get('threshold')}] — submitted {i.get('date_submitted')} "
                f"({i.get('date_source')}) — "
                f"{'not counted' if i.get('days') is None else str(i['days']) + ' business days'} {i.get('flag')}{mark} "
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
    ap.add_argument("--edited", help="last week's draft as the officer left it (her Items-sheet changes)")
    ap.add_argument("--drafted", help="that draft as written (default: the same file name in --out)")
    args = ap.parse_args(argv)
    jobs = [j for j in (args.jobs or "").split(",") if j.strip()] or None
    try:
        draft, ev_md, evidence = build_draft(
            args.prev, args.snapshots, args.out,
            asof=args.asof, state_dir=args.state, jobs=jobs, edited=args.edited, drafted=args.drafted)
    except (StateError, DraftInputError) as exc:
        print(f"stopped: {exc}", file=sys.stderr)
        return 2
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
