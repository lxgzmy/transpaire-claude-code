"""Configuration for the docusign-upload MCP server.

Everything comes from DOCUSIGN_* environment variables, or from a git-ignored
.env beside the package (or the file DOCUSIGN_ENV_FILE names), so the same
code points at the sandbox or production by changing the environment only. A
variable already set in the real environment always beats the .env. This
module never opens the private key: it checks where the key file is, and
auth.py reads it only to sign. Error messages never echo a path.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

# environment -> (auth server host, label on every result)
ENVIRONMENTS = {
    "demo": ("account-d.docusign.com", "SANDBOX"),
    "production": ("account.docusign.com", "PRODUCTION"),
}

REQUIRED = ("DOCUSIGN_ENVIRONMENT", "DOCUSIGN_INTEGRATION_KEY", "DOCUSIGN_USER_ID",
            "DOCUSIGN_ACCOUNT_ID", "DOCUSIGN_PRIVATE_KEY_PATH")

# Keys load_config took from the .env rather than the real environment, so
# docusign_token_info can say where the write switch came from.
_FROM_DOTENV: set[str] = set()


class ConfigError(RuntimeError):
    """Configuration is missing or unsafe; the message names the setting."""


def checkout_root() -> str:
    """The repo checkout: docusign_upload -> docusign-upload -> mcp -> shared -> <repo>.

    abspath, not resolve(): on the server resolve() rewrites a mapped drive
    into its UNC form (the same note as osc_mcp.config)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, *([os.pardir] * 4)))


def runtime_root() -> str:
    """The checkout's git-ignored runtime folder, the only upload root in demo."""
    return os.path.join(checkout_root(), "runtime")


def _real(p: str) -> str:
    return os.path.normcase(os.path.realpath(p))


def is_inside(candidate: str, root: str) -> bool:
    """True when candidate sits under root once both are fully resolved.

    realpath on both sides: a link under the root that points elsewhere counts
    as outside, and a mapped drive and its UNC spelling compare equal (realpath
    gives both the UNC form on the server)."""
    try:
        c, r = _real(candidate), _real(root)
    except OSError:
        return False
    return c.startswith(r.rstrip("\\/") + os.sep)


def same_path(a: str, b: str) -> bool:
    try:
        return _real(a) == _real(b)
    except OSError:
        return False


def windows_drive(p: str) -> str:
    """'c:' for C:\\..., c:/... or \\\\?\\C:\\...; '' when the path names no drive letter."""
    s = p.replace("/", "\\")
    if s.startswith("\\\\?\\"):
        s = s[4:]
    return s[:2].lower() if len(s) >= 2 and s[1] == ":" else ""


def _load_dotenv() -> None:
    """KEY=VALUE lines from the .env into os.environ, never overriding a real variable."""
    env_file = os.environ.get("DOCUSIGN_ENV_FILE")
    path = Path(env_file) if env_file else Path(os.path.abspath(__file__)).parent.parent / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            _FROM_DOTENV.add(key)


def setting_source(key: str) -> str:
    """'env' (real environment or .mcp.json), 'dotenv' (the .env file) or 'default' (unset)."""
    if key in _FROM_DOTENV:
        return "dotenv"
    if key in os.environ:
        return "env"
    return "default"


def _as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def check_key_path(raw: str) -> str:
    """The private key path, or ConfigError. The path itself is never echoed."""
    if windows_drive(raw) == "c:":
        raise ConfigError("DOCUSIGN_PRIVATE_KEY_PATH is on C:. Keep the key on Z: outside the checkout.")
    if not os.path.isabs(raw):
        raise ConfigError("DOCUSIGN_PRIVATE_KEY_PATH must be an absolute path.")
    try:
        resolved = os.path.realpath(raw)
    except OSError:
        resolved = raw
    if windows_drive(resolved) == "c:":
        raise ConfigError("DOCUSIGN_PRIVATE_KEY_PATH resolves to C:. Keep the key on Z: outside the checkout.")
    if is_inside(raw, checkout_root()):
        raise ConfigError("DOCUSIGN_PRIVATE_KEY_PATH is inside the repo checkout. Keep the key outside it.")
    if not os.path.isfile(raw):
        raise ConfigError("DOCUSIGN_PRIVATE_KEY_PATH does not point to a file the server can read.")
    return raw


