#!/usr/bin/env python3
"""Snapshot the pilot jobs from the production OnSite Companion (read-only).

The weekly BA report draft (``ba_report_draft.py``) works from one JSON per
job. This script writes those files with the same queries the role's field
map documents (``reference/osc-field-map.md``), through the ``osc_mcp``
client package the ``osc-api-prod`` MCP server itself uses — same
credentials (``production.env`` beside that package, never in git), same
host, GET requests only. Nothing here can write: the only method this
script ever sends is GET.

It must run under the MCP server's virtual environment, which has ``httpx``
(the repo's Python has no third-party packages):

  "shared\\mcp\\osc-api\\.venv\\Scripts\\python.exe" job-roles\\permit-officer\\scripts\\osc_snapshot.py
        --jobs 26029,26052,26001
        --out runtime\\permit-officer\\state\\snapshots

Before saving anything it checks the connection is the live system (the
newest job in OSC is recent), because a frozen copy once produced a week of
stale drafts. Every snapshot is live client data: it goes to the git-ignored
runtime folder only, and this script prints job numbers, counts and dates —
never names, addresses or document titles.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "shared" / "mcp" / "osc-api"))

try:
    from osc_mcp.client import OSCClient  # noqa: E402
    from osc_mcp.config import load_config  # noqa: E402
except ImportError as exc:  # pragma: no cover - environment guard
    sys.exit(f"cannot import the OSC client ({exc}); run this under "
             "shared\\mcp\\osc-api\\.venv\\Scripts\\python.exe")

JOB_SELECT = "jobID,contractNumber,clientName,siteAddress,workflowStatusName"
ACTIVITY_SELECT = ("jobActivityID,sequence,description,completionDate,completionDateLastUpdatedOnUtc,"
                   "isNotApplicable,serviceProvider,user,hasAlerts")
ALERT_SELECT = "alertID,subject,createdBy,createdOnUtc"
DOCUMENT_SELECT = "documentID,description,extension,version,attachedOnUtc,documentTypeID"


class SnapshotError(RuntimeError):
    pass


async def _get(client, path, query, body=None, what=""):
    """GET only. Raises on a non-2xx answer so a half snapshot is never saved."""
    result = await client.request("GET", path, params=query, json_body=body)
    if not result.get("ok"):
        raise SnapshotError(f"{what or path}: HTTP {result.get('status')} {result.get('error') or ''}".strip())
    data = result.get("data")
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    return data


async def live_check(client, stale_after_days):
    rows = await _get(client, "/api/Jobs",
                      {"$orderby": "createdOnUtc desc", "$top": 1, "$select": "contractNumber,createdOnUtc"},
                      {"shouldShowMyJobsOnly": False}, "newest job")
    created = rows[0].get("createdOnUtc") if rows else None
    if not created:
        raise SnapshotError("OnSite Companion returned no job to date-check; not saving.")
    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - dt).days
    if age > stale_after_days:
        raise SnapshotError(f"newest job in OSC was created {age} days ago — this looks like a frozen copy; "
                            "not saving.")
    return {"newest_job_created": dt.date().isoformat(), "age_days": age}


async def snapshot_job(client, jobno):
    jobs = await _get(client, "/api/Jobs",
                      {"$filter": f"contractNumber eq '{jobno}'", "$top": 2, "$select": JOB_SELECT},
                      {}, f"job {jobno}")
    if not jobs:
        return None
    if len(jobs) > 1:
        raise SnapshotError(f"job {jobno}: contract number matches {len(jobs)} jobs; not saving.")
    job = jobs[0]
    job_id = job["jobID"]
    activities = await _get(client, "/api/JobActivities",
                            {"$filter": f"jobID eq {job_id}", "$orderby": "sequence", "$top": 300,
                             "$select": ACTIVITY_SELECT}, None, f"job {jobno} activities")
    alerts = await _get(client, "/api/Jobs/Alerts",
                        {"$filter": f"jobID eq {job_id}", "$orderby": "createdOnUtc desc", "$top": 200,
                         "$select": ALERT_SELECT}, {}, f"job {jobno} alerts")
    documents = await _get(client, "/api/Jobs/Documents",
                           {"$filter": f"jobID eq {job_id}", "$orderby": "attachedOnUtc desc", "$top": 500,
                            "$select": DOCUMENT_SELECT}, {}, f"job {jobno} documents")
    site = job.get("siteAddress") or {}
    return {
        "retrievedAtUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contractNumber": str(job.get("contractNumber") or jobno),
        "jobID": job_id,
        "clientName": job.get("clientName"),
        "state": site.get("state"),
        "workflowStatusName": job.get("workflowStatusName"),
        "activities": activities,
        "alerts": alerts,
        "documents": documents,
    }


async def run(jobs, out_dir):
    config = load_config()
    client = OSCClient(config)
    try:
        live = await live_check(client, config.stale_after_days)
        print(f"source: {config.environment} (target {config.target_fingerprint()}), "
              f"newest job created {live['newest_job_created']} ({live['age_days']} days ago)")
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        missing = []
        for jobno in jobs:
            snap = await snapshot_job(client, jobno)
            if snap is None:
                missing.append(jobno)
                print(f"{jobno}: not found in OSC — no snapshot written")
                continue
            snap["source"] = {"environment": config.environment, "target": config.target_fingerprint(),
                              "newest_job_created": live["newest_job_created"]}
            path = out_dir / f"{jobno}.json"
            path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            done = sum(1 for a in snap["activities"] if a.get("completionDate"))
            print(f"{jobno}: {snap['state']} {snap['workflowStatusName']} — "
                  f"{len(snap['activities'])} activities ({done} complete), {len(snap['alerts'])} alerts, "
                  f"{len(snap['documents'])} documents -> {path}")
        return missing
    finally:
        await client.aclose()


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", required=True, help="comma-separated contract numbers")
    ap.add_argument("--out", required=True, help="snapshot folder (runtime only)")
    args = ap.parse_args(argv)
    jobs = [j.strip() for j in args.jobs.split(",") if j.strip()]
    out = Path(args.out)
    if "runtime" not in {p.lower() for p in out.resolve().parts}:
        sys.exit("--out must be under a runtime\\ folder (live client data never goes anywhere else)")
    try:
        missing = asyncio.run(run(jobs, out))
    except SnapshotError as exc:
        sys.exit(f"stopped: {exc}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
