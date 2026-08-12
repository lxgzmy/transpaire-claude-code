"""The job-location logic is OWNED by the org z-drive-ops skill; keep copies in step.

    python test_job_search.py

The Z: drive is the knowledge base. The canonical "where can a job folder be"
logic lives in the org-level skill (.claude/skills/z-drive-ops/scripts/
find_job.ps1); probe_job.py re-implements it in Python so the contract workflow
gets paths it can keep processing without a pwsh round-trip. Two copies of one
piece of knowledge drift: probe_job.py missed SYDNEY\\HANDED OVER (199 jobs)
until 12 Aug 2026 precisely because nothing held them together.

Three checks, all read-only:

  1. find_job.ps1 and probe_job.py descend the SAME lifecycle folder set.
  2. Every lifecycle-like folder on the live drive is in that set - a new
     variant name (e.g. an "ARCHIVED" someone creates next year) fails here
     before it silently hides jobs.
  3. A job known to live in each lifecycle location is actually found.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIND_PS1 = REPO / ".claude" / "skills" / "z-drive-ops" / "scripts" / "find_job.ps1"
PROJECTS = Path(r"Z:\PROJECTS")

sys.path.insert(0, str(HERE))
import probe_job  # noqa: E402


def ps1_lifecycle():
    m = re.search(r"^\$lifecycle\s*=\s*(.+)$", FIND_PS1.read_text(encoding="utf-8"), re.M)
    return set(re.findall(r"'([^']+)'", m.group(1)))


def py_lifecycle():
    src = (HERE / "probe_job.py").read_text(encoding="utf-8")
    m = re.search(r"path\.name in \(([^)]+)\)", src, re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def drive_lifecycle_names():
    """Region-level folders that look lifecycle-shaped, straight off the drive."""
    names = set()
    for top in PROJECTS.iterdir():
        if not top.is_dir():
            continue
        for sub in top.iterdir():
            if (sub.is_dir() and not re.match(r"^\d{5}", sub.name)
                    and re.search(r"HANDED|CANCEL|COMPLETE", sub.name, re.I)):
                names.add(sub.name)
    return names


def main():
    failures = []

    ps1, py = ps1_lifecycle(), py_lifecycle()
    if ps1 != py:
        failures.append(f"script drift: find_job.ps1 {sorted(ps1)} != probe_job.py {sorted(py)}")
    else:
        print(f"OK  scripts agree on lifecycle set: {sorted(ps1)}")

    live = drive_lifecycle_names()
    unknown = live - ps1
    if unknown:
        failures.append(f"drive has lifecycle folder(s) the scripts do not search: {sorted(unknown)}")
    else:
        print(f"OK  every lifecycle folder on the drive is searched: {sorted(live)}")

    # one real job per lifecycle location must be findable by its number
    for rel in ["SYDNEY/HANDED OVER", "SEQ/ARCHIVE-HANDED OVER", "SYDNEY/CANCELLED",
                "COMPLETED CONTRACTS", "CANCELLED CONTRACTS"]:
        d = PROJECTS / rel
        job = next((p for p in d.iterdir()
                    if p.is_dir() and re.match(r"^\d{5}", p.name)), None)
        if job is None:
            print(f"--  {rel}: no numbered job folder to test with (skipped)")
            continue
        number = job.name[:5]
        hits = probe_job.find_jobs(number)
        if any(h[1] == job for h in hits):
            print(f"OK  {rel}: job {number} found")
        else:
            failures.append(f"{rel}: job {number} exists but find_jobs() missed it")

    print()
    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        return 1
    print("PASS")
    return 0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
