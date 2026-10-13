# docusign-upload MCP server implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local stdio MCP server, `shared/mcp/docusign-upload/`, that creates a DocuSign **draft** envelope (status `created`, never sent) from one of the six company templates with the job's own PDFs in it, carrying the template's tabs onto each document whose page count matches and flagging the rest.

**Architecture:** A Python package (`docusign_upload`) laid out like `shared/mcp/osc-api/`: `config` (env and path rules), `auth` (JWT Grant), `pdfcheck` (file checks), `draft` (pure request building and read-back), `client` (the fixed list of REST calls), `server` (three FastMCP tools). PR #49's `docusign_payload.py` gains a `documents` list; Claude passes the payload's values to the tools as arguments.

**Tech Stack:** Python 3.11+, `mcp>=1.2,<2` (FastMCP), `httpx`, `PyJWT[crypto]`, `pypdf`; tests with `unittest` and `httpx.MockTransport` (no network, no credentials). DocuSign eSignature REST API v2.1.

**Spec:** [`docs/superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md`](../brainstorms/2026-10-13-docusign-upload-mcp.md)

## Global Constraints

- Branch `docusign-upload-mcp`, stacked on PR #49 (`docusign-integration`). Every change lands through a PR whose base is `docusign-integration`; never commit to `main`, never merge, never force-push. Commit messages and PR bodies carry no AI attribution (no `Co-Authored-By`, no "Generated with").
- The only envelope status ever sent is `"created"`, a constant in `draft.py`. No code path may send, void, correct or delete an envelope: `client.py` has no PUT, PATCH, DELETE or generic request method.
- Dependencies, exactly: `mcp>=1.2.0,<2`, `httpx>=0.27`, `PyJWT[crypto]>=2.8`, `pypdf>=4.0`; `requires-python = ">=3.11"`.
- `DOCUSIGN_ENVIRONMENT=demo` locks the upload root to the checkout's `runtime` folder (any other `DOCUSIGN_UPLOAD_ROOTS` entry is a config error); `production` requires `DOCUSIGN_UPLOAD_ROOTS`.
- The private key is never in the repo, never on `C:`, never logged, returned or printed. `DOCUSIGN_PRIVATE_KEY_PATH` is refused when relative, on `C:` or inside the checkout. Config errors never echo a path.
- Document kinds: `BUILD CONTRACT`, `INCLUSIONS`, `PRELIMINARY AGREEMENT`, `PLANS`, matched in template document names by containment, never by id or order. The build contract must carry (page counts equal); otherwise the run stops.
- Limits: 25 MB per document; estimated request body 30 MiB; duplicate window 180 days; `email_subject` at most 100 characters; `email_blurb` at most 10,000; `job_no` matches `^[A-Za-z0-9-]{1,20}$`.
- Tools: `docusign_token_info` and `docusign_draft_preview` (read, `allow`), `docusign_create_draft` (write, `ask`); MCP server name `docusign-upload`.
- No client data, real names, real emails, account or template ids, or server names in the repo. Tests use synthetic values (`@example.com`, `tmpl-...`, `acct-synthetic`).
- Docs in Australian English through `transpire-writing`: no em or en dashes, sentence-case headings, no buzzwords. Code comments follow the same no-dash rule.
- Package tests run from `shared/mcp/docusign-upload` as `.venv/bin/python -m unittest discover -s tests -v` (Windows: `.venv\Scripts\python.exe`). Role script tests run from the repo root as `python3 job-roles/contract-admin/scripts/test_docusign_payload.py`.

## Review Focus

- **Role names that differ only in capitals.** QLD 2 Buyer's first role is `BUYER 1`, NSW's is `Buyer 1`. A role off by case must stop and list the template's roles, never add a second recipient. Test: Task 4, `test_role_case_mismatch_stops_with_the_role_list`.
- **Template names with trailing spaces and near-duplicates.** Three stored names end in a space, and a search can also return `... (old)` copies. Only the trimmed exact name counts. Test: Task 4, `test_pick_template_is_exact_after_trimming`.
- **Job folders with spaces and square brackets, and links out of a root.** `26098 LOT 4 [STAGE 2]` must pass; a link inside `runtime` that points elsewhere must be refused. Tests: Task 1 `InsideTests`, Task 3 `test_spaces_and_brackets_in_the_job_folder_are_fine` and `test_a_link_out_of_the_root_is_refused`.
- **Non-JSON error bodies.** A proxy can answer 502 with an HTML page. The tool reports the status and does not crash or retry. Test: Task 6, `test_a_non_json_error_body_does_not_crash`.
- **Job numbers carrying query characters.** `00001&status=any` must be refused before any network call, so it cannot widen the duplicate search. Tests: Task 4 `test_text_args`, Task 7 `test_job_no_with_query_characters_is_refused_before_network`.

---

## File structure

| File | Responsibility |
|---|---|
| `shared/mcp/docusign-upload/pyproject.toml` (create) | Package metadata and the four dependencies |
| `shared/mcp/docusign-upload/docusign_upload/__init__.py` (create) | Package marker |
| `shared/mcp/docusign-upload/docusign_upload/config.py` (create) | `DOCUSIGN_*` settings, `.env` loading, key-path and upload-root rules, `is_inside` |
| `shared/mcp/docusign-upload/docusign_upload/auth.py` (create) | JWT assertion, token exchange, userinfo, cached `Session` |
| `shared/mcp/docusign-upload/docusign_upload/pdfcheck.py` (create) | `check_pdf`: roots, type, size, encryption, page count |
| `shared/mcp/docusign-upload/docusign_upload/draft.py` (create) | Pure functions: argument checks, template parsing, carry or flag, size, duplicates, request body, read-back |
| `shared/mcp/docusign-upload/docusign_upload/client.py` (create) | The fixed list of REST calls; create refuses any status but `created` |
| `shared/mcp/docusign-upload/docusign_upload/server.py` (create) | The three FastMCP tools |
| `shared/mcp/docusign-upload/docusign_upload/selftest.py` (create) | Read-only connectivity check |
| `shared/mcp/docusign-upload/tests/support.py` (create) | Synthetic fixtures: key pair, config, PDFs, templates, fake DocuSign |
| `shared/mcp/docusign-upload/tests/test_*.py` (create) | One test module per package module |
| `shared/mcp/docusign-upload/README.md`, `.env.example` (create) | Install, config, gates |
| `job-roles/contract-admin/scripts/docusign_payload.py` (modify) | `documents` list in `docusign_envelope.json` and the report |
| `job-roles/contract-admin/scripts/test_docusign_payload.py` (modify) | `check_documents_list` |
| `job-roles/contract-admin/scripts/README.md` (modify) | Row text for the two payload files |
| `.mcp.json`, `.claude/settings.json` (modify) | Registration and permissions |
| `.gitignore` (modify) | `*.pem`, `*.key` backstop |
| `docs/mcp-servers.md`, `CLAUDE.md` (modify) | Register row and section; one sentence in the gated-write paragraph |

---

### Task 1: Package scaffold and config rules

**Files:**
- Create: `shared/mcp/docusign-upload/pyproject.toml`
- Create: `shared/mcp/docusign-upload/docusign_upload/__init__.py`
- Create: `shared/mcp/docusign-upload/docusign_upload/config.py`
- Test: `shared/mcp/docusign-upload/tests/test_config.py`
- Modify: `.gitignore` (Transpire section, after `*.variation.json`)

**Interfaces:**
- Produces (used by every later task):
  - `ENVIRONMENTS: dict[str, tuple[str, str]]` (`"demo" -> ("account-d.docusign.com", "SANDBOX")`, `"production" -> ("account.docusign.com", "PRODUCTION")`)
  - `class ConfigError(RuntimeError)`
  - `checkout_root() -> str`, `runtime_root() -> str`
  - `is_inside(candidate: str, root: str) -> bool`, `same_path(a: str, b: str) -> bool`, `windows_drive(p: str) -> str`
  - `check_key_path(raw: str) -> str`, `upload_roots_for(environment: str, raw: str) -> tuple[str, ...]`
  - `@dataclass(frozen=True) class Config` with fields `environment, integration_key, user_id, account_id, private_key_path, upload_roots, enable_writes=False, enable_writes_source="default", consent_redirect_uri=None, timeout=60.0`, properties `auth_host`, `label`, methods `consent_url() -> str | None`, `redacted() -> dict`
  - `load_config() -> Config`
  - module-level `_FROM_DOTENV: set[str]` (tests clear it)

- [ ] **Step 1: Create the package skeleton**

`shared/mcp/docusign-upload/pyproject.toml`:

```toml
[project]
name = "docusign-upload-mcp"
version = "0.1.0"
description = "Local MCP server that creates DocuSign draft envelopes with a job's own PDFs. Never sends."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    # mcp 2.x negotiates a protocol the Claude Code CLI rejects at the
    # initialize handshake, so stay on 1.x (same pin as osc-api).
    "mcp>=1.2.0,<2",
    "httpx>=0.27",
    "PyJWT[crypto]>=2.8",
    "pypdf>=4.0",
]

[project.scripts]
docusign-upload-mcp = "docusign_upload.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["docusign_upload"]
```

`shared/mcp/docusign-upload/docusign_upload/__init__.py`:

```python
"""MCP server that creates DocuSign draft envelopes with a job's own PDFs. Never sends."""
```

Create a placeholder `shared/mcp/docusign-upload/README.md` containing the single line `# docusign-upload MCP server` (Task 9 writes the full text; hatchling needs the file to exist).

- [ ] **Step 2: Create the venv and install**

```bash
cd shared/mcp/docusign-upload && python3 -m venv .venv && .venv/bin/python -m pip install -e .
```

Expected: `Successfully installed ... docusign-upload-mcp-0.1.0 ... mcp-1.x ... PyJWT-2.x ... pypdf-...`. The install needs network access to PyPI. If no `mcp` 1.x release installs on this Python, recreate the venv with an older Python that does (for example `python3.12 -m venv .venv`) and say so in the task report.

- [ ] **Step 3: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_config.py`:

```python
"""Config rules: required settings, key custody, upload roots per environment."""
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import config
from docusign_upload.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = os.path.join(self.tmp.name, "synthetic-key.pem")
        with open(self.key, "w", encoding="utf-8") as fh:
            fh.write("not a real key; config never opens it\n")
        config._FROM_DOTENV.clear()
        self.addCleanup(config._FROM_DOTENV.clear)

    def env(self, **overrides):
        """Patch os.environ to a complete demo config plus overrides (None removes a key)."""
        values = {"DOCUSIGN_ENV_FILE": os.path.join(self.tmp.name, "absent.env"),
                  "DOCUSIGN_ENVIRONMENT": "demo",
                  "DOCUSIGN_INTEGRATION_KEY": "ik-synthetic-0000",
                  "DOCUSIGN_USER_ID": "user-synthetic-0000",
                  "DOCUSIGN_ACCOUNT_ID": "acct-synthetic",
                  "DOCUSIGN_PRIVATE_KEY_PATH": self.key}
        values.update(overrides)
        return patch.dict(os.environ, {k: v for k, v in values.items() if v is not None}, clear=True)

    def test_loads_a_complete_demo_config(self):
        with self.env():
            c = load_config()
        self.assertEqual((c.environment, c.label, c.auth_host),
                         ("demo", "SANDBOX", "account-d.docusign.com"))
        self.assertEqual(c.upload_roots, (config.runtime_root(),))
        self.assertEqual((c.enable_writes, c.enable_writes_source, c.timeout), (False, "default", 60.0))

    def test_missing_settings_are_named(self):
        with self.env(DOCUSIGN_INTEGRATION_KEY=None, DOCUSIGN_USER_ID=None):
            with self.assertRaises(ConfigError) as cm:
                load_config()
        self.assertIn("DOCUSIGN_INTEGRATION_KEY", str(cm.exception))
        self.assertIn("DOCUSIGN_USER_ID", str(cm.exception))

    def test_environment_must_be_demo_or_production(self):
        with self.env(DOCUSIGN_ENVIRONMENT="staging"):
            with self.assertRaisesRegex(ConfigError, "'demo' or 'production'"):
                load_config()

    def test_key_on_c_is_refused_without_echoing_the_path(self):
        for path in (r"C:\secretfolder-x1\docusign.pem", "c:/secretfolder-x1/docusign.pem",
                     r"\\?\C:\secretfolder-x1\docusign.pem"):
            with self.subTest(path=path), self.env(DOCUSIGN_PRIVATE_KEY_PATH=path):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("on C:", str(cm.exception))
                self.assertNotIn("secretfolder-x1", str(cm.exception))

    def test_key_must_be_absolute(self):
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH="keys/docusign.pem"):
            with self.assertRaisesRegex(ConfigError, "absolute"):
                load_config()

    def test_key_inside_the_checkout_is_refused(self):
        inside = os.path.join(config.checkout_root(), "shared", "mcp", "docusign-upload", "key.pem")
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH=inside):
            with self.assertRaisesRegex(ConfigError, "inside the repo checkout"):
                load_config()

    def test_key_file_must_exist(self):
        with self.env(DOCUSIGN_PRIVATE_KEY_PATH=os.path.join(self.tmp.name, "missing.pem")):
            with self.assertRaisesRegex(ConfigError, "does not point to a file"):
                load_config()

    def test_demo_refuses_roots_outside_runtime(self):
        with self.env(DOCUSIGN_UPLOAD_ROOTS=self.tmp.name):
            with self.assertRaisesRegex(ConfigError, "synthetic jobs"):
                load_config()

    def test_demo_accepts_a_folder_inside_runtime(self):
        sub = os.path.join(config.runtime_root(), "contract-admin", "outputs")
        with self.env(DOCUSIGN_UPLOAD_ROOTS=sub):
            self.assertEqual(load_config().upload_roots, (sub,))

    def test_production_needs_roots_and_refuses_c(self):
        with self.env(DOCUSIGN_ENVIRONMENT="production"):
            with self.assertRaisesRegex(ConfigError, "required in production"):
                load_config()
        with self.env(DOCUSIGN_ENVIRONMENT="production", DOCUSIGN_UPLOAD_ROOTS=r"C:\PROJECTS"):
            with self.assertRaisesRegex(ConfigError, "C:"):
                load_config()
        with self.env(DOCUSIGN_ENVIRONMENT="production", DOCUSIGN_UPLOAD_ROOTS=self.tmp.name):
            c = load_config()
        self.assertEqual((c.label, c.auth_host, c.upload_roots),
                         ("PRODUCTION", "account.docusign.com", (self.tmp.name,)))

    def test_real_environment_beats_dotenv_and_the_source_is_reported(self):
        dotenv = os.path.join(self.tmp.name, "server.env")
        with open(dotenv, "w", encoding="utf-8") as fh:
            fh.write("DOCUSIGN_ENABLE_WRITES=true\nDOCUSIGN_TIMEOUT=7\n")
        with self.env(DOCUSIGN_ENV_FILE=dotenv):
            c = load_config()
        self.assertEqual((c.enable_writes, c.enable_writes_source, c.timeout), (True, "dotenv", 7.0))
        config._FROM_DOTENV.clear()
        with self.env(DOCUSIGN_ENV_FILE=dotenv, DOCUSIGN_ENABLE_WRITES="false"):
            c = load_config()
        self.assertEqual((c.enable_writes, c.enable_writes_source), (False, "env"))

    def test_consent_url_is_encoded(self):
        with self.env(DOCUSIGN_CONSENT_REDIRECT_URI="https://example.com/after consent"):
            url = load_config().consent_url()
        self.assertTrue(url.startswith("https://account-d.docusign.com/oauth/auth?"))
        self.assertIn("scope=signature%20impersonation", url)
        self.assertIn("client_id=ik-synthetic-0000", url)
        self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fafter%20consent", url)
        with self.env():
            self.assertIsNone(load_config().consent_url())

    def test_redacted_view_hides_the_key_path_and_counts_roots(self):
        with self.env():
            view = load_config().redacted()
        self.assertNotIn(self.key, str(view))
        self.assertEqual((view["environment"], view["upload_roots"]), ("SANDBOX", 1))


class InsideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_spaces_and_brackets_in_folder_names(self):
        root = os.path.join(self.tmp.name, "PROJECTS", "REGION - SEQ")
        job = os.path.join(root, "26098 LOT 4 [STAGE 2]", "CONTRACT DOCUMENTATION")
        os.makedirs(job)
        self.assertTrue(config.is_inside(os.path.join(job, "BUILD CONTRACT_LOT 4.pdf"), root))
        self.assertFalse(config.is_inside(root, root))
        sibling = os.path.join(self.tmp.name, "PROJECTS", "REGION - SEQX", "a.pdf")
        self.assertFalse(config.is_inside(sibling, root))

    def test_a_link_out_of_the_root_is_outside(self):
        root = os.path.join(self.tmp.name, "root")
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(root)
        os.makedirs(outside)
        link = os.path.join(root, "link")
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need extra rights on this machine")
        self.assertFalse(config.is_inside(os.path.join(link, "a.pdf"), root))

    def test_windows_drive(self):
        self.assertEqual(config.windows_drive(r"C:\x"), "c:")
        self.assertEqual(config.windows_drive("z:/x"), "z:")
        self.assertEqual(config.windows_drive(r"\\?\C:\x"), "c:")
        self.assertEqual(config.windows_drive("/Users/x"), "")
