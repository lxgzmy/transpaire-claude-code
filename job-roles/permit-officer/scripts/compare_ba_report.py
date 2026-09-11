#!/usr/bin/env python3
"""Score an AI BA-report draft against the officer's real report (pilot metric).

Reads both workbooks with ba_report_parse, restricts to the pilot jobs, and
compares per job: outstanding items (matched by item family, so "ENG" and
"ENGINEERING" agree), the date columns D-K, and Assigned-to where both sides
carry column L. Writes a Markdown scorecard with the headline "% of the
officer's outstanding items the draft pre-populated" against the pilot's
90 per cent criterion. Review time and "zero unapproved writes" are recorded
by hand in the same file (blank lines provided).

Usage:
  python compare_ba_report.py --draft "…\\BA REPORT DRAFT - 07.09.2026.xlsx"
                              --actual "…\\BA REPORT - 07.09.2026.xlsx"
                              --jobs 26029,26052,26001
                              [--out runtime\\permit-officer\\reports\\compare-07.09.2026.md]

Read-only on both inputs; the scorecard goes to the runtime folder only.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ba_report_draft import item_key
from ba_report_parse import DATE_KEYS, parse_report

DATE_LABELS = {
    "submit_for_ba": "Submit for BA", "received_rfi": "Received RFI",
    "received_covenant": "Received Covenant Approval", "submit_all_rfi_items": "Submit all RFI Items",
    "ba_received": "BA Received", "deposit_paid": "Deposit Paid",
    "nominate_site_start": "Nominate Site Start", "site_start_physical": "Site Start (Physical)",
}


def _items(row):
    g = row["submit_all_rfi_items"]
    return {item_key(i["name"]): i for i in g["items"]} if g["pending"] else {}


def _cell(row, key):
    v = row[key]
    return v["date"] or (str(v["raw"]).strip() if v["raw"] not in (None, "") else "")


def compare(draft_path, actual_path, jobs):
    draft = {str(r["job_no"]): r for r in parse_report(draft_path)["rows"]}
    actual = {str(r["job_no"]): r for r in parse_report(actual_path)["rows"]}
    report = {"jobs": [], "officer_items": 0, "matched": 0, "missed": 0, "extra": 0,
              "date_cells": 0, "date_agree": 0, "assignee_pairs": 0, "assignee_agree": 0}
    for job in jobs:
        d, a = draft.get(job), actual.get(job)
        j = {"job_no": job, "in_draft": d is not None, "in_actual": a is not None}
        if d is None or a is None:
            report["jobs"].append(j)
            continue
        di, ai = _items(d), _items(a)
        j["matched"] = sorted(set(di) & set(ai))
        j["missed"] = sorted(set(ai) - set(di))     # officer has it, draft did not
        j["extra"] = sorted(set(di) - set(ai))      # draft has it, officer dropped/never had it
        report["officer_items"] += len(ai)
        report["matched"] += len(j["matched"])
        report["missed"] += len(j["missed"])
        report["extra"] += len(j["extra"])
        j["dates"] = []
        for key in DATE_KEYS:
            if key == "submit_all_rfi_items":
                continue
            dv, av = _cell(d, key), _cell(a, key)
            if not dv and not av:
                continue
            report["date_cells"] += 1
            agree = dv == av
            report["date_agree"] += int(agree)
            if not agree:
                j["dates"].append((DATE_LABELS[key], dv or "—", av or "—"))
        j["assignees"] = []
        for k in j["matched"]:
            da, aa = di[k].get("assigned_to"), ai[k].get("assigned_to")
            if da and aa:
                report["assignee_pairs"] += 1
                agree = re.sub(r"\W", "", da).lower() == re.sub(r"\W", "", aa).lower()
                report["assignee_agree"] += int(agree)
                if not agree:
                    j["assignees"].append((di[k]["name"], da, aa))
        report["jobs"].append(j)
    return report


def render(report, draft_path, actual_path, jobs):
    pct = (100.0 * report["matched"] / report["officer_items"]) if report["officer_items"] else None
    lines = [f"# BA report pilot scorecard — {date.today().strftime('%d.%m.%Y')}", "",
             f"Draft: `{draft_path}`  ", f"Actual: `{actual_path}`  ",
             f"Pilot jobs: {', '.join(jobs)}", "",
             "## Headline", "",
             f"- Officer's outstanding items across pilot jobs: {report['officer_items']}",
             f"- Pre-populated by the draft (matched): {report['matched']}",
             f"- Missed by the draft: {report['missed']}",
             f"- Extra in the draft (officer did not list): {report['extra']}",
             (f"- **{pct:.0f} % correctly pre-populated** (criterion: at least 90 %)" if pct is not None
              else "- **no officer items to score** (all pilot jobs complete or absent)"),
             f"- Date cells agreeing: {report['date_agree']} of {report['date_cells']}",
             f"- Assigned-to agreeing: {report['assignee_agree']} of {report['assignee_pairs']} "
             "(scored only where both sides filled column L)",
             "", "## Recorded by hand", "",
             "- Officer review time (target under 30 minutes): ____ minutes",
             "- Unapproved writes to OSC / mailbox / Z: business folders (must be zero): ____",
             "- Officer comments:", "", ""]
    for j in report["jobs"]:
        lines.append(f"## Job {j['job_no']}")
        if not j["in_draft"] or not j["in_actual"]:
            where = "draft" if not j["in_draft"] else "officer's report"
            lines += [f"- not a row in the {where} — unscored", ""]
            continue
        lines.append(f"- matched: {', '.join(j['matched']) or 'none'}")
        lines.append(f"- missed: {', '.join(j['missed']) or 'none'}")
        lines.append(f"- extra: {', '.join(j['extra']) or 'none'}")
        for label, dv, av in j["dates"]:
            lines.append(f"- date differs — {label}: draft {dv}, officer {av}")
        for name, da, aa in j["assignees"]:
            lines.append(f"- assigned-to differs — {name}: draft \"{da}\", officer \"{aa}\"")
        lines.append("")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--actual", required=True)
    ap.add_argument("--jobs", required=True, help="comma-separated pilot job numbers")
    ap.add_argument("--out", help="scorecard .md path (default: next to the actual report)")
    args = ap.parse_args(argv)
    jobs = [j.strip() for j in args.jobs.split(",") if j.strip()]
    report = compare(args.draft, args.actual, jobs)
    text = render(report, args.draft, args.actual, jobs)
    out = Path(args.out) if args.out else Path(args.actual).with_name(
        "compare-" + re.sub(r"^.*?(\d{2}\.\d{2}\.\d{4}).*$", r"\1", Path(args.actual).stem) + ".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.split("## Recorded by hand")[0])
    print(f"scorecard: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
