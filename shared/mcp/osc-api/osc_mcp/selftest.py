"""Host-free smoke test: exercises the OSC client with the configured env vars.

Run:  python -m osc_mcp.selftest
It prints granted scope and a one-record sample from a couple of read endpoints.
No secret is printed. It performs read-only GETs only.
"""
from __future__ import annotations

import asyncio
import json
import sys

from .client import OSCClient
from .config import ConfigError, load_config


async def _run() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    print("Config:", json.dumps(config.redacted(), indent=2))
    client = OSCClient(config)
    try:
        info = await client.token_info()
        print("Token OK. Granted scope:", info.get("grantedScope"),
              "| expiresIn:", info.get("expiresIn"))

        for path, params in (("/api/versions", None), ("/api/Clients", {"$top": 1})):
            res = await client.request("GET", path, params=params)
            data = res.get("data")
            if isinstance(data, dict) and "value" in data:
                n = len(data["value"])
                sample = json.dumps(data["value"][0], default=str)[:200] if n else "(empty)"
                print(f"GET {path} -> {res['status']} | {n} record(s) | {sample}")
            else:
                print(f"GET {path} -> {res['status']} | {json.dumps(data, default=str)[:200]}")
        return 0
    finally:
        await client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