```

- [ ] **Step 4: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_config.py' -v`
Expected: ERROR, `ImportError: cannot import name 'ConfigError' from 'docusign_upload.config'` (module missing).

- [ ] **Step 5: Write `config.py`**

`shared/mcp/docusign-upload/docusign_upload/config.py`:

```python
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
```

- [ ] **Step 6: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_config.py' -v`
Expected: `Ran 16 tests ... OK` (the symlink test may report `skipped`).

- [ ] **Step 7: Add the key backstop to `.gitignore`**

In the Transpire section of `.gitignore`, after the line `*.variation.json`, add:

```gitignore
# DocuSign JWT keys live on Z: outside the checkout; never commit one by accident
*.pem
*.key
```

Run: `git check-ignore -v shared/mcp/docusign-upload/x.pem`
Expected: `.gitignore:<line>:*.pem	shared/mcp/docusign-upload/x.pem`

- [ ] **Step 8: Commit**

```bash
git add .gitignore shared/mcp/docusign-upload/pyproject.toml shared/mcp/docusign-upload/README.md shared/mcp/docusign-upload/docusign_upload/__init__.py shared/mcp/docusign-upload/docusign_upload/config.py shared/mcp/docusign-upload/tests/test_config.py
git commit -m "docusign-upload: package scaffold and config rules (key off C: and out of the checkout, demo locked to runtime)"
```

---

### Task 2: JWT Grant authentication

**Files:**
- Create: `shared/mcp/docusign-upload/docusign_upload/auth.py`
- Create: `shared/mcp/docusign-upload/tests/support.py`
- Test: `shared/mcp/docusign-upload/tests/test_auth.py`

**Interfaces:**
- Consumes: `Config` (Task 1).
- Produces:
  - `SCOPE = "signature impersonation"`, `GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"`
  - `class AuthError(RuntimeError)` with attributes `consent_url: str | None`, `status: int | None`
  - `@dataclass(frozen=True) class Session` with `access_token: str`, `expires_at: float` (monotonic), `base_uri: str`, `account_name: str`, `user_name: str`, and `account_url(account_id: str) -> str` returning `<base_uri>/restapi/v2.1/accounts/<account_id>`
  - `build_assertion(config: Config, private_key_pem: bytes, now: int | None = None) -> str`
  - `class Authenticator(config: Config, http: httpx.AsyncClient)` with `async session() -> Session` and attributes `config`, `http`, `_session`
  - `tests/support.py`: `ACCOUNT = "acct-synthetic"`, `BASE = "https://demo.invalid"`, `keypair() -> tuple[bytes, bytes]` (cached PKCS8 private PEM, public PEM), `write_key(folder: str, private_pem: bytes) -> str`, `make_config(key_path: str, roots: tuple[str, ...] = (), **overrides) -> Config`

- [ ] **Step 1: Write the test support module**

`shared/mcp/docusign-upload/tests/support.py`:

```python
"""Synthetic fixtures for the docusign-upload tests. No real data, no network, no credentials."""
from __future__ import annotations

import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from docusign_upload.config import Config

ACCOUNT = "acct-synthetic"
BASE = "https://demo.invalid"

_KEYPAIR: tuple[bytes, bytes] | None = None


def keypair() -> tuple[bytes, bytes]:
    """(private PEM, public PEM), generated once per test run."""
    global _KEYPAIR
    if _KEYPAIR is None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        _KEYPAIR = (
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()),
            key.public_key().public_bytes(serialization.Encoding.PEM,
                                          serialization.PublicFormat.SubjectPublicKeyInfo),
        )
    return _KEYPAIR


def write_key(folder: str, private_pem: bytes) -> str:
    path = os.path.join(folder, "synthetic-key.pem")
    with open(path, "wb") as fh:
        fh.write(private_pem)
    return path


def make_config(key_path: str, roots: tuple[str, ...] = (), **overrides) -> Config:
    values = dict(environment="demo", integration_key="ik-synthetic-0000",
                  user_id="user-synthetic-0000", account_id=ACCOUNT, private_key_path=key_path,
                  upload_roots=roots, enable_writes=True, enable_writes_source="env",
                  consent_redirect_uri="https://example.com/consent", timeout=5.0)
    values.update(overrides)
    return Config(**values)
```

- [ ] **Step 2: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_auth.py`:

```python
"""JWT Grant: the assertion, the token exchange, userinfo, consent and caching."""
import dataclasses
import tempfile
import time
import unittest
from urllib.parse import parse_qs

import httpx
import jwt

from docusign_upload.auth import AuthError, Authenticator, build_assertion
from support import ACCOUNT, BASE, keypair, make_config, write_key


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.private, self.public = keypair()
        self.config = make_config(write_key(self.tmp.name, self.private))
        self.token_calls = 0
        self.forms = []
        self.token_reply = (200, {"access_token": "synthetic-token", "token_type": "Bearer",
                                  "expires_in": 3600})
        self.accounts = [{"account_id": ACCOUNT, "account_name": "synthetic", "base_uri": BASE}]

        def handle(request):
            if request.url.path == "/oauth/token":
                self.token_calls += 1
                self.forms.append(parse_qs(request.content.decode()))
                status, body = self.token_reply
                return httpx.Response(status, json=body)
            if request.url.path == "/oauth/userinfo":
                assert request.headers["Authorization"] == "Bearer synthetic-token"
                return httpx.Response(200, json={"name": "Synthetic User", "accounts": self.accounts})
            return httpx.Response(404)

        self.http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        self.addAsyncCleanup(self.http.aclose)
        self.auth = Authenticator(self.config, self.http)

    def test_assertion_claims_and_signature(self):
        token = build_assertion(self.config, self.private, now=1_000_000)
        claims = jwt.decode(token, self.public, algorithms=["RS256"],
                            audience="account-d.docusign.com",
                            options={"verify_exp": False, "verify_iat": False})
        self.assertEqual(claims, {"iss": "ik-synthetic-0000", "sub": "user-synthetic-0000",
                                  "aud": "account-d.docusign.com", "iat": 1_000_000,
                                  "exp": 1_003_600, "scope": "signature impersonation"})
        self.assertEqual(jwt.get_unverified_header(token)["alg"], "RS256")

    async def test_session_signs_in_once_and_reuses_the_token(self):
        first = await self.auth.session()
        second = await self.auth.session()
        self.assertIs(first, second)
        self.assertEqual(self.token_calls, 1)
        self.assertEqual(self.forms[0]["grant_type"], ["urn:ietf:params:oauth:grant-type:jwt-bearer"])
        self.assertIn("assertion", self.forms[0])
        self.assertEqual(first.account_url(ACCOUNT), f"{BASE}/restapi/v2.1/accounts/{ACCOUNT}")
        self.assertEqual((first.account_name, first.user_name), ("synthetic", "Synthetic User"))

    async def test_an_expired_token_signs_in_again(self):
        session = await self.auth.session()
        self.auth._session = dataclasses.replace(session, expires_at=time.monotonic() - 1)
        await self.auth.session()
        self.assertEqual(self.token_calls, 2)

    async def test_consent_required_carries_the_consent_url(self):
        self.token_reply = (400, {"error": "consent_required"})
        with self.assertRaises(AuthError) as cm:
            await self.auth.session()
        self.assertIn("Consent", str(cm.exception))
        self.assertTrue(cm.exception.consent_url.startswith("https://account-d.docusign.com/oauth/auth?"))

    async def test_a_refused_token_names_the_error_not_the_key(self):
        self.token_reply = (400, {"error": "invalid_grant",
                                  "error_description": "no_valid_keys_or_signatures"})
        with self.assertRaises(AuthError) as cm:
            await self.auth.session()
        self.assertIn("invalid_grant", str(cm.exception))
        self.assertIn("no_valid_keys_or_signatures", str(cm.exception))
        self.assertNotIn(self.config.private_key_path, str(cm.exception))

    async def test_an_account_the_user_does_not_hold_is_refused(self):
        self.accounts = [{"account_id": "acct-other", "account_name": "other", "base_uri": BASE}]
        with self.assertRaisesRegex(AuthError, "not one of this user's accounts"):
            await self.auth.session()

    async def test_an_unreadable_key_file_is_reported_plainly(self):
        self.auth.config = make_config("/nonexistent/synthetic-key.pem")
        with self.assertRaisesRegex(AuthError, "could not be read"):
            await self.auth.session()
        self.assertEqual(self.token_calls, 0)
```

- [ ] **Step 3: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_auth.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'docusign_upload.auth'`.

- [ ] **Step 4: Write `auth.py`**

`shared/mcp/docusign-upload/docusign_upload/auth.py`:

```python
"""JWT Grant for the DocuSign eSignature REST API.

An RS256 assertion (iss the integration key, sub the impersonated user, aud the
environment's auth server, scope "signature impersonation") is exchanged at
/oauth/token for an access token, and /oauth/userinfo then gives the base URI
of the configured account. The key file is opened only here, only to sign; its
contents never leave this module and no message includes its path.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx
import jwt

from .config import Config

SCOPE = "signature impersonation"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
REFRESH_MARGIN_SECONDS = 300


class AuthError(RuntimeError):
    """Sign-in failed. consent_url is set when the user has not consented yet."""

    def __init__(self, message: str, *, consent_url: str | None = None, status: int | None = None):
        super().__init__(message)
        self.consent_url = consent_url
        self.status = status


@dataclass(frozen=True)
class Session:
    access_token: str
    expires_at: float  # time.monotonic() seconds
    base_uri: str
    account_name: str
    user_name: str

    def account_url(self, account_id: str) -> str:
        return f"{self.base_uri.rstrip('/')}/restapi/v2.1/accounts/{quote(account_id, safe='')}"


def build_assertion(config: Config, private_key_pem: bytes, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    claims = {"iss": config.integration_key, "sub": config.user_id, "aud": config.auth_host,
              "iat": now, "exp": now + 3600, "scope": SCOPE}
    return jwt.encode(claims, private_key_pem, algorithm="RS256")


def _json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class Authenticator:
    def __init__(self, config: Config, http: httpx.AsyncClient):
        self.config = config
        self.http = http
        self._session: Session | None = None

    async def session(self) -> Session:
        if self._session is None or time.monotonic() >= self._session.expires_at:
            self._session = await self._login()
        return self._session

    async def _login(self) -> Session:
        try:
            with open(self.config.private_key_path, "rb") as fh:
                pem = fh.read()
        except OSError:
            raise AuthError("The private key file could not be read by the server. Check "
                            "DOCUSIGN_PRIVATE_KEY_PATH and the folder's permissions.") from None
        assertion = build_assertion(self.config, pem)
        host = self.config.auth_host
        resp = await self.http.post(f"https://{host}/oauth/token",
                                    data={"grant_type": GRANT_TYPE, "assertion": assertion})
        if resp.status_code != 200:
            body = _json(resp)
            error = str(body.get("error") or "no error code")
            if error == "consent_required":
                raise AuthError("Consent has not been granted for this integration key and user. "
                                "The template owner opens the consent URL once, signs in and "
                                "clicks Accept.", consent_url=self.config.consent_url(),
                                status=resp.status_code)
            detail = str(body.get("error_description") or "")
            raise AuthError(f"Token request refused ({resp.status_code} {error}"
                            f"{', ' + detail if detail else ''}). Check the integration key, the "
                            "user id, the key pair and the environment.", status=resp.status_code)
        payload = resp.json()
        token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))
        info = await self.http.get(f"https://{host}/oauth/userinfo",
                                   headers={"Authorization": f"Bearer {token}"})
        if info.status_code != 200:
            raise AuthError(f"userinfo failed ({info.status_code}).", status=info.status_code)
        data = _json(info)
        account = next((a for a in data.get("accounts", [])
                        if a.get("account_id") == self.config.account_id), None)
        if account is None:
            raise AuthError("The configured account is not one of this user's accounts. Check "
                            "DOCUSIGN_ACCOUNT_ID against the Apps and Keys page.")
        return Session(access_token=token,
                       expires_at=time.monotonic() + max(expires_in - REFRESH_MARGIN_SECONDS, 60),
                       base_uri=str(account.get("base_uri", "")),
                       account_name=str(account.get("account_name", "")),
                       user_name=str(data.get("name", "")))
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_auth.py' -v`
Expected: `Ran 7 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/auth.py shared/mcp/docusign-upload/tests/support.py shared/mcp/docusign-upload/tests/test_auth.py
git commit -m "docusign-upload: JWT Grant sign-in with consent URL, account check and token reuse"
```

---

### Task 3: PDF checks

**Files:**
- Create: `shared/mcp/docusign-upload/docusign_upload/pdfcheck.py`
- Modify: `shared/mcp/docusign-upload/tests/support.py` (append `make_pdf`)
- Test: `shared/mcp/docusign-upload/tests/test_pdfcheck.py`

**Interfaces:**
- Consumes: `is_inside` (Task 1).
- Produces:
  - `MAX_DOCUMENT_BYTES = 25 * 1024 * 1024`
  - `class PdfCheckError(Exception)`
  - `@dataclass(frozen=True) class PdfFile` with `path: str`, `name: str`, `bytes: int`, `pages: int`
  - `check_pdf(path: str, roots: tuple[str, ...]) -> PdfFile`
  - `tests/support.py`: `make_pdf(path: str, pages: int, *, password: str | None = None) -> str`

- [ ] **Step 1: Append `make_pdf` to `tests/support.py`**

Add the import `from pypdf import PdfWriter` beside the other imports at the top, and append:

```python
def make_pdf(path: str, pages: int, *, password: str | None = None) -> str:
    """A blank A4 PDF with the given page count (optionally password-protected)."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if password:
        writer.encrypt(password, algorithm="AES-256")
    with open(path, "wb") as fh:
        writer.write(fh)
    return path
```

- [ ] **Step 2: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_pdfcheck.py`:

```python
"""Document checks: roots, type, size, encryption, page count."""
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import pdfcheck
from docusign_upload.pdfcheck import PdfCheckError, check_pdf
from support import make_pdf


class PdfCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "runtime")
        os.makedirs(self.root)
        self.roots = (self.root,)

    def path(self, *parts):
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p

    def write(self, name, data):
        p = self.path(name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p

    def test_a_good_pdf_reports_name_pages_and_bytes(self):
        p = make_pdf(self.path("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf"), 37)
        f = check_pdf(p, self.roots)
        self.assertEqual((f.name, f.pages, f.path), ("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf", 37, p))
        self.assertEqual(f.bytes, os.path.getsize(p))

    def test_spaces_and_brackets_in_the_job_folder_are_fine(self):
        p = make_pdf(self.path("26098 LOT 4 [STAGE 2]", "CONTRACT DOCUMENTATION", "PLANS_LOT 4.pdf"), 3)
        self.assertEqual(check_pdf(p, self.roots).pages, 3)

    def test_refusals(self):
        outside_dir = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(outside_dir)
        cases = {
            "relative/path.pdf": "absolute",
            make_pdf(os.path.join(outside_dir, "a.pdf"), 1): "outside the allowed upload roots",
            self.path("missing.pdf"): "not an existing file",
            self.write("notes.txt", b"%PDF-1.7 pretend"): r"not a \.pdf",
            self.write("fake.pdf", b"PK\x03\x04 a zip, not a pdf"): "does not start with %PDF-",
            self.write("damaged.pdf", b"%PDF-1.7\nnothing else here"): "page count could not be read|has no pages",
            make_pdf(self.path("locked.pdf"), 2, password="synthetic"): "password-protected",
        }
        for path, needle in cases.items():
            with self.subTest(file=os.path.basename(path)):
                with self.assertRaisesRegex(PdfCheckError, needle):
                    check_pdf(path, self.roots)

    def test_no_roots_means_no_documents(self):
        p = make_pdf(self.path("a.pdf"), 1)
        with self.assertRaisesRegex(PdfCheckError, "outside"):
            check_pdf(p, ())

    def test_size_limit(self):
        p = make_pdf(self.path("big.pdf"), 1)
        with patch.object(pdfcheck, "MAX_DOCUMENT_BYTES", 10):
            with self.assertRaisesRegex(PdfCheckError, "limit per document"):
                check_pdf(p, self.roots)

    def test_a_link_out_of_the_root_is_refused(self):
        outside_dir = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(outside_dir)
        target = make_pdf(os.path.join(outside_dir, "target.pdf"), 1)
        link = self.path("link.pdf")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks need extra rights on this machine")
        with self.assertRaisesRegex(PdfCheckError, "outside"):
            check_pdf(link, self.roots)
```

- [ ] **Step 3: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_pdfcheck.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'docusign_upload.pdfcheck'`.

- [ ] **Step 4: Write `pdfcheck.py`**

`shared/mcp/docusign-upload/docusign_upload/pdfcheck.py`:

```python
"""Checks on a job PDF before any of it goes into a request.

The path must be absolute and sit under an upload root (resolved, so a link
out of the root is refused). The file must be a regular .pdf that starts with
%PDF-, holds at most 25 MB, is not password-protected and has a readable page
count. Only the PDF's structure is read here; draft.py reads the bytes for the
request after every check has passed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from .config import is_inside

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


class PdfCheckError(Exception):
    """A document failed a check; the message says which."""


@dataclass(frozen=True)
class PdfFile:
    path: str
    name: str
    bytes: int
    pages: int


def check_pdf(path: str, roots: tuple[str, ...]) -> PdfFile:
    if not path or not os.path.isabs(path):
        raise PdfCheckError("not an absolute path")
    if not any(is_inside(path, root) for root in roots):
        raise PdfCheckError("outside the allowed upload roots")
    p = Path(path)
    if not p.is_file():
        raise PdfCheckError("not an existing file on the server")
    if p.suffix.lower() != ".pdf":
        raise PdfCheckError("not a .pdf file")
    size = p.stat().st_size
    if size > MAX_DOCUMENT_BYTES:
        raise PdfCheckError(f"{size / 1048576:.1f} MB, over the {MAX_DOCUMENT_BYTES // 1048576} MB "
                            "limit per document")
    with p.open("rb") as fh:
        if fh.read(5) != b"%PDF-":
            raise PdfCheckError("does not start with %PDF-, so it is not a PDF")
    try:
        reader = PdfReader(str(p))
        encrypted = reader.is_encrypted
        pages = 0 if encrypted else len(reader.pages)
    except Exception as exc:  # pypdf raises several types on a damaged file
        raise PdfCheckError("its page count could not be read (a damaged PDF?)") from exc
    if encrypted:
        raise PdfCheckError("password-protected, and DocuSign cannot open it")
    if pages < 1:
        raise PdfCheckError("has no pages")
    return PdfFile(path=path, name=p.name, bytes=size, pages=pages)
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_pdfcheck.py' -v`
Expected: `Ran 6 tests ... OK` (the symlink test may report `skipped`).

- [ ] **Step 6: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/pdfcheck.py shared/mcp/docusign-upload/tests/support.py shared/mcp/docusign-upload/tests/test_pdfcheck.py
git commit -m "docusign-upload: PDF checks (upload roots resolved, type, 25 MB, encryption, page count)"
```

---

### Task 4: Building the request (template, recipients, carry or flag, body)

**Files:**
- Create: `shared/mcp/docusign-upload/docusign_upload/draft.py`
- Modify: `shared/mcp/docusign-upload/tests/support.py` (append template fixtures)
- Test: `shared/mcp/docusign-upload/tests/test_draft.py`

**Interfaces:**
- Consumes: `PdfFile` (Task 3).
- Produces (Task 5 appends to the same module; Tasks 6 and 7 import these):
  - Constants: `DRAFT_STATUS = "created"`, `KINDS`, `MAX_BODY_BYTES`, `BODY_OVERHEAD_BYTES`, `SUBJECT_MAX = 100`, `BLURB_MAX = 10000`, `JOB_NO_RE`, `EMAIL_RE`, `DEAD_STATUSES = {"voided", "declined", "deleted"}`, `FRESH_ID_START = 9001`
  - `class Stop(Exception)`
  - Frozen dataclasses: `TemplateDoc(document_id: str, kind: str, pages: int)`, `TemplateRole(role: str, recipient_id: str, routing_order: str, recipient_type: str)`, `Template(template_id: str, name: str, documents: tuple[TemplateDoc, ...], roles: tuple[TemplateRole, ...])`, `Recipient(role: str, name: str, email: str)`, `PlannedDoc(kind: str, file: PdfFile, carry: bool, template_document_id: str | None, reason: str)`, `Plan(template: Template, recipients: tuple[tuple[Recipient, TemplateRole], ...], documents: tuple[PlannedDoc, ...], email_subject: str, email_blurb: str, job_no: str)`
  - Functions: `check_text_args(job_no, email_subject, email_blurb) -> None`, `check_kinds(kinds: list[str]) -> list[str]`, `kind_of(document_name: str) -> str | None`, `pick_template(candidates: list[dict], wanted: str) -> dict`, `parse_template(raw: dict) -> Template`, `check_recipients(raw: list[dict], template: Template) -> tuple[tuple[Recipient, TemplateRole], ...]`, `plan_documents(files: list[tuple[str, PdfFile]], template: Template) -> tuple[PlannedDoc, ...]`, `estimated_body_bytes(documents) -> int`, `check_size(documents) -> None`, `find_duplicate(envelopes: list[dict], job_no: str) -> dict | None`, `build_body(plan: Plan) -> dict`, `plan_view(plan: Plan) -> dict`
  - `tests/support.py`: `qld_single_template() -> dict` (template id `tmpl-qld-single`, document ids `1`, `86092972`, `3`, pages 37/15/4, signer roles `Buyer` id 1 order 1 and `Builder` id 3 order 2), `nsw_company_template() -> dict`

- [ ] **Step 1: Append the template fixtures to `tests/support.py`**

```python
def qld_single_template() -> dict:
    """Shaped like the sandbox's QLD Single Buyer template: three documents (a mix of small
    and eight-digit ids, as in the account) and two signer roles. Synthetic names and ids."""
    return {"templateId": "tmpl-qld-single", "name": "QLD Build _ Single Buyer ",
            "documents": [
                {"documentId": "1", "name": "BUILD CONTRACT _LOT 0_SYNTHETIC.pdf", "pages": "37"},
                {"documentId": "86092972", "name": "INCLUSIONS_LOT 0_SYNTHETIC.pdf", "pages": "15"},
                {"documentId": "3", "name": "PLANS_LOT 0_SYNTHETIC.pdf", "pages": "4"}],
            "recipients": {"signers": [
                {"roleName": "Buyer", "recipientId": "1", "routingOrder": "1"},
                {"roleName": "Builder", "recipientId": "3", "routingOrder": "2"}],
                "carbonCopies": [], "recipientCount": "2"}}


def nsw_company_template() -> dict:
    """Shaped like NSW Build _ Company: four documents, the prelim named EXECUTED-..."""
    return {"templateId": "tmpl-nsw-company", "name": "NSW Build _ Company",
            "documents": [
                {"documentId": "1", "name": "BUILD CONTRACT_LOT 0_SYNTHETIC.pdf", "pages": "45"},
                {"documentId": "2", "name": "INCLUSIONS_LOT 0_SYNTHETIC.pdf", "pages": "18"},
                {"documentId": "4", "name": "EXECUTED-PRELIMINARY AGREEMENT_LOT 0.pdf", "pages": "3"},
                {"documentId": "3", "name": "PLANS_LOT 0_SYNTHETIC.pdf", "pages": "5"}],
            "recipients": {"signers": [
                {"roleName": "Buyer - Company Guarantor", "recipientId": "1", "routingOrder": "1"},
                {"roleName": "Builder", "recipientId": "2", "routingOrder": "2"},
                {"roleName": "Builder Witness", "recipientId": "3", "routingOrder": "3"},
                {"roleName": "Date Contract", "recipientId": "4", "routingOrder": "4"}]}}
```

- [ ] **Step 2: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_draft.py`:

```python
"""Request building: kinds, template, recipients, carry or flag, size, duplicates, body."""
import base64
import os
import tempfile
import unittest
from unittest.mock import patch

from docusign_upload import draft
from docusign_upload.draft import Stop
from docusign_upload.pdfcheck import PdfFile
from support import make_pdf, nsw_company_template, qld_single_template


def pdf(name, pages, size=1000):
    return PdfFile(path="/synthetic/" + name, name=name, bytes=size, pages=pages)


def build_plan(folder):
    """A QLD Single Buyer plan over real synthetic PDFs: contract and inclusions carry, plans flag."""
    template = draft.parse_template(qld_single_template())
    files = []
    for kind, pages in (("BUILD CONTRACT", 37), ("INCLUSIONS", 15), ("PLANS", 5)):
        name = f"{kind}_LOT 1_TESTVILLE_EXAMPLE.pdf"
        path = make_pdf(os.path.join(folder, name), pages)
        files.append((kind, PdfFile(path=path, name=name, bytes=os.path.getsize(path), pages=pages)))
    sent = draft.check_recipients(
        [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}], template)
    return draft.Plan(template, sent, draft.plan_documents(files, template),
                      "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE", "Dear Alex,", "00001")


class KindAndTemplateTests(unittest.TestCase):
    def test_kind_of_matches_by_name(self):
        self.assertEqual(draft.kind_of("BUILD CONTRACT _LOT 0_SYNTHETIC.pdf"), "BUILD CONTRACT")
        self.assertEqual(draft.kind_of("EXECUTED-PRELIMINARY AGREEMENT_LOT 0.pdf"), "PRELIMINARY AGREEMENT")
        self.assertEqual(draft.kind_of("plans_lot 0.pdf"), "PLANS")
        self.assertIsNone(draft.kind_of("SITE PHOTOS.pdf"))
        self.assertIsNone(draft.kind_of("INCLUSIONS AND PLANS.pdf"))

    def test_pick_template_is_exact_after_trimming(self):
        found = [{"name": "QLD Build _ Single Buyer (old)"}, {"name": "QLD Build _ Single Buyer "}]
        self.assertEqual(draft.pick_template(found, "QLD Build _ Single Buyer")["name"],
                         "QLD Build _ Single Buyer ")

    def test_pick_template_stops_on_zero_or_several(self):
        with self.assertRaisesRegex(Stop, "matched 0 templates.*QLD Build _ 2 Buyer"):
            draft.pick_template([{"name": "QLD Build _ 2 Buyer"}], "QLD Build _ 2 Buyers")
        with self.assertRaisesRegex(Stop, "matched 2 templates"):
            draft.pick_template([{"name": "X "}, {"name": " X"}], "X")
        with self.assertRaisesRegex(Stop, "nothing"):
            draft.pick_template([], "X")

    def test_parse_template_reads_documents_and_roles(self):
        t = draft.parse_template(nsw_company_template())
        self.assertEqual(t.name, "NSW Build _ Company")
        self.assertEqual([(d.kind, d.document_id, d.pages) for d in t.documents],
                         [("BUILD CONTRACT", "1", 45), ("INCLUSIONS", "2", 18),
                          ("PRELIMINARY AGREEMENT", "4", 3), ("PLANS", "3", 5)])
        self.assertIn(draft.TemplateRole("Builder", "2", "2", "signers"), t.roles)

    def test_an_unknown_template_document_stops_without_naming_it(self):
        raw = qld_single_template()
        raw["documents"].append({"documentId": "77", "name": "SITE PHOTOS_SOMEONE.pdf", "pages": "2"})
        with self.assertRaises(Stop) as cm:
            draft.parse_template(raw)
        self.assertIn("77", str(cm.exception))
        self.assertNotIn("SOMEONE", str(cm.exception))

    def test_a_repeated_template_kind_stops(self):
        raw = qld_single_template()
        raw["documents"].append({"documentId": "78", "name": "PLANS_SECOND.pdf", "pages": "2"})
        with self.assertRaisesRegex(Stop, "more than one PLANS"):
            draft.parse_template(raw)


class ArgumentTests(unittest.TestCase):
    def setUp(self):
        self.template = draft.parse_template(qld_single_template())

    def test_text_args(self):
        draft.check_text_args("26045", "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE",
                              "Dear Alex,")
        for job_no in ("", "00001&status=any", "26045 ", "x" * 21):
            with self.subTest(job_no=job_no), self.assertRaisesRegex(Stop, "job_no"):
                draft.check_text_args(job_no, "s", "b")
        with self.assertRaisesRegex(Stop, "email_subject is empty"):
            draft.check_text_args("1", "  ", "b")
        with self.assertRaisesRegex(Stop, "allows 100"):
            draft.check_text_args("1", "s" * 101, "b")
        with self.assertRaisesRegex(Stop, "allows 10000"):
            draft.check_text_args("1", "s", "b" * 10001)

    def test_kinds(self):
        self.assertEqual(draft.check_kinds([" build contract", "Plans"]), ["BUILD CONTRACT", "PLANS"])
        with self.assertRaisesRegex(Stop, "unknown document kind: SPEC"):
            draft.check_kinds(["BUILD CONTRACT", "SPEC"])
        with self.assertRaisesRegex(Stop, "given twice: PLANS"):
            draft.check_kinds(["BUILD CONTRACT", "PLANS", "plans"])
        with self.assertRaisesRegex(Stop, "no BUILD CONTRACT"):
            draft.check_kinds(["INCLUSIONS"])

    def test_recipients_take_the_template_ids(self):
        (r, t), = draft.check_recipients(
            [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}], self.template)
        self.assertEqual((r.role, r.name, t.recipient_id, t.routing_order),
                         ("Buyer", "Alex EXAMPLE", "1", "1"))

    def test_role_case_mismatch_stops_with_the_role_list(self):
        # QLD 2 Buyer spells its first role "BUYER 1" and NSW "Buyer 1": no silent second recipient
        with self.assertRaises(Stop) as cm:
            draft.check_recipients([{"role": "buyer", "name": "A", "email": "a@example.com"}],
                                   self.template)
        self.assertIn("Builder, Buyer", str(cm.exception))
        self.assertIn("capitals", str(cm.exception))

    def test_recipient_stops(self):
        raw = qld_single_template()
        raw["recipients"]["carbonCopies"] = [{"roleName": "Office copy", "recipientId": "9",
                                              "routingOrder": "3"}]
        template = draft.parse_template(raw)
        one = {"role": "Buyer", "name": "A", "email": "a@example.com"}
        cases = [
            ([], "no recipients"),
            ([one, one], "given twice"),
            ([dict(one, role="Office copy")], "not a signer"),
            ([dict(one, name=" ")], "has no name"),
            ([dict(one, email="not-an-email")], "malformed email"),
        ]
        for recipients, needle in cases:
            with self.subTest(needle=needle), self.assertRaisesRegex(Stop, needle):
                draft.check_recipients(recipients, template)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.qld = draft.parse_template(qld_single_template())

    def test_carry_when_pages_match_and_flag_otherwise_in_envelope_order(self):
        files = [("PLANS", pdf("PLANS_X.pdf", 5)), ("BUILD CONTRACT", pdf("BUILD CONTRACT_X.pdf", 37)),
                 ("INCLUSIONS", pdf("INCLUSIONS_X.pdf", 15)),
                 ("PRELIMINARY AGREEMENT", pdf("PRELIMINARY AGREEMENT_X.pdf", 3))]
        planned = draft.plan_documents(files, self.qld)
        self.assertEqual([(d.kind, d.carry, d.template_document_id) for d in planned],
                         [("BUILD CONTRACT", True, "1"), ("INCLUSIONS", True, "86092972"),
                          ("PRELIMINARY AGREEMENT", False, None), ("PLANS", False, "3")])
        self.assertEqual(planned[2].reason, "the template has no PRELIMINARY AGREEMENT document")
        self.assertEqual(planned[3].reason, "5 pages, the template's has 4")

    def test_the_contract_must_carry(self):
        with self.assertRaisesRegex(Stop, "BUILD CONTRACT: 36 pages, the template's has 37.*fixed form"):
            draft.plan_documents([("BUILD CONTRACT", pdf("B.pdf", 36))], self.qld)
        with self.assertRaisesRegex(Stop, "no BUILD CONTRACT"):
            draft.plan_documents([("PLANS", pdf("P.pdf", 4))], self.qld)

    def test_size_limit_names_the_largest_document(self):
        planned = draft.plan_documents([("BUILD CONTRACT", pdf("B.pdf", 37, size=3_000_000)),
                                        ("PLANS", pdf("P.pdf", 4, size=9_000_000))], self.qld)
        draft.check_size(planned)
        with patch.object(draft, "MAX_BODY_BYTES", 10_000_000):
            with self.assertRaisesRegex(Stop, "largest: PLANS"):
                draft.check_size(planned)

    def test_find_duplicate(self):
        def env(status, value="26045", fields=True):
            e = {"envelopeId": f"env-{status}", "status": status}
            if fields:
                e["customFields"] = {"textCustomFields": [{"name": "JobNo", "value": value}]}
            return e
        self.assertIsNone(draft.find_duplicate([env("voided"), env("Declined"), env("deleted")], "26045"))
        self.assertEqual(draft.find_duplicate([env("voided"), env("created")], "26045")["envelopeId"],
                         "env-created")
        self.assertIsNone(draft.find_duplicate([env("sent", value="26046")], "26045"))
        self.assertEqual(draft.find_duplicate([env("sent", fields=False)], "26045")["envelopeId"],
                         "env-sent")


class BodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plan = build_plan(self.tmp.name)
        self.body = draft.build_body(self.plan)

    def test_top_level(self):
        self.assertEqual(self.body["status"], "created")
        self.assertEqual(set(self.body), {"status", "emailSubject", "emailBlurb", "compositeTemplates"})

    def test_carried_documents_replace_the_template_documents(self):
        c1, c2, _ = self.body["compositeTemplates"]
        self.assertEqual(c1["serverTemplates"], [{"sequence": "1", "templateId": "tmpl-qld-single"}])
        self.assertEqual(c1["inlineTemplates"][0]["sequence"], "2")
        self.assertEqual((c1["document"]["documentId"], c2["document"]["documentId"]), ("1", "86092972"))
        self.assertEqual((c1["document"]["name"], c1["document"]["fileExtension"]),
                         ("BUILD CONTRACT_LOT 1_TESTVILLE_EXAMPLE.pdf", "pdf"))
        with open(self.plan.documents[0].file.path, "rb") as fh:
            self.assertEqual(base64.b64decode(c1["document"]["documentBase64"]), fh.read())

    def test_a_flagged_document_has_no_server_template_and_a_fresh_id(self):
        c3 = self.body["compositeTemplates"][2]
        self.assertNotIn("serverTemplates", c3)
        self.assertEqual(c3["inlineTemplates"][0]["sequence"], "1")
        self.assertEqual(c3["document"]["documentId"], "9001")

    def test_buyers_only_and_job_no_in_the_first_inline_template(self):
        for comp in self.body["compositeTemplates"]:
            self.assertEqual(comp["inlineTemplates"][0]["recipients"]["signers"],
                             [{"recipientId": "1", "roleName": "Buyer", "routingOrder": "1",
                               "name": "Alex EXAMPLE", "email": "alex@example.com"}])
        first, *rest = self.body["compositeTemplates"]
        self.assertEqual(first["inlineTemplates"][0]["customFields"]["textCustomFields"],
                         [{"name": "JobNo", "value": "00001", "show": "false", "required": "false"}])
        self.assertTrue(all("customFields" not in c["inlineTemplates"][0] for c in rest))

    def test_plan_view(self):
        view = draft.plan_view(self.plan)
        self.assertEqual(view["roles_left_as_template_defaults"], ["Builder"])
        self.assertEqual([d["tabs"] for d in view["documents"]],
                         ["carried from the template", "carried from the template",
                          "none, flagged: 5 pages, the template's has 4"])
        self.assertEqual((view["template_documents_left_out"], view["status"]), ([], "created"))
```

- [ ] **Step 3: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_draft.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'docusign_upload.draft'`.

- [ ] **Step 4: Write `draft.py`**

`shared/mcp/docusign-upload/docusign_upload/draft.py`:

```python
"""From the tool's arguments and the template to the request, and back.

Plain functions, no network. Argument checks, template parsing, recipient
checks, the carry-or-flag plan, the size and duplicate checks and the request
body are here; the read-back findings follow at the end of the module.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pdfcheck import PdfFile

DRAFT_STATUS = "created"  # the only status this server ever sends
KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")  # envelope order
MAX_BODY_BYTES = 30 * 1024 * 1024
BODY_OVERHEAD_BYTES = 64 * 1024
SUBJECT_MAX = 100
BLURB_MAX = 10000
JOB_NO_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEAD_STATUSES = {"voided", "declined", "deleted"}
FRESH_ID_START = 9001


class Stop(Exception):
    """A stop condition: nothing is created, and the message says why."""


@dataclass(frozen=True)
class TemplateDoc:
    document_id: str
    kind: str
    pages: int


@dataclass(frozen=True)
class TemplateRole:
    role: str
    recipient_id: str
    routing_order: str
    recipient_type: str


@dataclass(frozen=True)
class Template:
    template_id: str
    name: str
    documents: tuple[TemplateDoc, ...]
    roles: tuple[TemplateRole, ...]


@dataclass(frozen=True)
class Recipient:
    role: str
    name: str
    email: str


@dataclass(frozen=True)
class PlannedDoc:
    kind: str
    file: PdfFile
    carry: bool
    template_document_id: str | None
    reason: str


@dataclass(frozen=True)
class Plan:
    template: Template
    recipients: tuple[tuple[Recipient, TemplateRole], ...]
    documents: tuple[PlannedDoc, ...]
    email_subject: str
    email_blurb: str
    job_no: str


def check_text_args(job_no: str, email_subject: str, email_blurb: str) -> None:
    if not JOB_NO_RE.match(str(job_no)):
        raise Stop("job_no must be 1 to 20 letters, digits or hyphens; it is used in the "
                   "duplicate search")
    if not str(email_subject).strip():
        raise Stop("email_subject is empty")
    if len(email_subject) > SUBJECT_MAX:
        raise Stop(f"email_subject has {len(email_subject)} characters; DocuSign allows {SUBJECT_MAX}")
    if len(email_blurb) > BLURB_MAX:
        raise Stop(f"email_blurb has {len(email_blurb)} characters; DocuSign allows {BLURB_MAX}")


def check_kinds(kinds: list[str]) -> list[str]:
    """The kinds normalised to capitals, in the order given. Stops on unknown or repeated kinds."""
    norm = [str(k).strip().upper() for k in kinds]
    unknown = sorted({k for k in norm if k not in KINDS})
    if unknown:
        raise Stop(f"unknown document kind: {', '.join(unknown)}. Use {', '.join(KINDS)}")
    twice = sorted({k for k in norm if norm.count(k) > 1})
    if twice:
        raise Stop(f"document kind given twice: {', '.join(twice)}")
    if "BUILD CONTRACT" not in norm:
        raise Stop("no BUILD CONTRACT document; the draft needs the job's build contract")
    return norm


def kind_of(document_name: str) -> str | None:
    """The one kind whose words appear in a template document's name, else None."""
    up = str(document_name).upper()
    hits = [k for k in KINDS if k in up]
    return hits[0] if len(hits) == 1 else None


def pick_template(candidates: list[dict[str, Any]], wanted: str) -> dict[str, Any]:
    """The one template whose name, trimmed, equals the wanted name, trimmed."""
    target = wanted.strip()
    hits = [t for t in candidates if str(t.get("name", "")).strip() == target]
    if len(hits) != 1:
        names = sorted({str(t.get("name", "")).strip() for t in candidates})
        raise Stop(f"template {target!r} matched {len(hits)} templates; the search returned: "
                   f"{', '.join(names) if names else 'nothing'}")
    return hits[0]


def parse_template(raw: dict[str, Any]) -> Template:
    """Documents by kind (name match, never id or order) and roles. Never echoes a document name."""
    documents = []
    for d in raw.get("documents") or []:
        kind = kind_of(d.get("name", ""))
        if kind is None:
            raise Stop(f"template document {d.get('documentId')} is not one of {', '.join(KINDS)}; "
                       "the template has changed and a person needs to look")
        documents.append(TemplateDoc(str(d.get("documentId")), kind, int(d.get("pages") or 0)))
    kinds = [d.kind for d in documents]
    twice = sorted({k for k in kinds if kinds.count(k) > 1})
    if twice:
        raise Stop(f"the template holds more than one {', '.join(twice)} document; a person needs to look")
    roles = []
    for recipient_type, items in (raw.get("recipients") or {}).items():
        if not isinstance(items, list):
            continue
        for r in items:
            if r.get("roleName"):
                roles.append(TemplateRole(str(r["roleName"]), str(r.get("recipientId", "")),
                                          str(r.get("routingOrder", "")), recipient_type))
    return Template(str(raw.get("templateId", "")), str(raw.get("name", "")).strip(),
                    tuple(documents), tuple(roles))


def check_recipients(raw: list[dict[str, str]],
                     template: Template) -> tuple[tuple[Recipient, TemplateRole], ...]:
    """Each buyer role must be a signer role on the template, named exactly (capitals included)."""
    if not raw:
        raise Stop("no recipients given; the draft needs at least one buyer role")
    by_role = {r.role: r for r in template.roles}
    seen: set[str] = set()
    out = []
    for item in raw:
        role = str(item.get("role", ""))
        name = str(item.get("name", "")).strip()
        email = str(item.get("email", "")).strip()
        if role in seen:
            raise Stop(f"role {role!r} is given twice")
        seen.add(role)
        trole = by_role.get(role)
        if trole is None:
            raise Stop(f"role {role!r} is not on template {template.name!r}; its roles are: "
                       f"{', '.join(sorted(by_role))}. Role names match exactly, capitals included")
        if trole.recipient_type != "signers":
            raise Stop(f"role {role!r} is not a signer on the template")
        if not name:
            raise Stop(f"role {role!r} has no name")
        if not EMAIL_RE.match(email):
            raise Stop(f"role {role!r} has a malformed email address")
        out.append((Recipient(role, name, email), trole))
    return tuple(out)


def plan_documents(files: list[tuple[str, PdfFile]], template: Template) -> tuple[PlannedDoc, ...]:
    """Carry or flag each job document, in envelope order. The build contract must carry."""
    by_kind = {d.kind: d for d in template.documents}
    given = dict(files)
    planned = []
    for kind in KINDS:
        f = given.get(kind)
        if f is None:
            continue
        tdoc = by_kind.get(kind)
        if tdoc is None:
            planned.append(PlannedDoc(kind, f, False, None, f"the template has no {kind} document"))
        elif tdoc.pages != f.pages:
            planned.append(PlannedDoc(kind, f, False, tdoc.document_id,
                                      f"{f.pages} pages, the template's has {tdoc.pages}"))
        else:
            planned.append(PlannedDoc(kind, f, True, tdoc.document_id, ""))
    if not planned or planned[0].kind != "BUILD CONTRACT":
        raise Stop("no BUILD CONTRACT document; the draft needs the job's build contract")
    if not planned[0].carry:
        raise Stop(f"BUILD CONTRACT: {planned[0].reason}. The contract is a fixed form, so a "
                   "different page count means its layout changed; a person checks the fill")
    return tuple(planned)


def estimated_body_bytes(documents: tuple[PlannedDoc, ...]) -> int:
    return BODY_OVERHEAD_BYTES + sum(4 * ((d.file.bytes + 2) // 3) for d in documents)


def check_size(documents: tuple[PlannedDoc, ...]) -> None:
    estimate = estimated_body_bytes(documents)
    if estimate > MAX_BODY_BYTES:
        biggest = max(documents, key=lambda d: d.file.bytes)
        raise Stop(f"the request would be about {estimate / 1048576:.1f} MiB, over the "
                   f"{MAX_BODY_BYTES / 1048576:.0f} MiB limit (largest: {biggest.kind}, "
                   f"{biggest.file.bytes / 1048576:.1f} MB)")


def find_duplicate(envelopes: list[dict[str, Any]], job_no: str) -> dict[str, Any] | None:
    """The first live envelope carrying this JobNo. One whose custom fields did not come back
    counts as a match: the search already filtered on JobNo, and missing a duplicate is worse."""
    for env in envelopes:
        if str(env.get("status", "")).lower() in DEAD_STATUSES:
            continue
        fields = (env.get("customFields") or {}).get("textCustomFields")
        if fields is None or any(f.get("name") == "JobNo" and str(f.get("value", "")).strip() == job_no
                                 for f in fields):
            return env
    return None


def _fresh_ids(template: Template, count: int) -> list[str]:
    used = {d.document_id for d in template.documents}
    ids, n = [], FRESH_ID_START
    while len(ids) < count:
        if str(n) not in used:
            ids.append(str(n))
        n += 1
    return ids


def build_body(plan: Plan) -> dict[str, Any]:
    """The Envelopes:create body. Reads each PDF now, after every check has passed."""
    signers = [{"recipientId": t.recipient_id, "roleName": r.role, "routingOrder": t.routing_order,
                "name": r.name, "email": r.email} for r, t in plan.recipients]
    fresh = iter(_fresh_ids(plan.template, sum(1 for d in plan.documents if not d.carry)))
    composites: list[dict[str, Any]] = []
    for n, d in enumerate(plan.documents, start=1):
        document = {"documentId": d.template_document_id if d.carry else next(fresh),
                    "name": d.file.name, "fileExtension": "pdf",
                    "documentBase64": base64.b64encode(Path(d.file.path).read_bytes()).decode("ascii")}
        recipients = {"signers": [dict(s) for s in signers]}
        if d.carry:
            composites.append({
                "compositeTemplateId": str(n),
                "serverTemplates": [{"sequence": "1", "templateId": plan.template.template_id}],
                "inlineTemplates": [{"sequence": "2", "recipients": recipients}],
                "document": document})
        else:
            composites.append({
                "compositeTemplateId": str(n),
                "inlineTemplates": [{"sequence": "1", "recipients": recipients}],
                "document": document})
    # With composites, envelope custom fields belong in an inline template (root ones are ignored).
    composites[0]["inlineTemplates"][0]["customFields"] = {"textCustomFields": [
        {"name": "JobNo", "value": plan.job_no, "show": "false", "required": "false"}]}
    return {"status": DRAFT_STATUS, "emailSubject": plan.email_subject,
            "emailBlurb": plan.email_blurb, "compositeTemplates": composites}


def plan_view(plan: Plan) -> dict[str, Any]:
    """What the preview shows and the create repeats: everything a person approves."""
    sent_roles = {r.role for r, _ in plan.recipients}
    given_kinds = {d.kind for d in plan.documents}
    return {
        "template": plan.template.name,
        "status": DRAFT_STATUS,
        "job_no": plan.job_no,
        "email_subject": plan.email_subject,
        "recipients_set": [{"role": r.role, "name": r.name, "email": r.email} for r, _ in plan.recipients],
        "roles_left_as_template_defaults": [t.role for t in plan.template.roles if t.role not in sent_roles],
        "documents": [{"kind": d.kind, "file": d.file.name, "pages": d.file.pages,
                       "tabs": "carried from the template" if d.carry else f"none, flagged: {d.reason}"}
                      for d in plan.documents],
        "template_documents_left_out": [d.kind for d in plan.template.documents
                                        if d.kind not in given_kinds],
        "estimated_request_mib": round(estimated_body_bytes(plan.documents) / 1048576, 1),
    }
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_draft.py' -v`
Expected: `Ran 20 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/draft.py shared/mcp/docusign-upload/tests/support.py shared/mcp/docusign-upload/tests/test_draft.py
git commit -m "docusign-upload: request building (template by trimmed name, exact roles, carry or flag, size, duplicates, composite body)"
```

---

### Task 5: Read-back findings

**Files:**
- Modify: `shared/mcp/docusign-upload/docusign_upload/draft.py` (append)
- Modify: `shared/mcp/docusign-upload/tests/support.py` (append `qld_single_template_tabs`, `readback_for`)
- Modify: `shared/mcp/docusign-upload/tests/test_draft.py` (append `ReadBackTests`)

**Interfaces:**
- Consumes: `Plan`, `PlannedDoc`, `DRAFT_STATUS`, `build_body` (Task 4).
- Produces:
  - `tab_counts(recipients: dict) -> dict[str, dict[tuple[str, int], int]]` (`{documentId: {(roleName, page): count}}`)
  - `read_back(plan: Plan, *, envelope: dict, documents: dict, recipients: dict, custom_fields: dict, template_tabs: dict) -> dict` with keys `documents` (list), `roles_without_tabs` (list), `findings` (list of str), `check` (str)
  - `tests/support.py`: `qld_single_template_tabs() -> dict`, `readback_for(body: dict, template_tabs: dict) -> dict` with keys `documents`, `recipients`, `custom_fields`

- [ ] **Step 1: Append the fixtures to `tests/support.py`**

```python
def qld_single_template_tabs() -> dict:
    """The template's tabs, shaped like GET /templates/{id}/recipients?include_tabs=true.
    Same pattern as the real template: contract initials and signatures, inclusions initials
    on all but the last three pages, a plans signature on every page."""
    def tabs(doc, pages):
        return [{"documentId": doc, "pageNumber": str(p)} for p in pages]
    return {"signers": [
        {"roleName": "Buyer", "recipientId": "1", "routingOrder": "1", "tabs": {
            "signHereTabs": tabs("1", [3, 13]) + tabs("86092972", [13, 14, 15]) + tabs("3", [1, 2, 3, 4]),
            "initialHereTabs": tabs("1", range(6, 13)) + tabs("86092972", range(1, 13))}},
        {"roleName": "Builder", "recipientId": "3", "routingOrder": "2", "tabs": {
            "signHereTabs": tabs("1", [13]) + tabs("86092972", [13])}}],
        "recipientCount": "2"}


def readback_for(body: dict, template_tabs: dict) -> dict:
    """What DocuSign is expected to hold after the create: one document per composite (ids
    renumbered), the template's tabs on each carried document, each role once. The sandbox
    prototype checks the real service against the same expectation."""
    by_template_doc: dict[str, list[tuple[str, str, str]]] = {}
    for signer in template_tabs.get("signers", []):
        for tab_type, tabs in (signer.get("tabs") or {}).items():
            for tab in tabs:
                by_template_doc.setdefault(str(tab["documentId"]), []).append(
                    (signer["roleName"], tab_type, str(tab["pageNumber"])))
    roles = {s["roleName"]: {"roleName": s["roleName"], "recipientId": s["recipientId"],
                             "email": "builder@example.com", "tabs": {}}
             for s in template_tabs.get("signers", [])}
    documents = []
    for n, comp in enumerate(body["compositeTemplates"], start=1):
        doc = comp["document"]
        new_id = str(n)
        documents.append({"documentId": new_id, "name": doc["name"], "type": "content"})
        for signer in comp["inlineTemplates"][0]["recipients"]["signers"]:
            roles[signer["roleName"]]["email"] = signer["email"]
        if comp.get("serverTemplates"):
            for role, tab_type, page in by_template_doc.get(doc["documentId"], []):
                roles[role]["tabs"].setdefault(tab_type, []).append(
                    {"documentId": new_id, "pageNumber": page})
    custom = body["compositeTemplates"][0]["inlineTemplates"][0].get("customFields", {})
    return {"documents": {"envelopeDocuments": documents},
            "recipients": {"signers": list(roles.values()), "recipientCount": str(len(roles))},
            "custom_fields": custom}
```

- [ ] **Step 2: Write the failing tests**

Add `import copy` to the imports at the top of `tests/test_draft.py`, change the `from support import ...` line to `from support import make_pdf, nsw_company_template, qld_single_template, qld_single_template_tabs, readback_for`, and append:

```python
class ReadBackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.plan = build_plan(self.tmp.name)
        self.rb = readback_for(draft.build_body(self.plan), qld_single_template_tabs())
        self.template_tabs = draft.tab_counts(qld_single_template_tabs())

    def check(self, **overrides):
        parts = {"envelope": {"status": "created"}, "documents": self.rb["documents"],
                 "recipients": self.rb["recipients"], "custom_fields": self.rb["custom_fields"]}
        parts.update(overrides)
        return draft.read_back(self.plan, template_tabs=self.template_tabs, **parts)

    def test_tab_counts(self):
        counts = draft.tab_counts({"signers": [{"roleName": "Buyer", "tabs": {
            "signHereTabs": [{"documentId": "1", "pageNumber": "3"}, {"documentId": "1", "pageNumber": "3"}],
            "initialHereTabs": [{"documentId": "2", "pageNumber": "1"}]}}], "recipientCount": "1"})
        self.assertEqual(counts, {"1": {("Buyer", 3): 2}, "2": {("Buyer", 1): 1}})

    def test_a_draft_that_matches_the_plan_has_no_findings(self):
        out = self.check()
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["check"], "the draft matches the plan")
        self.assertEqual([(d["kind"], d["tabs"]) for d in out["documents"]],
                         [("BUILD CONTRACT", "carried"), ("INCLUSIONS", "carried"),
                          ("PLANS", "none, flagged")])
        self.assertEqual(out["documents"][1]["tab_pages_by_role"]["Builder"], [13])
        self.assertEqual(out["roles_without_tabs"], [])

    def test_findings(self):
        docs = self.rb["documents"]["envelopeDocuments"]
        signers = self.rb["recipients"]["signers"]
        tagged_plans = copy.deepcopy(self.rb["recipients"])
        tagged_plans["signers"][0]["tabs"].setdefault("signHereTabs", []).append(
            {"documentId": "3", "pageNumber": "1"})
        cases = [
            ({"envelope": {"status": "sent"}}, "status is 'sent'"),
            ({"documents": {"envelopeDocuments": docs + [
                {"documentId": "9", "name": "PLANS_PAST JOB.pdf", "type": "content"}]}},
             "not one of the job's files (id 9)"),
            ({"documents": {"envelopeDocuments": docs[:2]}}, "PLANS: not in the draft"),
            ({"recipients": {"signers": signers + [
                {"roleName": "Buyer", "email": "alex@example.com", "tabs": {}}]}},
             "role 'Buyer' appears 2 times"),
            ({"recipients": {"signers": [dict(s, email="someone@example.com") if s["roleName"] == "Buyer"
                                         else s for s in signers]}}, "different email"),
            ({"recipients": tagged_plans}, "PLANS: 1 tabs in the draft, expected 0"),
            ({"custom_fields": {"textCustomFields": []}}, "JobNo"),
        ]
        for overrides, needle in cases:
            with self.subTest(needle=needle):
                out = self.check(**overrides)
                self.assertTrue(any(needle in f for f in out["findings"]), out["findings"])
                self.assertNotIn("PAST JOB", " ".join(out["findings"]))
                self.assertEqual(out["check"], "a person should look at the findings before sending")
```

- [ ] **Step 3: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_draft.py' -v`
Expected: the three new tests ERROR with `AttributeError: module 'docusign_upload.draft' has no attribute 'tab_counts'`; the Task 4 tests still pass.

- [ ] **Step 4: Append the read-back to `draft.py`**

```python
def tab_counts(recipients: dict[str, Any]) -> dict[str, dict[tuple[str, int], int]]:
    """{documentId: {(roleName, page): number of tabs}} across every recipient and tab type."""
    out: dict[str, dict[tuple[str, int], int]] = {}
    for items in (recipients or {}).values():
        if not isinstance(items, list):
            continue
        for r in items:
            role = str(r.get("roleName") or "(no role)")
            for tabs in (r.get("tabs") or {}).values():
                if not isinstance(tabs, list):
                    continue
                for tab in tabs:
                    doc = out.setdefault(str(tab.get("documentId", "")), {})
                    key = (role, int(tab.get("pageNumber") or 0))
                    doc[key] = doc.get(key, 0) + 1
    return out


def _pages_by_role(counts: dict[tuple[str, int], int]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for role, page in sorted(counts):
        pages = out.setdefault(role, [])
        if page not in pages:
            pages.append(page)
    return out


def _has_tabs(recipient: dict[str, Any]) -> bool:
    return any(isinstance(tabs, list) and tabs for tabs in (recipient.get("tabs") or {}).values())


def read_back(plan: Plan, *, envelope: dict[str, Any], documents: dict[str, Any],
              recipients: dict[str, Any], custom_fields: dict[str, Any],
              template_tabs: dict[str, dict[tuple[str, int], int]]) -> dict[str, Any]:
    """Compare the created draft with the plan. Findings are reported, never acted on: the draft
    exists and a person decides. Documents are matched by name because DocuSign renumbers ids."""
    findings: list[str] = []
    if envelope.get("status") != DRAFT_STATUS:
        findings.append(f"status is {envelope.get('status')!r}, expected {DRAFT_STATUS!r}")
    content = [d for d in documents.get("envelopeDocuments", []) if d.get("type", "content") == "content"]
    by_name = {str(d.get("name", "")).lower(): str(d.get("documentId")) for d in content}
    planned_names = {d.file.name.lower() for d in plan.documents}
    for d in content:
        if str(d.get("name", "")).lower() not in planned_names:
            findings.append("the draft holds a document that is not one of the job's files "
                            f"(id {d.get('documentId')})")
    counts = tab_counts(recipients)
    summary = []
    for d in plan.documents:
        doc_id = by_name.get(d.file.name.lower())
        if doc_id is None:
            findings.append(f"{d.kind}: not in the draft")
            continue
        got = counts.get(doc_id, {})
        expected = template_tabs.get(d.template_document_id or "", {}) if d.carry else {}
        if got != expected:
            findings.append(f"{d.kind}: {sum(got.values())} tabs in the draft, expected "
                            f"{sum(expected.values())}"
                            + (" from the template" if d.carry else " (flagged, so none)"))
        summary.append({"kind": d.kind, "file": d.file.name, "pages": d.file.pages,
                        "tabs": "carried" if d.carry else "none, flagged",
                        "flag": d.reason or None, "tab_count": sum(got.values()),
                        "tab_pages_by_role": _pages_by_role(got)})
    job = [f for f in custom_fields.get("textCustomFields", []) if f.get("name") == "JobNo"]
    if len(job) != 1 or str(job[0].get("value", "")) != plan.job_no:
        findings.append("the JobNo custom field is missing or wrong")
    by_role: dict[str, list[dict[str, Any]]] = {}
    for items in recipients.values():
        if isinstance(items, list):
            for r in items:
                by_role.setdefault(str(r.get("roleName") or "(no role)"), []).append(r)
    for r, _ in plan.recipients:
        found = by_role.get(r.role, [])
        if len(found) != 1:
            findings.append(f"role {r.role!r} appears {len(found)} times in the draft")
        elif str(found[0].get("email", "")).lower() != r.email.lower():
            findings.append(f"role {r.role!r} has a different email in the draft")
    without_tabs = sorted(role for role, items in by_role.items()
                          if not any(_has_tabs(x) for x in items))
    return {"documents": summary, "roles_without_tabs": without_tabs, "findings": findings,
            "check": ("the draft matches the plan" if not findings
                      else "a person should look at the findings before sending")}
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_draft.py' -v`
Expected: `Ran 23 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/draft.py shared/mcp/docusign-upload/tests/support.py shared/mcp/docusign-upload/tests/test_draft.py
git commit -m "docusign-upload: read-back findings (documents by name, tab counts against the template, roles, JobNo)"
```

---

### Task 6: The REST client and its fixed call list

**Files:**
- Create: `shared/mcp/docusign-upload/docusign_upload/client.py`
- Modify: `shared/mcp/docusign-upload/tests/support.py` (append `FakeDocuSign`)
- Test: `shared/mcp/docusign-upload/tests/test_client.py`

**Interfaces:**
- Consumes: `Config` (Task 1), `Authenticator`, `Session.account_url` (Task 2), `DRAFT_STATUS` (Task 4).
- Produces:
  - `LIVE_STATUSES = "created,sent,delivered,signed,completed,processing,timedout"`
  - `class DocuSignError(RuntimeError)` with `status: int | None`, `error_code: str | None`, `detail: str | None`
  - `class DocuSignClient(config: Config, http: httpx.AsyncClient | None = None)` with attribute `auth: Authenticator` and async methods `list_templates(search_text) -> list[dict]`, `template_recipients(template_id) -> dict`, `list_envelopes(from_date, custom_field) -> list[dict]`, `create_draft(body) -> dict`, `envelope(envelope_id) -> dict`, `envelope_documents(envelope_id) -> dict`, `envelope_recipients(envelope_id) -> dict`, `envelope_custom_fields(envelope_id) -> dict`, `aclose() -> None`
  - `tests/support.py`: `class FakeDocuSign` with `transport() -> httpx.MockTransport`, `calls() -> list[tuple[str, str]]`, and settable `existing: list[dict]`, `token_error: str | None`, `create_error: tuple[int, dict | str] | None`, `create_transport_error: bool`; it records `requests: list[httpx.Request]` and `created: dict | None`, and answers on the fixed envelope id `env-synthetic`

- [ ] **Step 1: Append `FakeDocuSign` to `tests/support.py`**

Add `import json` and `import httpx` beside the other imports at the top, and append:

```python
class FakeDocuSign:
    """httpx.MockTransport handler standing in for DocuSign: auth, templates, envelopes.
    Anything it does not know answers 404 NOT_IN_FAKE, so a stray call shows up in a test."""

    ENVELOPE_ID = "env-synthetic"

    def __init__(self, template: dict | None = None, template_tabs: dict | None = None):
        self.template = template or qld_single_template()
        self.template_tabs = template_tabs or qld_single_template_tabs()
        self.existing: list[dict] = []
        self.token_error: str | None = None
        self.create_error: tuple[int, dict | str] | None = None
        self.create_transport_error = False
        self.requests: list[httpx.Request] = []
        self.created: dict | None = None
        self.readback: dict | None = None

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def calls(self) -> list[tuple[str, str]]:
        return [(r.method, r.url.path) for r in self.requests]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        method, path, host = request.method, request.url.path, request.url.host
        if host == "account-d.docusign.com":
            if (method, path) == ("POST", "/oauth/token"):
                if self.token_error:
                    return httpx.Response(400, json={"error": self.token_error})
                return httpx.Response(200, json={"access_token": "synthetic-token",
                                                 "token_type": "Bearer", "expires_in": 3600})
            if (method, path) == ("GET", "/oauth/userinfo"):
                return httpx.Response(200, json={"name": "Synthetic User", "accounts": [
                    {"account_id": ACCOUNT, "account_name": "synthetic", "base_uri": BASE,
                     "is_default": True}]})
        if host == "demo.invalid":
            api = f"/restapi/v2.1/accounts/{ACCOUNT}"
            env = f"{api}/envelopes/{self.ENVELOPE_ID}"
            if (method, path) == ("GET", f"{api}/templates"):
                return httpx.Response(200, json={"envelopeTemplates": [self.template]})
            if (method, path) == ("GET", f"{api}/templates/{self.template['templateId']}/recipients"):
                return httpx.Response(200, json=self.template_tabs)
            if (method, path) == ("GET", f"{api}/envelopes"):
                return httpx.Response(200, json={"envelopes": self.existing})
            if (method, path) == ("POST", f"{api}/envelopes"):
                if self.create_transport_error:
                    raise httpx.ConnectError("synthetic transport failure", request=request)
                if self.create_error:
                    status, payload = self.create_error
                    if isinstance(payload, dict):
                        return httpx.Response(status, json=payload)
                    return httpx.Response(status, text=payload)
                self.created = json.loads(request.content)
                self.readback = readback_for(self.created, self.template_tabs)
                return httpx.Response(201, json={"envelopeId": self.ENVELOPE_ID, "status": "created",
                                                 "uri": f"/envelopes/{self.ENVELOPE_ID}"})
            if method == "GET" and self.readback is not None:
                if path == env:
                    return httpx.Response(200, json={"envelopeId": self.ENVELOPE_ID, "status": "created",
                                                     "emailSubject": self.created["emailSubject"]})
                if path == f"{env}/documents":
                    return httpx.Response(200, json=self.readback["documents"])
                if path == f"{env}/recipients":
                    return httpx.Response(200, json=self.readback["recipients"])
                if path == f"{env}/custom_fields":
                    return httpx.Response(200, json=self.readback["custom_fields"])
        return httpx.Response(404, json={"errorCode": "NOT_IN_FAKE", "message": f"{method} {path}"})
```

- [ ] **Step 2: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_client.py`:

```python
"""The client's fixed call list and its error handling."""
import inspect
import json
import re
import tempfile
import unittest

import httpx

from docusign_upload import client as client_module
from docusign_upload.client import DocuSignClient, DocuSignError
from support import FakeDocuSign, keypair, make_config, write_key


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fake = FakeDocuSign()
        self.client = DocuSignClient(make_config(write_key(self.tmp.name, keypair()[0])),
                                     httpx.AsyncClient(transport=self.fake.transport()))
        self.addAsyncCleanup(self.client.aclose)

    def last(self, method, suffix):
        return [r for r in self.fake.requests if r.method == method and r.url.path.endswith(suffix)][-1]

    async def test_list_templates_asks_for_documents_and_recipients(self):
        templates = await self.client.list_templates("QLD Build _ Single Buyer")
        self.assertEqual(templates[0]["templateId"], "tmpl-qld-single")
        request = self.last("GET", "/templates")
        self.assertEqual((request.url.params["search_text"], request.url.params["include"]),
                         ("QLD Build _ Single Buyer", "documents,recipients"))
        self.assertEqual(request.headers["Authorization"], "Bearer synthetic-token")

    async def test_template_recipients_include_tabs(self):
        data = await self.client.template_recipients("tmpl-qld-single")
        self.assertIn("signers", data)
        self.assertEqual(self.last("GET", "/recipients").url.params["include_tabs"], "true")

    async def test_list_envelopes_filters_on_job_no_and_live_statuses(self):
        await self.client.list_envelopes("2026-04-16", "JobNo=00001")
        params = self.last("GET", "/envelopes").url.params
        self.assertEqual((params["from_date"], params["custom_field"], params["include"]),
                         ("2026-04-16", "JobNo=00001", "custom_fields"))
        self.assertEqual(params["status"], "created,sent,delivered,signed,completed,processing,timedout")

    async def test_create_draft_refuses_any_other_status_without_a_call(self):
        for status in ("sent", "Created", None):
            with self.subTest(status=status), self.assertRaisesRegex(DocuSignError, "only creates drafts"):
                await self.client.create_draft({"status": status, "compositeTemplates": []})
        self.assertEqual(self.fake.requests, [])

    async def test_create_draft_posts_with_merge_roles_on_draft(self):
        body = {"status": "created", "emailSubject": "s", "emailBlurb": "b", "compositeTemplates": [
            {"compositeTemplateId": "1",
             "inlineTemplates": [{"sequence": "1", "recipients": {"signers": []},
                                  "customFields": {"textCustomFields": []}}],
             "document": {"documentId": "1", "name": "B.pdf", "fileExtension": "pdf",
                          "documentBase64": ""}}]}
        out = await self.client.create_draft(body)
        self.assertEqual(out["envelopeId"], "env-synthetic")
        post = self.last("POST", "/envelopes")
        self.assertEqual(post.url.params["merge_roles_on_draft"], "true")
        self.assertEqual(json.loads(post.content)["status"], "created")

    async def test_docusign_errors_carry_code_and_message(self):
        self.fake.create_error = (400, {"errorCode": "INVALID_REQUEST_BODY", "message": "Synthetic."})
        with self.assertRaises(DocuSignError) as cm:
            await self.client.create_draft({"status": "created", "compositeTemplates": []})
        self.assertEqual((cm.exception.status, cm.exception.error_code, cm.exception.detail),
                         (400, "INVALID_REQUEST_BODY", "Synthetic."))

    async def test_a_non_json_error_body_does_not_crash(self):
        self.fake.create_error = (502, "<html><body>Bad gateway</body></html>")
        with self.assertRaises(DocuSignError) as cm:
            await self.client.create_draft({"status": "created", "compositeTemplates": []})
        self.assertEqual((cm.exception.status, cm.exception.error_code), (502, None))

    def test_the_client_has_no_call_that_could_send_or_change_an_envelope(self):
        source = inspect.getsource(client_module)
        self.assertIsNone(re.search(r"\.(put|patch|delete|request|send)\(", source))
        public = {n for n in dir(DocuSignClient) if not n.startswith("_")}
        self.assertEqual(public, {"aclose", "create_draft", "envelope", "envelope_custom_fields",
                                  "envelope_documents", "envelope_recipients", "list_envelopes",
                                  "list_templates", "template_recipients"})
```

- [ ] **Step 3: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_client.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'docusign_upload.client'`.

- [ ] **Step 4: Write `client.py`**

`shared/mcp/docusign-upload/docusign_upload/client.py`:

```python
"""The only DocuSign calls this server can make.

Reads: the template list (with documents and recipients), one template's
recipients with tabs, the envelope list for the duplicate check, and one
envelope's status, documents, recipients with tabs and custom fields. One
write: create an envelope, and only with status "created". There is no PUT,
PATCH or DELETE and no generic request method, so nothing here can send, void,
correct or delete an envelope.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .auth import Authenticator
from .config import Config
from .draft import DRAFT_STATUS

# Every status except voided, declined and deleted: a live envelope for the job blocks a new draft.
LIVE_STATUSES = "created,sent,delivered,signed,completed,processing,timedout"


class DocuSignError(RuntimeError):
    """A DocuSign call failed. Carries DocuSign's own errorCode and message when it sent them."""

    def __init__(self, message: str, *, status: int | None = None, error_code: str | None = None,
                 detail: str | None = None):
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.detail = detail


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _result(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if not resp.is_success:
        raise DocuSignError(f"DocuSign returned {resp.status_code}.", status=resp.status_code,
                            error_code=data.get("errorCode"), detail=data.get("message"))
    return data


class DocuSignClient:
    def __init__(self, config: Config, http: httpx.AsyncClient | None = None):
        self.config = config
        self.http = http or httpx.AsyncClient(timeout=config.timeout)
        self.auth = Authenticator(config, self.http)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        session = await self.auth.session()
        resp = await self.http.get(session.account_url(self.config.account_id) + path,
                                   params=params, headers=_headers(session.access_token))
        return _result(resp)

    async def list_templates(self, search_text: str) -> list[dict[str, Any]]:
        data = await self._get("/templates", {"search_text": search_text,
                                              "include": "documents,recipients"})
        return list(data.get("envelopeTemplates") or [])

    async def template_recipients(self, template_id: str) -> dict[str, Any]:
        return await self._get(f"/templates/{quote(template_id, safe='')}/recipients",
                               {"include_tabs": "true"})

    async def list_envelopes(self, from_date: str, custom_field: str) -> list[dict[str, Any]]:
        data = await self._get("/envelopes", {"from_date": from_date, "custom_field": custom_field,
                                              "status": LIVE_STATUSES, "include": "custom_fields"})
        return list(data.get("envelopes") or [])

    async def create_draft(self, body: dict[str, Any]) -> dict[str, Any]:
        if body.get("status") != DRAFT_STATUS:
            raise DocuSignError("Refused: this server only creates drafts (status 'created').")
        session = await self.auth.session()
        resp = await self.http.post(session.account_url(self.config.account_id) + "/envelopes",
                                    params={"merge_roles_on_draft": "true"}, json=body,
                                    headers=_headers(session.access_token))
        return _result(resp)

    async def envelope(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}")

    async def envelope_documents(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/documents")

    async def envelope_recipients(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/recipients",
                               {"include_tabs": "true"})

    async def envelope_custom_fields(self, envelope_id: str) -> dict[str, Any]:
        return await self._get(f"/envelopes/{quote(envelope_id, safe='')}/custom_fields")
```

- [ ] **Step 5: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_client.py' -v`
Expected: `Ran 8 tests ... OK`

- [ ] **Step 6: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/client.py shared/mcp/docusign-upload/tests/support.py shared/mcp/docusign-upload/tests/test_client.py
git commit -m "docusign-upload: REST client with a fixed call list; create refuses any status but created"
```

---

### Task 7: The three tools, the selftest and an MCP smoke check

**Files:**
- Create: `shared/mcp/docusign-upload/docusign_upload/server.py`
- Create: `shared/mcp/docusign-upload/docusign_upload/selftest.py`
- Test: `shared/mcp/docusign-upload/tests/test_server.py`

**Interfaces:**
- Consumes: everything from Tasks 1 to 6.
- Produces: FastMCP server `mcp` named `docusign-upload` with async tools `docusign_token_info() -> dict`, `docusign_draft_preview(template_name: str, recipients: list[dict[str, str]], email_subject: str, email_blurb: str, job_no: str, documents: list[dict[str, str]]) -> dict`, `docusign_create_draft(...same arguments...) -> dict`; module globals `_config`, `_config_error`, `_client` (tests patch them); `main()`. Every failure returns `{"ok": False, "error": str, ...}`; stops add `"stop": True`; auth failures add `"consent_url"` when known; DocuSign errors add `"status"`, `"errorCode"`, `"message"`.

- [ ] **Step 1: Write the failing tests**

`shared/mcp/docusign-upload/tests/test_server.py`:

```python
"""The three tools end to end against a fake DocuSign: no network, synthetic data."""
import importlib
import json
import os
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

import httpx

from docusign_upload.client import DocuSignClient
from support import FakeDocuSign, keypair, make_config, make_pdf, write_key

with patch("docusign_upload.config.load_config", return_value=make_config("/nonexistent/key.pem")):
    server = importlib.import_module("docusign_upload.server")

API = "/restapi/v2.1/accounts/acct-synthetic"
ENV = f"{API}/envelopes/env-synthetic"
ALLOWED_CALLS = {
    ("POST", "/oauth/token"), ("GET", "/oauth/userinfo"),
    ("GET", f"{API}/templates"), ("GET", f"{API}/templates/tmpl-qld-single/recipients"),
    ("GET", f"{API}/envelopes"), ("POST", f"{API}/envelopes"),
    ("GET", ENV), ("GET", f"{ENV}/documents"), ("GET", f"{ENV}/recipients"),
    ("GET", f"{ENV}/custom_fields"),
}


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        keys = os.path.join(self.tmp.name, "keys")
        self.root = os.path.join(self.tmp.name, "runtime")
        self.job = os.path.join(self.root, "CONTRACT DOCUMENTATION")
        os.makedirs(keys)
        os.makedirs(self.job)
        self.config = make_config(write_key(keys, keypair()[0]), (self.root,))
        self.fake = FakeDocuSign()
        self.client = DocuSignClient(self.config, httpx.AsyncClient(transport=self.fake.transport()))
        self.addAsyncCleanup(self.client.aclose)
        for p in (patch.object(server, "_config", self.config),
                  patch.object(server, "_client", self.client)):
            p.start()
            self.addCleanup(p.stop)
        self.args = {
            "template_name": "QLD Build _ Single Buyer",
            "recipients": [{"role": "Buyer", "name": "Alex EXAMPLE", "email": "alex@example.com"}],
            "email_subject": "Complete with DocuSign: BUILD CONTRACT - LOT 1, TESTVILLE",
            "email_blurb": "Dear Alex,\n\nPlease find the building contract for review and signing."
                           "\n\nThank you\nSales Admin",
            "job_no": "00001",
            "documents": [self.doc("BUILD CONTRACT", 37), self.doc("INCLUSIONS", 15),
                          self.doc("PLANS", 5)],
        }

    def doc(self, kind, pages, name=None):
        name = name or f"{kind}_LOT 1_TESTVILLE_EXAMPLE.pdf"
        return {"kind": kind, "path": make_pdf(os.path.join(self.job, name), pages)}

    def posts(self):
        return [c for c in self.fake.calls() if c == ("POST", f"{API}/envelopes")]

    async def test_token_info(self):
        out = await server.docusign_token_info()
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["environment"], out["account"], out["user"]),
                         ("SANDBOX", "synthetic", "Synthetic User"))
        self.assertNotIn(self.config.private_key_path, json.dumps(out))

    async def test_preview_plans_and_creates_nothing(self):
        out = await server.docusign_draft_preview(**self.args)
        self.assertTrue(out["ok"], out)
        self.assertEqual([d["tabs"] for d in out["plan"]["documents"]],
                         ["carried from the template", "carried from the template",
                          "none, flagged: 5 pages, the template's has 4"])
        self.assertEqual(self.posts(), [])

    async def test_create_makes_one_draft_and_reads_it_back(self):
        out = await server.docusign_create_draft(**self.args)
        self.assertTrue(out["ok"], out)
        self.assertEqual((out["envelopeId"], out["status"], out["environment"]),
                         ("env-synthetic", "created", "SANDBOX"))
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["plan"]["template"], "QLD Build _ Single Buyer")
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.fake.created["status"], "created")
        post = [r for r in self.fake.requests if r.method == "POST" and r.url.path.endswith("/envelopes")][0]
        self.assertEqual(post.url.params["merge_roles_on_draft"], "true")
        self.assertLessEqual(set(self.fake.calls()), ALLOWED_CALLS)

    async def test_writes_off_refuses_before_any_call(self):
        with patch.object(server, "_config", replace(self.config, enable_writes=False)):
            out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertIn("Writes are disabled", out["error"])
        self.assertEqual(self.fake.calls(), [])

    async def test_an_existing_draft_for_the_job_stops_both_tools(self):
        self.fake.existing = [{"envelopeId": "env-old", "status": "created", "customFields": {
            "textCustomFields": [{"name": "JobNo", "value": "00001"}]}}]
        for tool in (server.docusign_draft_preview, server.docusign_create_draft):
            out = await tool(**self.args)
            self.assertTrue(out["stop"], out)
            self.assertIn("env-old", out["error"])
        self.assertEqual(self.posts(), [])

    async def test_stops_reach_the_caller(self):
        outside = make_pdf(os.path.join(self.tmp.name, "outside.pdf"), 37)
        cases = [
            ({"documents": [self.doc("BUILD CONTRACT", 36, name="BUILD CONTRACT_SHORT.pdf")]},
             "fixed form"),
            ({"documents": [{"kind": "BUILD CONTRACT", "path": outside}]},
             "outside the allowed upload roots"),
            ({"template_name": "QLD Build _ 2 Buyer"}, "matched 0 templates"),
            ({"recipients": [{"role": "BUYER", "name": "A", "email": "a@example.com"}]},
             "not on template"),
        ]
        for change, needle in cases:
            with self.subTest(needle=needle):
                out = await server.docusign_draft_preview(**{**self.args, **change})
                self.assertFalse(out["ok"])
                self.assertTrue(out["stop"])
                self.assertIn(needle, out["error"])

    async def test_job_no_with_query_characters_is_refused_before_network(self):
        out = await server.docusign_draft_preview(**{**self.args, "job_no": "00001&status=any"})
        self.assertFalse(out["ok"])
        self.assertIn("job_no", out["error"])
        self.assertEqual(self.fake.calls(), [])

    async def test_a_docusign_error_is_returned_verbatim_and_not_retried(self):
        self.fake.create_error = (400, {"errorCode": "RECIPIENT_LIMIT_EXCEEDED",
                                        "message": "Synthetic limit message."})
        out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertEqual((out["errorCode"], out["message"]),
                         ("RECIPIENT_LIMIT_EXCEEDED", "Synthetic limit message."))
        self.assertEqual(len(self.posts()), 1)

    async def test_a_transport_failure_says_the_outcome_is_uncertain(self):
        self.fake.create_transport_error = True
        out = await server.docusign_create_draft(**self.args)
        self.assertFalse(out["ok"])
        self.assertIn("uncertain", out["error"])
        self.assertIn("docusign_draft_preview", out["error"])
        self.assertEqual(len(self.posts()), 1)

    async def test_consent_required_is_reported_with_the_consent_url(self):
        self.fake.token_error = "consent_required"
        out = await server.docusign_draft_preview(**self.args)
        self.assertFalse(out["ok"])
        self.assertTrue(out["consent_url"].startswith("https://account-d.docusign.com/oauth/auth?"))

    async def test_not_configured(self):
        message = "Missing required setting(s): DOCUSIGN_USER_ID."
        with patch.object(server, "_config", None), patch.object(server, "_config_error", message):
            for tool in (server.docusign_draft_preview, server.docusign_create_draft):
                self.assertIn("DOCUSIGN_USER_ID", (await tool(**self.args))["error"])
            self.assertIn("DOCUSIGN_USER_ID", (await server.docusign_token_info())["error"])
