"""Read-only check of the configured DocuSign connection. No envelope is touched.

    python -m docusign_upload.selftest

Prints the redacted config, signs in with JWT, names the account and user, and
lists the templates whose name contains "Build _". It never prints the key, the
token or a path. Exit codes: 0 ok, 2 config, 3 sign-in, 4 DocuSign error.
"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

from .auth import AuthError
from .client import DocuSignClient, DocuSignError
from .config import ConfigError, load_config


async def _run() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2
    print("Config:", json.dumps(config.redacted(), indent=2))
    client = DocuSignClient(config)
    try:
        session = await client.auth.session()
        print(f"Signed in ({config.label}): account {session.account_name!r}, user {session.user_name!r}")
        names = sorted(str(t.get("name", "")).strip() for t in await client.list_templates("Build _"))
        print(f"Templates matching 'Build _': {len(names)}")
        for name in names:
            print(f"  {name}")
        return 0
    except AuthError as exc:
        print(f"SIGN-IN ERROR: {exc}", file=sys.stderr)
        if exc.consent_url:
            print(f"Consent URL: {exc.consent_url}", file=sys.stderr)
        return 3
    except DocuSignError as exc:
        print(f"DOCUSIGN ERROR {exc.status}: {exc.error_code} {exc.detail}", file=sys.stderr)
        return 4
    except httpx.HTTPError as exc:
        print(f"NETWORK ERROR: {type(exc).__name__}", file=sys.stderr)
        return 4
    finally:
        await client.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
