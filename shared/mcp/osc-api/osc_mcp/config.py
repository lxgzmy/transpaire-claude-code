"""Configuration for the OSC API MCP server.

Everything is read from environment variables, so no host or secret is ever in
the code. The server talks to the production OnSite Companion only (owner
approval, 13 Oct 2026). The dev copy it used before was a frozen 21 Aug 2026
snapshot that staff never see, so it is no longer a supported target. No
secret is ever written to disk by this module.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

# The only environment this server will start against. The name is also the
# env file's name (production.env beside the package) and is shown to staff in
# every confirmation, so it must say what it is.
ENVIRONMENTS = ("production",)

PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # shared/mcp/osc-api


def env_file_path(environment: str) -> Path:
    """OSC_ENV_FILE if set, otherwise <environment>.env beside the package.

    The old dev settings lived in `.env`; that file is never read any more, so a
    leftover copy on a checkout cannot point this server at the dev copy.
    """
    explicit = os.environ.get("OSC_ENV_FILE")
    return Path(explicit) if explicit else PACKAGE_ROOT / f"{environment}.env"


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from an env file into os.environ, if present.

    Dependency-free. A variable already set in the real environment is NOT
    overridden, so values passed in the MCP server's `env` block (.mcp.json)
    always win over the file.
    """
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
            _FROM_DOTENV.add(key)


# Keys that load_config took from the env file rather than the real
# environment. Lets osc_token_info say WHERE a setting came from - the write
# switch in particular, which a person otherwise chases through three files.
_FROM_DOTENV: set[str] = set()


def setting_source(key: str) -> str:
    """'env' (MCP server env / real environment), 'dotenv' (env file) or 'default' (unset)."""
    if key in _FROM_DOTENV:
        return "dotenv"
    if key in os.environ:
        return "env"
    return "default"


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
    # Directories a multipart upload may read from. Empty means "no uploads at
    # all"; load_config always fills it (OSC_UPLOAD_ROOTS or the checkout's
    # git-ignored runtime\ folder).
    upload_roots: tuple[str, ...] = ()
    # Where the write switch came from: "env" (the MCP server's env block in
    # .mcp.json, or a real environment variable), "dotenv" (the env file) or
    # "default" (unset -> false). Reported by osc_token_info.
    enable_writes_source: str = "default"
    environment: str = "production"
    # Writes are refused when the newest job in OSC is older than this many
    # days: the sign of a frozen copy rather than the system staff use.
    stale_after_days: int = 30
    # A confirmation code stays valid this many minutes.
    approval_minutes: int = 30

    @property
    def token_url(self) -> str:
        return self.base_url.rstrip("/") + "/api/Token"

    def api_url(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def target_fingerprint(self) -> str:
        """Short hash of the base URL: compares two setups without naming the host."""
        return hashlib.sha256(self.base_url.strip().lower().encode()).hexdigest()[:8]

    def redacted(self) -> dict[str, object]:
        """A safe-to-log view: no secret and no host name."""
        return {
            "environment": self.environment,
            "target": self.target_fingerprint(),
            "client_id": self.client_id[:8] + "..." if self.client_id else "",
            "spec_configured": bool(self.swagger_url),
            "scopes": self.scopes,
            "verify_tls": self.verify_tls,
            "enable_writes": self.enable_writes,
            "enable_writes_source": self.enable_writes_source,
            "timeout": self.timeout,
            "stale_after_days": self.stale_after_days,
            # count only: a root spelled as a UNC path would name the file server
            "upload_roots": len(self.upload_roots),
        }


def default_upload_root() -> str:
    """The checkout's runtime\\ folder: shared/mcp/osc-api/osc_mcp -> <repo>/runtime.

    abspath, not resolve(): on this server resolve() rewrites a mapped drive
    into its UNC form, and the caller's path would then never compare equal.
    """
    here = os.path.dirname(os.path.abspath(__file__))  # .../shared/mcp/osc-api/osc_mcp
    return os.path.normpath(os.path.join(here, *([os.pardir] * 4), "runtime"))


def load_config() -> Config:
    """Build Config from OSC_* environment variables.

    OSC_ENVIRONMENT names the target (default and only value: production) and
    the env file read for it (production.env beside the package, or
    OSC_ENV_FILE). That file is loaded first but never overrides a variable
    already set in the real environment.

    Required: OSC_BASE_URL, OSC_CLIENT_ID, OSC_CLIENT_SECRET.
    Optional: OSC_SWAGGER_URL, OSC_SCOPES, OSC_VERIFY_TLS (default true),
    OSC_ENABLE_WRITES (default false), OSC_TIMEOUT (default 30),
    OSC_UPLOAD_ROOTS (semicolon-separated absolute directories a multipart
    upload may read from; default: the checkout's runtime\\ folder),
    OSC_STALE_AFTER_DAYS (default 30), OSC_APPROVAL_MINUTES (default 30).
    """
    environment = os.environ.get("OSC_ENVIRONMENT", "production").strip().lower() or "production"
    if environment not in ENVIRONMENTS:
        raise ConfigError(
            f"OSC_ENVIRONMENT={environment!r} is not supported. This server connects to the "
            "production OnSite Companion only; the dev copy was retired on 13 Oct 2026."
        )
    path = env_file_path(environment)
    _load_dotenv(path)
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
            "Missing required setting(s): " + ", ".join(missing) + f". They belong in "
            f"{path.name} beside the osc-api package (template: production.env.example), "
            "filled from the company password store."
        )

    swagger_url = os.environ.get("OSC_SWAGGER_URL", "").strip() or None
    scopes = os.environ.get("OSC_SCOPES", "").strip() or None
    roots_raw = os.environ.get("OSC_UPLOAD_ROOTS", "")
    upload_roots = tuple(r.strip() for r in roots_raw.split(";") if r.strip()) or (default_upload_root(),)
    for root in upload_roots:
        if not os.path.isabs(root):
            raise ConfigError(f"OSC_UPLOAD_ROOTS entries must be absolute directories: {root!r}")

    return Config(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        swagger_url=swagger_url,
        scopes=scopes,
        verify_tls=_as_bool(os.environ.get("OSC_VERIFY_TLS"), default=True),
        enable_writes=_as_bool(os.environ.get("OSC_ENABLE_WRITES"), default=False),
        timeout=float(os.environ.get("OSC_TIMEOUT", "30")),
        upload_roots=upload_roots,
        enable_writes_source=setting_source("OSC_ENABLE_WRITES"),
        environment=environment,
        stale_after_days=int(os.environ.get("OSC_STALE_AFTER_DAYS", "30")),
        approval_minutes=int(os.environ.get("OSC_APPROVAL_MINUTES", "30")),
    )