```

- [ ] **Step 2: Run them and watch them fail**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_server.py' -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'docusign_upload.server'`.

- [ ] **Step 3: Write `server.py`**

`shared/mcp/docusign-upload/docusign_upload/server.py`:

```python
"""FastMCP server: DocuSign drafts with a job's own PDFs. Never sends.

Tools
-----
docusign_token_info     read   environment, account, user, token expiry, write switch
docusign_draft_preview  read   every check the create runs; returns the plan, creates nothing
docusign_create_draft   WRITE  the same checks, then one draft (status "created"), then a read-back

Gates: DOCUSIGN_ENABLE_WRITES (off by default, set in .mcp.json); the host keeps
docusign_create_draft on `ask`, so a person approves every call; and the status
is the constant draft.DRAFT_STATUS. No tool can send, void, correct or delete
an envelope, because client.py has no call that could.
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any

import httpx

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp 2 renamed it; pyproject pins <2, as osc-api does
    from mcp.server.mcpserver import MCPServer as FastMCP

from . import draft
from .auth import AuthError
from .client import DocuSignClient, DocuSignError
from .config import Config, ConfigError, load_config
from .draft import Stop
from .pdfcheck import PdfCheckError, check_pdf

mcp = FastMCP("docusign-upload")

DUPLICATE_WINDOW_DAYS = 180

_config: Config | None = None
_config_error: str | None = None
_client: DocuSignClient | None = None

try:
    _config = load_config()
except ConfigError as exc:  # report it at tool-call time, as osc-api does
    _config_error = str(exc)


def _get_client() -> DocuSignClient:
    global _client
    if _client is None:
        _client = DocuSignClient(_config)
    return _client


def _err(message: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "error": message}
    out.update({k: v for k, v in extra.items() if v is not None})
    return out


def _not_configured() -> dict[str, Any]:
    return _err(_config_error or "docusign-upload is not configured.")


def _failure(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, Stop):
        return _err(str(exc), stop=True)
    if isinstance(exc, AuthError):
        return _err(str(exc), consent_url=exc.consent_url)
    if isinstance(exc, DocuSignError):
        return _err(str(exc), status=exc.status, errorCode=exc.error_code, message=exc.detail)
    return _err("Could not reach DocuSign; nothing was created.")


async def _plan(template_name: str, recipients: list[dict[str, str]], email_subject: str,
                email_blurb: str, job_no: str, documents: list[dict[str, str]]) -> draft.Plan:
    """Every check, cheapest first. Raises Stop, AuthError, DocuSignError or httpx.HTTPError."""
    draft.check_text_args(job_no, email_subject, email_blurb)
    kinds = draft.check_kinds([str(d.get("kind", "")) for d in documents])
    files = []
    for kind, item in zip(kinds, documents):
        try:
            files.append((kind, check_pdf(str(item.get("path", "")), _config.upload_roots)))
        except PdfCheckError as exc:
            raise Stop(f"{kind}: {exc}") from None
    client = _get_client()
    raw = draft.pick_template(await client.list_templates(template_name.strip()), template_name)
    template = draft.parse_template(raw)
    sent = draft.check_recipients(recipients, template)
    planned = draft.plan_documents(files, template)
    draft.check_size(planned)
    since = (date.today() - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    existing = draft.find_duplicate(await client.list_envelopes(since, f"JobNo={job_no}"), job_no)
    if existing is not None:
        raise Stop(f"an envelope for JobNo {job_no} already exists: {existing.get('envelopeId')} "
                   f"(status {existing.get('status')}). Use that one; nothing new was created.")
    return draft.Plan(template, sent, planned, email_subject, email_blurb, job_no)


async def _read_back(client: DocuSignClient, envelope_id: str, plan: draft.Plan) -> dict[str, Any]:
    return draft.read_back(
        plan,
        envelope=await client.envelope(envelope_id),
        documents=await client.envelope_documents(envelope_id),
        recipients=await client.envelope_recipients(envelope_id),
        custom_fields=await client.envelope_custom_fields(envelope_id),
        template_tabs=draft.tab_counts(await client.template_recipients(plan.template.template_id)),
    )


@mcp.tool()
async def docusign_token_info() -> dict[str, Any]:
    """READ-ONLY. Sign in with JWT and report the environment (SANDBOX or PRODUCTION), the
    account and user names, the token expiry and the write switch with its source. Start here
    to check the connection. A consent error includes the one-time consent URL."""
    if _config is None:
        return _not_configured()
    try:
        session = await _get_client().auth.session()
    except (AuthError, httpx.HTTPError) as exc:
        return _failure(exc)
    return {"ok": True, "environment": _config.label, "account": session.account_name,
            "user": session.user_name,
            "token_expires_in_seconds": max(0, int(session.expires_at - time.monotonic())),
            "config": _config.redacted()}


@mcp.tool()
async def docusign_draft_preview(template_name: str, recipients: list[dict[str, str]],
                                 email_subject: str, email_blurb: str, job_no: str,
                                 documents: list[dict[str, str]]) -> dict[str, Any]:
    """READ-ONLY. Run every check docusign_create_draft runs and return the plan. Creates nothing.

    Args (take them from docusign_envelope.json written by docusign_payload.py):
        template_name: the exact template name (templateName), e.g. "QLD Build _ Single Buyer".
        recipients: buyer-side roles only, [{"role", "name", "email"}] from templateRoles
            (roleName -> role). Never Builder, witnesses or date roles: they keep the template's.
        email_subject, email_blurb: from envelopeDefinition.
        job_no: the JobNo custom field value; used for the duplicate check.
        documents: [{"kind", "path"}] from the documents list; kind is BUILD CONTRACT,
            INCLUSIONS, PRELIMINARY AGREEMENT or PLANS; paths are absolute on this server.

    The plan says, per document, whether the template's tabs carry (same page count) or the
    document goes in untagged and flagged. A stop returns ok=false with stop=true and a reason.
    """
    if _config is None:
        return _not_configured()
    try:
        plan = await _plan(template_name, recipients, email_subject, email_blurb, job_no, documents)
    except (Stop, AuthError, DocuSignError, httpx.HTTPError) as exc:
        return _failure(exc)
    return {"ok": True, "dry_run": True, "environment": _config.label, "plan": draft.plan_view(plan),
            "note": "Nothing was created. docusign_create_draft with the same arguments creates "
                    "this draft."}


@mcp.tool()
async def docusign_create_draft(template_name: str, recipients: list[dict[str, str]],
                                email_subject: str, email_blurb: str, job_no: str,
                                documents: list[dict[str, str]]) -> dict[str, Any]:
    """WRITE (gated). Create ONE DocuSign draft envelope (status "created") from the template with
    the job's own PDFs, then read it back. It never sends: staff check the draft, tag any flagged
    document and send it themselves in DocuSign.

    The host keeps this tool on `ask`, so the approval prompt is the person's yes; do not ask
    again in chat. Same arguments as docusign_draft_preview; it re-runs every check itself.
    Call it once per job. On an error, report it as returned: do not retry, and do not change
    the arguments to make it pass. On "uncertain", run docusign_draft_preview before anything else.
    """
    if _config is None:
        return _not_configured()
    if not _config.enable_writes:
        return _err("Writes are disabled: DOCUSIGN_ENABLE_WRITES is not true for this server "
                    f"(source: {_config.enable_writes_source}). Nothing was created.")
    try:
        plan = await _plan(template_name, recipients, email_subject, email_blurb, job_no, documents)
        body = draft.build_body(plan)
    except (Stop, AuthError, DocuSignError, httpx.HTTPError) as exc:
        return _failure(exc)
    except OSError:
        return _err("A document could not be read on the server; nothing was created.")
    client = _get_client()
    try:
        created = await client.create_draft(body)
    except DocuSignError as exc:
        return _err("DocuSign refused the draft. Reported as returned; not retried.",
                    status=exc.status, errorCode=exc.error_code, message=exc.detail)
    except httpx.HTTPError:
        return _err("The create call failed in transit, so whether a draft exists is uncertain. "
                    "Run docusign_draft_preview with the same arguments (it repeats the duplicate "
                    "check) before trying again.")
    envelope_id = str(created.get("envelopeId", ""))
    result: dict[str, Any] = {"ok": True, "environment": _config.label, "envelopeId": envelope_id,
                              "status": created.get("status"), "plan": draft.plan_view(plan)}
    try:
        result.update(await _read_back(client, envelope_id, plan))
    except (DocuSignError, httpx.HTTPError):
        result["read_back"] = "failed; the draft exists, so check it in DocuSign before sending"
    return result


def main() -> None:
    """Console-script and module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -p 'test_server.py' -v`
