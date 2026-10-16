"""Read-only check of the production OSC connection. Sends no write of any kind.

Run:  python -m osc_mcp.selftest [contract number]
Prints the environment, the granted scope, the live-data check (newest job in
OSC) and the lookups the contract intake depends on. With a contract number it
also reads that job and prints its number, status and custom-field count. No
secret or host name is printed.
"""
from __future__ import annotations

import asyncio
import json
import sys

from .client import OSCClient
from .config import ConfigError, load_config
from .gate import Gate, GateError, job_label


async def _run(contract: str | None) -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    print("Config:", json.dumps(config.redacted(), indent=2))
    client = OSCClient(config)
    gate = Gate(client, config)
    try:
        info = await client.token_info()
        print("Token OK. Granted scope:", info.get("grantedScope"), "| expiresIn:", info.get("expiresIn"))
        live = await gate.live_check(force=True)
        print("Live check:", json.dumps(live))
        for name in ("regions", "templates", "job_fields", "methods", "groups", "answers"):
            try:
                table = await gate._lookup(name, required=True)
                print(f"Lookup {name}: {len(table)} entries")
            except GateError as exc:
                print(f"Lookup {name}: FAILED - {exc}")
        if contract:
            res = await client.request("GET", "/api/Jobs", params={"$filter": f"contractNumber eq '{contract}'",
                                                                   "$top": 2},
                                       json_body={"shouldShowMyJobsOnly": False})
            rows = (res.get("data") or {}).get("value") or []
            print(f"Job {contract}: {len(rows)} match(es) (HTTP {res.get('status')})")
            for row in rows:
                print("  ", job_label(row), "|", row.get("workflowStatusName"), "|",
                      len(row.get("customFieldValues") or []), "custom fields")
        return 0 if live.get("live") else 1
    finally:
        await client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(_run(sys.argv[1] if len(sys.argv) > 1 else None)))


if __name__ == "__main__":
    main()