def upload_roots_for(environment: str, raw: str) -> tuple[str, ...]:
    """The folders documents may be read from. Demo: runtime only. Production: required."""
    entries = tuple(r.strip() for r in raw.split(";") if r.strip())
    for root in entries:
        if windows_drive(root) == "c:":
            raise ConfigError("DOCUSIGN_UPLOAD_ROOTS must not include a C: folder.")
        if not os.path.isabs(root):
            raise ConfigError("DOCUSIGN_UPLOAD_ROOTS entries must be absolute folders.")
    if environment == "demo":
        runtime = runtime_root()
        for root in entries:
            if not (same_path(root, runtime) or is_inside(root, runtime)):
                raise ConfigError(
                    "In demo the upload root is the checkout's runtime folder: the sandbox only "
                    "takes synthetic jobs. Real job folders need DOCUSIGN_ENVIRONMENT=production.")
        return entries or (runtime,)
    if not entries:
        raise ConfigError("DOCUSIGN_UPLOAD_ROOTS is required in production (the job folders' root).")
    return entries


@dataclass(frozen=True)
class Config:
    environment: str
    integration_key: str
    user_id: str
    account_id: str
    private_key_path: str
    upload_roots: tuple[str, ...]
    enable_writes: bool = False
    enable_writes_source: str = "default"
    consent_redirect_uri: str | None = None
    timeout: float = 60.0

    @property
    def auth_host(self) -> str:
        return ENVIRONMENTS[self.environment][0]

    @property
    def label(self) -> str:
        return ENVIRONMENTS[self.environment][1]

    def consent_url(self) -> str | None:
        """The one-time consent URL for the impersonated user, when a redirect URI is set."""
        if not self.consent_redirect_uri:
            return None
        query = urlencode({"response_type": "code", "scope": "signature impersonation",
                           "client_id": self.integration_key,
                           "redirect_uri": self.consent_redirect_uri}, quote_via=quote)
        return f"https://{self.auth_host}/oauth/auth?{query}"

    def redacted(self) -> dict[str, object]:
        """Safe to show: no key path, ids shortened, roots counted (a UNC root names a server)."""
        return {"environment": self.label,
                "integration_key": self.integration_key[:8] + "...",
                "user_id": self.user_id[:8] + "...",
                "account_id": self.account_id[:8] + "...",
                "upload_roots": len(self.upload_roots),
                "enable_writes": self.enable_writes,
                "enable_writes_source": self.enable_writes_source,
                "timeout": self.timeout}


def load_config() -> Config:
    """Build Config from DOCUSIGN_* variables (after loading the .env, see _load_dotenv)."""
    _load_dotenv()
    values = {k: os.environ.get(k, "").strip() for k in REQUIRED}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ConfigError("Missing required setting(s): " + ", ".join(missing)
                          + ". Put them in the server's .env (see .env.example).")
    environment = values["DOCUSIGN_ENVIRONMENT"].lower()
    if environment not in ENVIRONMENTS:
        raise ConfigError("DOCUSIGN_ENVIRONMENT must be 'demo' or 'production'.")
    return Config(
        environment=environment,
        integration_key=values["DOCUSIGN_INTEGRATION_KEY"],
        user_id=values["DOCUSIGN_USER_ID"],
        account_id=values["DOCUSIGN_ACCOUNT_ID"],
        private_key_path=check_key_path(values["DOCUSIGN_PRIVATE_KEY_PATH"]),
        upload_roots=upload_roots_for(environment, os.environ.get("DOCUSIGN_UPLOAD_ROOTS", "")),
        enable_writes=_as_bool(os.environ.get("DOCUSIGN_ENABLE_WRITES")),
        enable_writes_source=setting_source("DOCUSIGN_ENABLE_WRITES"),
        consent_redirect_uri=os.environ.get("DOCUSIGN_CONSENT_REDIRECT_URI", "").strip() or None,
        timeout=float(os.environ.get("DOCUSIGN_TIMEOUT", "").strip() or 60),
    )