Expected: `Ran 11 tests ... OK`

- [ ] **Step 5: Write `selftest.py`**

`shared/mcp/docusign-upload/docusign_upload/selftest.py`:

```python
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
```

- [ ] **Step 6: Run the whole suite**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -v`
Expected: `Ran 71 tests ... OK` (16 config + 7 auth + 6 pdfcheck + 23 draft + 8 client + 11 server; symlink tests may show as skipped).

- [ ] **Step 7: MCP smoke check over stdio**

Run:

```bash
cd shared/mcp/docusign-upload && .venv/bin/python - <<'EOF'
import asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    env = dict(os.environ, DOCUSIGN_ENV_FILE=os.devnull)
    params = StdioServerParameters(command=sys.executable, args=["-m", "docusign_upload.server"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(sorted(t.name for t in tools.tools))
            info = await session.call_tool("docusign_token_info", {})
            print(info.content[0].text[:200])

asyncio.run(main())
EOF
```

Expected: `['docusign_create_draft', 'docusign_draft_preview', 'docusign_token_info']`, then a JSON text with `"ok": false` and `Missing required setting(s)` (no `.env` is loaded, so the server starts and defers the config error to the call).

- [ ] **Step 8: Commit**

```bash
git add shared/mcp/docusign-upload/docusign_upload/server.py shared/mcp/docusign-upload/docusign_upload/selftest.py shared/mcp/docusign-upload/tests/test_server.py
git commit -m "docusign-upload: token info, preview and gated create tools; read-only selftest"
```

---

### Task 8: The payload script lists the job's documents

**Files:**
- Modify: `job-roles/contract-admin/scripts/docusign_payload.py` (after `OWNER_KEYS`, in `main()` and in `write_payload`)
- Modify: `job-roles/contract-admin/scripts/test_docusign_payload.py`
- Modify: `job-roles/contract-admin/scripts/README.md:40-41`

**Interfaces:**
- Consumes: `dc.doc_suffix(values)` from `draft_contract.py` (existing).
- Produces: `UPLOAD_KINDS` and `documents_for(job_dir, values) -> tuple[list[dict[str, str]], list[str]]` in `docusign_payload.py`; `docusign_envelope.json` gains top-level `documents` (`[{"kind", "path"}]`, envelope order) and `documentsMissing` (kinds with no file under the CD-7.2 name). `envelopeDefinition` is unchanged, so step 8's `createEnvelope` path is unaffected.

- [ ] **Step 1: Write the failing check**

In `job-roles/contract-admin/scripts/test_docusign_payload.py`, add before the `if __name__ == "__main__":` block:

```python
def check_documents_list():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "job.json").write_text(json.dumps(TWO), encoding="utf-8")
        (wd / "routes.txt").write_text("BUILD CONTRACT\tPRODUCTION\tZ:\\p\n", encoding="utf-8")
        jd = wd / "CONTRACT DOCUMENTATION"
        jd.mkdir()
        suffix = "LOT 12_TESTVILLE_EXAMPLE&SAMPLE"
        for kind in ("BUILD CONTRACT", "INCLUSIONS"):
            (jd / f"{kind}_{suffix}.pdf").write_bytes(b"%PDF-1.7 synthetic")
        (jd / "PLANS - house design.pdf").write_bytes(b"%PDF-1.7 synthetic")  # not the CD-7.2 name
        rc = dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"])
        assert rc == 0, rc
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert [d["kind"] for d in env["documents"]] == ["BUILD CONTRACT", "INCLUSIONS"], env["documents"]
        assert env["documents"][0]["path"] == str(jd / f"BUILD CONTRACT_{suffix}.pdf")
        assert env["documentsMissing"] == ["PRELIMINARY AGREEMENT", "PLANS"], env["documentsMissing"]
        assert "documents" not in env["envelopeDefinition"]
        txt = (wd / "docusign_payload.txt").read_text(encoding="utf-8")
        assert f"    INCLUSIONS: INCLUSIONS_{suffix}.pdf" in txt, txt
        assert "not in the job folder under the CD-7.2 name: PRELIMINARY AGREEMENT, PLANS" in txt, txt
        (jd / f"PLANS_{suffix}.pdf").write_bytes(b"%PDF-1.7 synthetic")
        assert dp.main(["--job", str(wd / "job.json"), "--job-dir", str(jd), "--region", "NSW"]) == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert [d["kind"] for d in env["documents"]] == ["BUILD CONTRACT", "INCLUSIONS", "PLANS"]
        # no --job-dir: nothing listed, and the report says why
        assert dp.main(["--job", str(wd / "job.json"), "--region", "NSW"]) == 0
        env = json.loads((wd / "docusign_envelope.json").read_text(encoding="utf-8"))
        assert env["documents"] == [] and env["documentsMissing"] == []
        assert "none listed (no --job-dir)" in (wd / "docusign_payload.txt").read_text(encoding="utf-8")
    print("  documents list: ok")
```

and add `check_documents_list()` after `check_cli_files()` in the `__main__` block.

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: the earlier checks print `ok`, then `KeyError: 'documents'` in `check_documents_list`.

- [ ] **Step 3: Implement in `docusign_payload.py`**

After `OWNER_KEYS = ("owner_1", "owner_2", "owner_3")`, add:

```python
# The kinds the docusign-upload server takes, in envelope order (CD-7.2 names).
UPLOAD_KINDS = ("BUILD CONTRACT", "INCLUSIONS", "PRELIMINARY AGREEMENT", "PLANS")


def documents_for(job_dir, values):
    """([{kind, path}], [missing kinds]) for the job's PDFs under their CD-7.2 names.

    Only the exact `<KIND>_<suffix>.pdf` counts, so plans saved under any other
    name stay out and are reported as missing rather than guessed at."""
    suffix = dc.doc_suffix(values)
    found, missing = [], []
    for kind in UPLOAD_KINDS:
        path = Path(job_dir) / f"{kind}_{suffix}.pdf"
        if path.is_file():
            found.append({"kind": kind, "path": str(path)})
        else:
            missing.append(kind)
    return found, missing
```

In `main()`, replace the block

```python
        if args.job_dir:
            pdf = f"BUILD CONTRACT_{dc.doc_suffix(values)}.pdf"
            if not (Path(args.job_dir) / pdf).is_file():
                raise PayloadStop(f"build contract PDF not found in the job folder ({pdf}) "
                                  f"- the draft needs a saved contract")
```

with

```python
        if args.job_dir:
            pdf = f"BUILD CONTRACT_{dc.doc_suffix(values)}.pdf"
            if not (Path(args.job_dir) / pdf).is_file():
                raise PayloadStop(f"build contract PDF not found in the job folder ({pdf}) "
                                  f"- the draft needs a saved contract")
            env["documents"], env["documentsMissing"] = documents_for(args.job_dir, values)
        else:
            env["documents"], env["documentsMissing"] = [], []
```

In `write_payload`, directly after the `custom field  :` line is added to `lines` (the list literal ends with that line), insert before `if env["flags"]:`:

```python
    if "documents" in env:
        found = [f"    {d['kind']}: {Path(d['path']).name}" for d in env["documents"]]
        lines += ["documents     :", *(found or ["    none listed (no --job-dir)"])]
        if env.get("documentsMissing"):
            lines.append("not in the job folder under the CD-7.2 name: "
                         + ", ".join(env["documentsMissing"]))
```

- [ ] **Step 4: Run it and see it pass**

Run: `python3 job-roles/contract-admin/scripts/test_docusign_payload.py`
Expected: every check prints `ok`, ending with `  documents list: ok` and `docusign_payload self-test: all ok`.

- [ ] **Step 5: Update the scripts README rows**

In `job-roles/contract-admin/scripts/README.md`, in the `docusign_payload.py` row (line 40), after the sentence ending `a TEST-routed build contract gets the files and \`CALL: no\`.` add: `Since 13 Oct 2026 the JSON also lists the job's PDFs under their CD-7.2 names (\`documents\`, plus \`documentsMissing\`) for the \`docusign-upload\` server; plans count only under the exact name.` In the `test_docusign_payload.py` row (line 41), after `region from the job-folder path` add `, the documents list (CD-7.2 names only, envelope order)`.

- [ ] **Step 6: Commit**

```bash
git add job-roles/contract-admin/scripts/docusign_payload.py job-roles/contract-admin/scripts/test_docusign_payload.py job-roles/contract-admin/scripts/README.md
git commit -m "contract-admin: docusign_payload.py lists the job's PDFs by CD-7.2 name for the docusign-upload server"
```

---

### Task 9: Registration, permissions and docs

**Files:**
- Modify: `.mcp.json`
- Modify: `.claude/settings.json`
- Create: `shared/mcp/docusign-upload/.env.example`
- Modify: `shared/mcp/docusign-upload/README.md` (replace the placeholder)
- Modify: `docs/mcp-servers.md` (table rows 13 to 16; new section before `## OSC API (Companion Systems)`)
- Modify: `CLAUDE.md:91-98` (the gated-write paragraph)

**Interfaces:**
- Consumes: tool names from Task 7, variable names from Task 1.
- Produces: the server registered at project scope; `mcp__docusign-upload__docusign_token_info` and `mcp__docusign-upload__docusign_draft_preview` on `allow`; `mcp__docusign-upload__docusign_create_draft` and `mcp__docusign-upload-prod__docusign_create_draft` on `ask`.

Use the `transpire-writing` skill for every prose change in this task (Australian English, no em or en dashes, sentence-case headings).

- [ ] **Step 1: Register the server in `.mcp.json`**

Add a second entry inside `mcpServers`, after `osc-api`:

```json
    "docusign-upload": {
      "type": "stdio",
      "command": "Z:/CLAUDE CODE/transpire-claude-code/shared/mcp/docusign-upload/.venv/Scripts/python.exe",
      "args": ["-m", "docusign_upload.server"],
      "env": {
        "DOCUSIGN_ENVIRONMENT": "demo",
        "DOCUSIGN_ENABLE_WRITES": "true"
      }
    }
```

- [ ] **Step 2: Permissions in `.claude/settings.json`**

- `enabledMcpjsonServers`: `["osc-api", "docusign-upload"]`
- `allow`: add `"mcp__docusign-upload__docusign_token_info"` and `"mcp__docusign-upload__docusign_draft_preview"` after the `mcp__docusign-demo__getEnvelopeVsAgreementSkill` line.
- `ask`: add `"mcp__docusign-upload__docusign_create_draft"` and `"mcp__docusign-upload-prod__docusign_create_draft"` after the `mcp__docusign-demo__installDVApps` line. Do **not** add a server-wide `mcp__docusign-upload` entry: `ask` beats `allow`, so it would make the read tools prompt.

Run: `python3 -m json.tool .mcp.json > /dev/null && python3 -m json.tool .claude/settings.json > /dev/null && echo valid`
Expected: `valid`

- [ ] **Step 3: Write `shared/mcp/docusign-upload/.env.example`**

```dotenv
# docusign-upload MCP: environment template.
# Copy to .env beside this file on the server (git-ignored), or point
# DOCUSIGN_ENV_FILE at a copy outside the repo. Never commit real values.
# The private key never goes in this file: only its path.

# Required
# demo is the developer sandbox (account-d.docusign.com) and only takes
# synthetic jobs from this checkout's runtime folder; production is live.
# The committed .mcp.json sets this for Claude Code sessions.
DOCUSIGN_ENVIRONMENT=demo

# From Apps and Keys in that environment's DocuSign admin.
DOCUSIGN_INTEGRATION_KEY=
# The template owner's API Username (a user id): the user the drafts are created as.
DOCUSIGN_USER_ID=
# The API Account ID.
DOCUSIGN_ACCOUNT_ID=

# Absolute path to the RSA private key (*.pem) on Z:, outside this checkout,
# in a folder only the accounts running Claude Code can read. Never on C:.
DOCUSIGN_PRIVATE_KEY_PATH=

# Optional
# Folders documents may be read from, separated by ";". Required in
# production (the job folders' root); in demo only runtime or a folder in it.
DOCUSIGN_UPLOAD_ROOTS=

# The redirect URI registered on the integration key. Used to print the
# one-time consent URL when consent is missing.
DOCUSIGN_CONSENT_REDIRECT_URI=

# Write switch. The committed .mcp.json sets it for Claude Code sessions and
# beats this file; this line only matters for a server started by hand.
DOCUSIGN_ENABLE_WRITES=false

# Seconds per request.
DOCUSIGN_TIMEOUT=60
```

- [ ] **Step 4: Write `shared/mcp/docusign-upload/README.md`**

Replace the placeholder with:

````markdown
# docusign-upload MCP server

A local (stdio) MCP server that creates a DocuSign **draft** envelope from one
of the six company templates with the job's own PDFs in it. It never sends:
staff check the draft, tag anything the report flags and send it in DocuSign.
Design and decisions: [`docs/superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md`](../../../docs/superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md).

This is code only. Ids, the key path and the environment come from
`DOCUSIGN_*` variables (see [`.env.example`](.env.example)); nothing that
identifies an account or a server is in the repo.

## Tools

| Tool | Kind | Permission | What it does |
|---|---|---|---|
| `docusign_token_info` | read | `allow` | Environment (SANDBOX or PRODUCTION), account, user, token expiry, write switch |
| `docusign_draft_preview` | read | `allow` | Every check the create runs; returns the plan, creates nothing |
| `docusign_create_draft` | write | `ask` | The same checks, one draft with status `created`, then a read-back |

Both preview and create take `template_name`, `recipients` (buyer roles:
`role`, `name`, `email`), `email_subject`, `email_blurb`, `job_no` and
`documents` (`kind`, `path`), taken from the `docusign_envelope.json` that
`job-roles/contract-admin/scripts/docusign_payload.py` writes.

## How the draft is built

One composite per job document. A document **carries** the template's tabs
when the template has a document of that kind with the same page count;
otherwise it goes in with no tabs and the report **flags** it for staff to tag.
The build contract must carry, or the run stops. Template documents with no
job file are left out, so no past job's PDF reaches the draft. Every template
tab is fixed to a page position, which is why page counts decide.

## Gates

1. `DOCUSIGN_ENABLE_WRITES` is off by default; the committed `.mcp.json` sets it.
2. `docusign_create_draft` is on `ask` in `.claude/settings.json`: every call prompts.
3. The status is a constant in `draft.py`, and `client.py` has no call that could
   send, void, correct or delete an envelope.

With `DOCUSIGN_ENVIRONMENT=demo` the server reads documents only from this
checkout's `runtime` folder: the sandbox gets synthetic jobs only.

## Install (Windows server, `pwsh`)

```powershell
Set-Location "Z:\CLAUDE CODE\transpire-claude-code\shared\mcp\docusign-upload"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# .env beside this README: copy .env.example and fill it in (values from the
# DocuSign admin; the key file stays on Z: outside the checkout)
.\.venv\Scripts\python.exe -m docusign_upload.selftest
```

Then open a new Claude Code session in the repo folder and run
`docusign_token_info`. The admin prerequisites (integration key, RSA public
key, consent) are listed in the design document.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Synthetic data only, no network, no credentials.
````

- [ ] **Step 5: `docs/mcp-servers.md`**

Add a table row under `osc-api`:

```markdown
| `docusign-upload` | Project (`.mcp.json` in repo root) | DocuSign **developer sandbox** (`demo`), synthetic jobs only | Code in repo; needs the per-checkout venv, `.env` and the DocuSign admin prerequisites. Create on `ask` per call |
```

Insert before `## OSC API (Companion Systems)`:

```markdown
## DocuSign drafts with the job's PDFs (`docusign-upload`)

A **local (stdio) MCP server**, our code, at
[`shared/mcp/docusign-upload/`](../shared/mcp/docusign-upload/). The hosted
`docusign-demo` server takes documents only by public URL, so its drafts
carry the templates' placeholder PDFs. This server reads the job's PDFs
itself and creates the draft through the eSignature REST API with JWT Grant,
as the user who owns the six templates. Design:
[`2026-10-13-docusign-upload-mcp.md`](superpowers/brainstorms/2026-10-13-docusign-upload-mcp.md).

- **Tools.** `docusign_token_info` and `docusign_draft_preview` are read-only
  and on `allow`; `docusign_create_draft` is on `ask`, so every create prompts.
  It creates drafts only (status `created`); nothing in the code can send, void
  or delete an envelope.
- **Sandbox data rule.** With `DOCUSIGN_ENVIRONMENT=demo` (set in `.mcp.json`)
  the server reads documents only from the checkout's `runtime` folder. Real job
  folders need a production server, `docusign-upload-prod`, whose `ask` entry is
  already in place.
- **Key custody.** The RSA private key lives on `Z:` outside the checkout, in a
  folder only the accounts running Claude Code can read, named `*.pem` so the
  `Z:` deny rules keep Claude's own file tools off it. Only the public key goes
  to DocuSign. Never on `C:`, in a prompt, a log or a commit.
- **Setup.** Install steps are in the server's
  [README](../shared/mcp/docusign-upload/README.md); the DocuSign admin
  prerequisites are in the design document.
- Step 8 of `/new-contract-template` still uses `docusign-demo` until
  production DocuSign is connected.
```

- [ ] **Step 6: `CLAUDE.md`**

At the end of the gated-write paragraph (after `` `getEnvelopeVsAgreementSkill`) are on `allow`. ``), add:

