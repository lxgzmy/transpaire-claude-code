"""The layout-pass watchdog in draft_contract.py, with stand-in scripts instead of Word.

    python test_layout_watchdog.py

- a pass that keeps printing finishes normally, however long it runs;
- a pass that goes silent is stopped and run once more, then reported failed;
- the process ID a pass reports is stopped only when it is Word: a stand-in "Word"
  that is really another process survives.
Exit 0 = pass. Writes only to runtime\\contract-admin\\state\\_watchdog-selftest.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import draft_contract as dc  # noqa: E402

WORK = HERE.parents[2] / "runtime" / "contract-admin" / "state" / "_watchdog-selftest"
SCRIPTS = {
    "ok.ps1": 'Write-Host "word pid 0"; Write-Host "done"',
    "ticks.ps1": 'Write-Host "word pid 0"; 1..5 | ForEach-Object { Start-Sleep -Milliseconds 900; Write-Host "step $_" }',
    "hang.ps1": 'param([int]$Pid2) Write-Host "word pid $Pid2"; Start-Sleep -Seconds 600',
}


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    for name, body in SCRIPTS.items():
        (WORK / name).write_text(body, encoding="utf-8")
    fails = []

    r = dc.run_layout(script=WORK / "ok.ps1", silence=3)
    if r.returncode != 0 or "done" not in r.stdout:
        fails.append(f"ok: {r.returncode} {r.stdout!r}")

    t = time.monotonic()
    r = dc.run_layout(script=WORK / "ticks.ps1", silence=3)
    if r.returncode != 0 or "step 5" not in r.stdout or time.monotonic() - t < 4:
        fails.append(f"ticks: a pass that keeps printing was stopped ({r.returncode} {r.stdout!r})")

    bystander = subprocess.Popen(["ping", "-n", "60", "127.0.0.1"], stdout=subprocess.DEVNULL)
    t = time.monotonic()
    r = dc.run_layout(bystander.pid, script=WORK / "hang.ps1", silence=3)
    took = time.monotonic() - t
    if r.returncode == 0 or "both tries" not in r.stderr:
        fails.append(f"hang: not reported failed ({r.returncode} {r.stderr!r})")
    if took > 30:
        fails.append(f"hang: took {took:.0f}s - the watchdog did not stop it")
    if bystander.poll() is not None:
        fails.append("hang: a process that is not Word was stopped")
    bystander.kill()

    for f in fails:
        print("FAIL", f)
    print("PASS: layout watchdog" if not fails else f"FAIL - {len(fails)} problem(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
