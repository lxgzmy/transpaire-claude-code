"""Configuration for the OSC API MCP server.

Everything is read from environment variables so the same code points at dev or
production by changing the environment only - never the code. No secret is ever
written to disk by this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a .env file into os.environ, if present.

    Dependency-free. A variable already set in the real environment is NOT
    overridden, so production values passed via `claude mcp add --env` always
    win over a local .env used for dev/testing.

    Location: OSC_ENV_FILE if set, otherwise a `.env` beside this package
    (shared/mcp/osc-api/.env).
    """
    env_path = os.environ.get("OSC_ENV_FILE")
    path = Path(env_path) if env_path else Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class Config:
    base_url: str
    client_id: str
    client_secret: str
    swagger_url: str | None
    scopes: str | None
    verify_tls: bool
    enable_writes: bool
    timeout: float

    @property
    def token_url(self) -> str:
        return self.base_url.rstrip("/") + "/api/Token"

    def api_url(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def redacted(self) -> dict[str, object]:
        """A safe-to-log view: the secret is never included."""
        return {
            "base_url": self.base_url,
            "client_id": self.client_id[:8] + "..." if self.client_id else "",
            "swagger_url": self.swagger_url,
            "scopes": self.scopes,
            "verify_tls": self.verify_tls,
            "enable_writes": self.enable_writes,
            "timeout": self.timeout,
        }


def load_config() -> Config:
    """Build Config from OSC_* environment variables.

    Required: OSC_BASE_URL, OSC_CLIENT_ID, OSC_CLIENT_SECRET.
    Optional: OSC_SWAGGER_URL, OSC_SCOPES, OSC_VERIFY_TLS (default false),
    OSC_ENABLE_WRITES (default false), OSC_TIMEOUT (default 30).

    A local .env (see _load_dotenv) is loaded first, but never overrides a
    variable already set in the real environment.
    """
    _load_dotenv()
    base_url = os.environ.get("OSC_BASE_URL", "").strip()
    client_id = os.environ.get("OSC_CLIENT_ID", "").strip()
    client_secret = os.environ.get("OSC_CLIENT_SECRET", "").strip()

    missing = [
        name
        for name, val in (
            ("OSC_BASE_URL", base_url),
            ("OSC_CLIENT_ID", client_id),
            ("OSC_CLIENT_SECRET", client_secret),
        )
        if not val
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Set them in the MCP server's env (see .env.example)."
        )

    swagger_url = os.environ.get("OSC_SWAGGER_URL", "").strip() or None
    scopes = os.environ.get("OSC_SCOPES", "").strip() or None

    return Config(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        swagger_url=swagger_url,
        scopes=scopes,
        verify_tls=_as_bool(os.environ.get("OSC_VERIFY_TLS"), default=False),
        enable_writes=_as_bool(os.environ.get("OSC_ENABLE_WRITES"), default=False),
        timeout=float(os.environ.get("OSC_TIMEOUT", "30")),
    )