```markdown
  The local `docusign-upload` server's `docusign_create_draft` (a draft with
  the job's own PDFs, design 13 Oct 2026) is the same kind of gated write, on
  `ask` per call; while it points at the sandbox it takes synthetic jobs only.
```

- [ ] **Step 7: Check the prose**

Run: `git diff -U0 docusign-integration | python3 -c "import sys; print(sum(1 for l in sys.stdin if l.startswith('+') and ('\\u2014' in l or '\\u2013' in l)))"`
Expected: `0` (no em or en dash anywhere the branch added; lines it did not touch may already have some).

- [ ] **Step 8: Commit**

```bash
git add .mcp.json .claude/settings.json shared/mcp/docusign-upload/.env.example shared/mcp/docusign-upload/README.md docs/mcp-servers.md CLAUDE.md
git commit -m "docusign-upload: register at project scope, preview and token on allow, create on ask; README, env template, MCP register, CLAUDE.md"
```

---

### Task 10: Push and open the PR

**Files:** none changed.

- [ ] **Step 1: Full verification before pushing**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python -m unittest discover -s tests -v 2>&1 | tail -3 && cd - && python3 job-roles/contract-admin/scripts/test_docusign_payload.py | tail -1 && python3 job-roles/contract-admin/scripts/test_routing.py | tail -1`
Expected: `OK` (with any skips), `docusign_payload self-test: all ok`, and the routing self-test's final ok line.

Run: `git diff docusign-integration --stat && git diff docusign-integration | grep -E "^\+" | grep -Ei "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|BEGIN (RSA )?PRIVATE KEY|Co-Authored-By|Generated with" ; echo "scan done"`
Expected: the file list, then only `scan done` (no GUIDs, no key material, no attribution).

- [ ] **Step 2: Push**

```bash
git push -u origin docusign-upload-mcp
```

- [ ] **Step 3: Write the PR body**

Write the body to the session scratchpad as `pr-body.md` through `transpire-writing` (Australian English, no dashes, no AI attribution). Sections: **What** (the server, three tools, carry or flag, the payload documents list, registration); **Why** (PR #49's draft carries placeholder PDFs; the templates' tabs are fixed-position, hence carry or flag); **Gates and data** (switch, `ask`, constant status, no send call, demo locked to `runtime`, key custody); **Verified** (unit test count from Step 1, payload and routing self-tests, the stdio smoke check; sandbox prototype pending the DocuSign admin prerequisites); **Not in this PR** (step 8 switch, production, re-basing, anchor tabs); **Stacked on** PR #49, to retarget to `main` once it merges.

- [ ] **Step 4: Open the PR**

```bash
gh pr create --repo lxgzmy/transpaire-claude-code --base docusign-integration --head docusign-upload-mcp --title "docusign-upload: local MCP server that puts the job's own PDFs in the DocuSign draft (sandbox)" --body-file "<scratchpad>/pr-body.md"
```

Expected: the PR URL. Then load and call `mcp__ccd_pr__get_status`; if it does not report this PR, call `mcp__ccd_pr__bind_pr` with the URL. Do not merge and do not enable auto-merge.

---

### Task 11: Sandbox prototype (needs the DocuSign admin prerequisites and a person's yes)

**Files:** none committed. Working files go to `runtime/contract-admin/outputs/_docusign-upload-proto/` (git-ignored) and the session scratchpad; the key and `.env` go to `~/.config/transpire/docusign-sandbox/` (outside the repo).

Every step that touches DocuSign or a credential is either a person's act or needs their explicit yes in chat first. Never type a password, never read the private key back, never print the token.

- [ ] **Step 1: Generate the key pair (with the person's yes)**

```bash
mkdir -p ~/.config/transpire/docusign-sandbox && chmod 700 ~/.config/transpire/docusign-sandbox
openssl genrsa -out ~/.config/transpire/docusign-sandbox/docusign-sandbox.pem 2048
chmod 600 ~/.config/transpire/docusign-sandbox/docusign-sandbox.pem
openssl rsa -in ~/.config/transpire/docusign-sandbox/docusign-sandbox.pem -pubout -out ~/.config/transpire/docusign-sandbox/docusign-sandbox.pub.pem
cat ~/.config/transpire/docusign-sandbox/docusign-sandbox.pub.pem
```

Show the person the **public** key only.

- [ ] **Step 2: The person does the admin steps**

In the sandbox's Apps and Keys: add the integration key, turn on Authorization Code Grant with one https redirect URI, **Upload RSA** with the public key from Step 1, and note the integration key, the template owner's API Username and the API Account ID. They write `~/.config/transpire/docusign-sandbox/.env` from `.env.example` with `DOCUSIGN_ENVIRONMENT=demo`, those three values, `DOCUSIGN_PRIVATE_KEY_PATH` set to the `.pem` from Step 1, the redirect URI and `DOCUSIGN_ENABLE_WRITES=true`. Then, signed in as the template owner, they open the consent URL (the spec's prerequisites list has the form) and click Accept.

- [ ] **Step 3: Selftest (read-only)**

Run: `cd shared/mcp/docusign-upload && DOCUSIGN_ENV_FILE=~/.config/transpire/docusign-sandbox/.env .venv/bin/python -m docusign_upload.selftest`
Expected: `Signed in (SANDBOX)`, and `Templates matching 'Build _': 6` with the six names. A `SIGN-IN ERROR` with a consent URL means Step 2's consent is missing.

- [ ] **Step 4: Build the synthetic job**

```bash
WD="runtime/contract-admin/outputs/_docusign-upload-proto"
mkdir -p "$WD/CONTRACT DOCUMENTATION"
printf '%s\n' '{"job_no": "00001", "lot_no": "1", "suburb": "Testville QLD", "owner_1": "Alex EXAMPLE", "owner_email": "alex.example@example.com"}' > "$WD/job.json"
printf 'BUILD CONTRACT\tPRODUCTION\t%s\n' "$WD/CONTRACT DOCUMENTATION" > "$WD/routes.txt"
shared/mcp/docusign-upload/.venv/bin/python - "$WD/CONTRACT DOCUMENTATION" <<'EOF'
import sys
from pathlib import Path
from pypdf import PdfWriter
folder = Path(sys.argv[1])
for kind, pages in (("BUILD CONTRACT", 37), ("INCLUSIONS", 15), ("PLANS", 5)):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    with open(folder / f"{kind}_LOT 1_TESTVILLE_EXAMPLE.pdf", "wb") as fh:
        w.write(fh)
