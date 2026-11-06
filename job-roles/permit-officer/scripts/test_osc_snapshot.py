#!/usr/bin/env python3
"""Retries and side-by-side reads in osc_snapshot.py, on a fake OSC client (no network, no OSC).

It needs httpx, so it runs under the osc-api virtual environment; regress_ba_report.py runs it
there when that environment exists:

  "shared\\mcp\\osc-api\\.venv\\Scripts\\python.exe" job-roles\\permit-officer\\scripts\\test_osc_snapshot.py
"""
import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx  # noqa: E402
import osc_snapshot as snap  # noqa: E402


class FakeClient:
    """Answers GETs from a script of answers (an exception is raised); counts calls and overlap."""

    def __init__(self, answers=()):
        self.answers, self.calls, self.in_flight, self.most = list(answers), 0, 0, 0

    async def request(self, method, path, params=None, json_body=None):
        assert method == "GET", method
        self.calls += 1
        self.in_flight += 1
        self.most = max(self.most, self.in_flight)
        await asyncio.sleep(0.02)
        self.in_flight -= 1
        answer = self.answer(path, params)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def answer(self, path, params):
        return self.answers.pop(0) if self.answers else {"ok": True, "data": {"value": []}}


class ByPath(FakeClient):
    """One job per contract number; empty lists for its activities, alerts and documents."""

    def answer(self, path, params):
        if path == "/api/Jobs":
            n = params["$filter"].split("'")[1]
            return {"ok": True, "data": {"value": [{"jobID": f"guid-{n}", "contractNumber": n,
                                                    "siteAddress": {"state": "NSW"}}]}}
        return {"ok": True, "data": {"value": []}}


def run(coro_fn):
    async def go():
        snap._slots = asyncio.Semaphore(snap.PARALLEL)
        return await coro_fn()
    return asyncio.run(go())


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.waits, snap.RETRY_WAITS = snap.RETRY_WAITS, (0, 0)

    def tearDown(self):
        snap.RETRY_WAITS = self.waits

    def test_a_passing_fault_is_tried_again(self):
        c = FakeClient([httpx.ReadTimeout("slow"), {"ok": False, "status": 503}, {"ok": True, "data": {"value": [1]}}])
        self.assertEqual(run(lambda: snap._get(c, "/api/x", {})), [1])
        self.assertEqual(c.calls, 3)

    def test_a_real_error_stops_at_once(self):
        c = FakeClient([{"ok": False, "status": 400, "error": "Bad request"}])
        with self.assertRaises(snap.SnapshotError):
            run(lambda: snap._get(c, "/api/x", {}))
        self.assertEqual(c.calls, 1)

    def test_it_gives_up_after_three_tries(self):
        c = FakeClient([httpx.ConnectError("down")] * 3)
        with self.assertRaisesRegex(snap.SnapshotError, "after 3 tries"):
            run(lambda: snap._get(c, "/api/x", {}))
        self.assertEqual(c.calls, 3)

    def test_jobs_are_read_side_by_side_within_the_limit_and_kept_in_order(self):
        c, jobs = ByPath(), ["90001", "90002", "90003"]
        got = run(lambda: asyncio.gather(*(snap.snapshot_job(c, j) for j in jobs)))
        self.assertEqual([s["contractNumber"] for s in got], jobs)
        self.assertEqual(c.calls, 12)
        self.assertTrue(1 < c.most <= snap.PARALLEL, c.most)


if __name__ == "__main__":
    unittest.main(verbosity=1)