print("written")
EOF
python3 job-roles/contract-admin/scripts/docusign_payload.py --job "$WD/job.json" --job-dir "$WD/CONTRACT DOCUMENTATION" --region QLD
```

Expected: `template      : QLD Build _ Single Buyer`, `CALL: yes`, and `documents     :` listing BUILD CONTRACT, INCLUSIONS and PLANS.

- [ ] **Step 5: Preview (read-only)**

Write this harness to the scratchpad as `proto.py`:

```python
"""Prototype harness: call the server's tools directly with the payload's values."""
import asyncio
import json
import os
import sys

os.environ.setdefault("DOCUSIGN_ENV_FILE", os.path.expanduser("~/.config/transpire/docusign-sandbox/.env"))
from docusign_upload import server  # noqa: E402


async def main(mode: str, envelope_json: str) -> None:
    with open(envelope_json, encoding="utf-8") as fh:
        env = json.load(fh)
    d = env["envelopeDefinition"]
    args = {"template_name": env["templateName"],
            "recipients": [{"role": r["roleName"], "name": r["name"], "email": r["email"]}
                           for r in d["templateRoles"]],
            "email_subject": d["emailSubject"], "email_blurb": d["emailBlurb"],
            "job_no": d["customFields"]["textCustomFields"][0]["value"],
            "documents": env["documents"]}
    tool = server.docusign_create_draft if mode == "create" else server.docusign_draft_preview
    print(json.dumps(await tool(**args), indent=2))


asyncio.run(main(sys.argv[1], sys.argv[2]))
```

Run: `cd shared/mcp/docusign-upload && .venv/bin/python <scratchpad>/proto.py preview "../../../runtime/contract-admin/outputs/_docusign-upload-proto/docusign_envelope.json"`
Expected: `"ok": true`, `"environment": "SANDBOX"`, documents `carried from the template` (contract, inclusions) and `none, flagged: 5 pages, the template's has 4` (plans), `roles_left_as_template_defaults: ["Builder"]`.

- [ ] **Step 6: Ask the person for an explicit yes**

Show the preview's plan and ask with `AskUserQuestion` whether to create this one sandbox draft. A no ends the task here, reported as "not created, declined".

- [ ] **Step 7: Create and read back (only after the yes)**

Run: `cd shared/mcp/docusign-upload && .venv/bin/python <scratchpad>/proto.py create "../../../runtime/contract-admin/outputs/_docusign-upload-proto/docusign_envelope.json"`
Expected: `"ok": true`, `"status": "created"`, `"findings": []`, contract and inclusions with `tab_pages_by_role` matching the template (Buyer initials and signatures, Builder on page 13), plans with none, `roles_without_tabs: []`. If DocuSign returns `RECIPIENT_LIMIT_EXCEEDED` or any other error, report it verbatim and stop: the prototype then needs an unrestricted sandbox account. Any finding is reported as found, with no fix-and-retry.

- [ ] **Step 8: Second preview proves the duplicate check sees drafts**

Run the Step 5 command again.
Expected: `"stop": true` and `an envelope for JobNo 00001 already exists`.

- [ ] **Step 9: The person deletes the draft**

Ask the person to delete the draft in the DocuSign web UI (Drafts folder). Deleting is their act, not the server's.

- [ ] **Step 10: Record the result on the PR**

Add a "Sandbox prototype" section to the PR body (`gh pr edit --body-file`): what was created (template, three synthetic documents, carry and flag as planned), the read-back result, the duplicate stop, and that the draft was deleted. No envelope id, account id or template id in the text.
