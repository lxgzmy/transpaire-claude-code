"""FastMCP server exposing the OSC API to Claude Code.

Tool surface
------------
Read (safe to allow-list):
  osc_token_info       - granted scope + expiry for the current credential
  osc_list_endpoints   - list endpoints from the OpenAPI spec (filterable)
  osc_describe_endpoint- parameters / request body / responses for one endpoint
  osc_get              - GET any endpoint (supports OData query + body-filter GETs)

Write (gated - see osc_write docstring):
  osc_write            - POST/PUT/PATCH/DELETE, refused unless OSC_ENABLE_WRITES=true

Writes are gated in two independent ways: this tool refuses at the code level
unless OSC_ENABLE_WRITES is true, and the host is expected to keep
mcp__osc-api__osc_write on `ask` so a human approves every call. That satisfies
the org rule that nothing is written to a system of record without human sign-off.
"""
from __future__ import annotations

import json
import mimetypes
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import httpx

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp >= 2.0 renamed FastMCP -> MCPServer; the API is the same
    from mcp.server.mcpserver import MCPServer as FastMCP

from .client import WRITE_METHODS, OSCClient, OSCError
from .config import Config, ConfigError, load_config
from .spec import SpecView, find_operation

mcp = FastMCP("osc-api")

_client: OSCClient | None = None
_config: Config | None = None
_config_error: str | None = None

try:
    _config = load_config()
except ConfigError as exc:  # defer failure to tool-call time with a clear message
    _config_error = str(exc)


def _get_client() -> OSCClient:
    global _client
    if _config is None:
        raise OSCError(_config_error or "OSC MCP is not configured.")
    if _client is None:
        _client = OSCClient(_config)
    return _client


def _err(message: str, **extra: Any) -> dict[str, Any]:
    out = {"ok": False, "error": message}
    out.update(extra)
    return out


def _forms(p: str) -> set[str]:
    """Comparable spellings of a path: as given and with drive mappings resolved."""
    out = {os.path.normcase(os.path.abspath(p))}
    try:
        out.add(os.path.normcase(os.path.realpath(p)))
    except OSError:
        pass
    return out


def _inside(candidate: str, roots: tuple[str, ...]) -> bool:
    """True when candidate sits under one of roots (any spelling, mapped or UNC)."""
    for root in roots:
        for r in _forms(root):
            r = r.rstrip("\\/") + os.sep
            if any(c.startswith(r) for c in _forms(candidate)):
                return True
    return False


def _check_uploads(files: dict[str, str], roots: tuple[str, ...]) -> list[dict[str, Any]]:
    """Per-file checks for a multipart write. Reads metadata only; never opens a file."""
    checks = []
    for field, value in files.items():
        p = Path(value)
        entry: dict[str, Any] = {"field": field, "path": value, "ok": False}
        if not p.is_absolute():
            entry["problem"] = "not an absolute path"
        elif not roots:
            entry["problem"] = "no upload roots configured (OSC_UPLOAD_ROOTS)"
        elif not _inside(value, roots):
            entry["problem"] = "outside the allowed upload roots"
        elif not p.is_file():
            entry["problem"] = "not an existing regular file on the MCP server machine"
        else:
            entry["ok"] = True
            entry["bytes"] = p.stat().st_size
        checks.append(entry)
    return checks


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def osc_token_info() -> dict[str, Any]:
    """Return the current credential's granted OAuth scope and token expiry.

    Use this first to confirm connectivity and to see which scopes you have
    (e.g. Basic, Orders, Inspections). A 403 from another tool usually means the
    endpoint needs a scope not listed here.
    """
    try:
        client = _get_client()
        info = await client.token_info()
        return {"ok": True, "config": _config.redacted() if _config else None, "token": info}
    except OSCError as exc:
        return _err(str(exc), status=exc.status, body=exc.body)


@mcp.tool()
async def osc_list_endpoints(contains: str = "", method: str = "") -> dict[str, Any]:
    """List OSC API endpoints from the OpenAPI spec.

    Args:
        contains: case-insensitive substring to filter paths (e.g. "Job", "Variation").
        method:   optional HTTP method filter (e.g. "get", "post").

    Returns each matching path with its available methods and summary. Read-only.
    """
    try:
        spec = await _get_client().get_spec()
    except OSCError as exc:
        return _err(str(exc), status=exc.status)

    contains_l = contains.lower()
    method_l = method.lower()
    endpoints = []
    for path, ops in spec.get("paths", {}).items():
        if contains_l and contains_l not in path.lower():
            continue
        methods = {
            m.upper(): (op.get("summary") or "").strip()
            for m, op in ops.items()
            if isinstance(op, dict) and m.lower() in {"get", "post", "put", "patch", "delete"}
        }
        if method_l:
            methods = {m: s for m, s in methods.items() if m.lower() == method_l}
        if methods:
            endpoints.append({"path": path, "methods": methods})
    endpoints.sort(key=lambda e: e["path"])
    return {
        "ok": True,
        "count": len(endpoints),
        "spec_title": spec.get("info", {}).get("title"),
        "endpoints": endpoints,
    }


@mcp.tool()
async def osc_describe_endpoint(path: str, method: str = "") -> dict[str, Any]:
    """Show parameters, request body and responses for one endpoint.

    Args:
        path:   exact path from osc_list_endpoints, e.g. "/api/Jobs".
        method: optional; if omitted, every method on the path is described.

    Includes request_body, response_details, full parameters and transitively
    referenced_definitions keyed by literal $ref. Check unresolved_references
    before constructing a payload. External references are never fetched.
    """
    try:
        spec = await _get_client().get_spec()
    except OSCError as exc:
        return _err(str(exc), status=exc.status)

    ops = spec.get("paths", {}).get(path)
    if ops is None:
        return _err(f"Path not found in spec: {path}. Try osc_list_endpoints.")

    view = SpecView(spec)
    ops = view.resolve(ops) if "$ref" in ops else ops
    wanted = method.lower()
    described = {}
    for m, op in ops.items():
        if m.lower() not in {"get", "post", "put", "patch", "delete"}:
            continue
        if wanted and m.lower() != wanted:
            continue
        rb = view.resolve(op["requestBody"]) if op.get("requestBody") else None
        body_types = None
        if rb:
            body_types = list(rb.get("content", {}).keys())
        parameters = {}
        for p in [*ops.get("parameters", []), *op.get("parameters", [])]:
            param = view.resolve(p)
            parameters[(param.get("in"), param.get("name"))] = param
        responses = {code: view.resolve(value) for code, value in op.get("responses", {}).items()}
        described[m.upper()] = {
            "summary": op.get("summary"),
            "description": (op.get("description") or "")[:800],
            "parameters": list(parameters.values()),
            "request_body_content_types": body_types,
            "request_body": rb,
            "responses": list(op.get("responses", {}).keys()),
            "response_details": responses,
            "is_write": m.upper() in WRITE_METHODS,
        }
    if not described:
        return _err(f"No matching method on {path}.")
    return {"ok": True, "path": path, "operations": described,
            "referenced_definitions": view.definitions,
            "unresolved_references": [{"ref": ref, "reason": reason}
                                      for ref, reason in sorted(view.unresolved.items())]}


@mcp.tool()
async def osc_get(path: str, query: dict | None = None, odata_filter: dict | None = None) -> dict[str, Any]:
    """GET data from any OSC endpoint. Read-only.

    Args:
        path:  endpoint path, e.g. "/api/Clients" or "/api/Jobs".
        query: OData/query-string params, e.g. {"$top": 5, "$filter": "name eq 'X'"}.
        odata_filter: some collection GETs (notably /api/Jobs) require a JSON body
               carrying the filter; pass it here (use {} for "no filter").

    Returns {status, ok, data}. Never mutates server state.
    """
    try:
        client = _get_client()
        result = await client.request("GET", path, params=query, json_body=odata_filter)
        return result
    except OSCError as exc:
        return _err(str(exc), status=exc.status, body=exc.body)


# ---------------------------------------------------------------------------
# Write tool (gated)
# ---------------------------------------------------------------------------
@mcp.tool()
async def osc_write(
    method: str,
    path: str,
    body: dict | None = None,
    query: dict | None = None,
    confirm: bool = False,
    form: dict[str, str] | None = None,
    files: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create/update/delete via the OSC API. WRITE - guarded.

    This changes a system of record, so it is gated:
      1. It refuses unless the server was started with OSC_ENABLE_WRITES=true.
      2. The host keeps this tool on `ask`, so a human approves each call.
      3. You must pass confirm=true, after showing the caller exactly what will
         be sent (method, path, body). With confirm=false it returns a dry-run
         preview and sends nothing.

    Args:
        method: POST | PUT | PATCH | DELETE.
        path:   endpoint path, e.g. "/api/Clients/{ClientID}".
        body:   JSON request body per osc_describe_endpoint.
        query:  optional query-string params.
        confirm: must be true to actually send; false returns a preview.
        form: multipart text fields, e.g. Subject and Documents[0].description.
        files: multipart field to absolute file path on the MCP server machine,
            e.g. Documents[0].file. Each path must sit under one of the
            configured upload roots (OSC_UPLOAD_ROOTS; default the checkout's
            runtime folder). Files are opened only after all write gates.
            Use form/files only for endpoints advertising multipart/form-data.
            Do not combine them with body. The preview runs the same route and
            file checks the send will (route is multipart, file exists under a
            root, size) and reports them under `checks`, without opening a file.
    """
    method_u = method.upper()
    if method_u not in WRITE_METHODS:
        return _err(f"osc_write only handles {sorted(WRITE_METHODS)}; use osc_get for GET.")

    if _config is None:
        return _err(_config_error or "OSC MCP is not configured.")

    preview = {"method": method_u, "path": path, "query": query, "body": body}
    multipart = form is not None or files is not None
    checks: list[dict[str, Any]] = []
    if multipart:
        preview.update(form=form, files=files)
        if body is not None:
            return _err("Use either body or multipart form/files, not both.", would_send=preview)
        if not form and not files:
            return _err("Multipart requests need at least one form field or file.", would_send=preview)
        # The same checks run for the preview and for the send, so a person
        # approving a dry run sees what the real call will hit. Nothing here
        # opens a file: route lookup reads the cached spec, files are stat'ed.
        checks = await _multipart_checks(method_u, path, files or {})
    problems = [c for c in checks if not c["ok"]]

    if not _config.enable_writes:
        return _err(
            "Writes are disabled. Start the server with OSC_ENABLE_WRITES=true to "
            "allow write calls (and only against the intended environment).",
            would_send=preview, checks=checks,
        )

    if not confirm:
        out: dict[str, Any] = {"ok": not problems, "dry_run": True, "would_send": preview,
                               "note": "Nothing was sent. Re-call with confirm=true to execute."}
        if checks:
            out["checks"] = checks
        if problems:
            out["error"] = "Preview found problems; fix them before confirm=true."
        return out

    if problems:
        return _err("Multipart checks failed; nothing was sent.", would_send=preview, checks=checks)

    try:
        client = _get_client()
        if multipart:
            paths = {field: Path(value) for field, value in (files or {}).items()}
            with ExitStack() as stack:
                uploads = {field: (p.name, stack.enter_context(p.open("rb")),
                                   mimetypes.guess_type(p.name)[0] or "application/octet-stream")
                           for field, p in paths.items()}
                result = await client.request(method_u, path, params=query,
                                              form_data=form, files=uploads)
        else:
            result = await client.request(method_u, path, params=query, json_body=body)
        result["dry_run"] = False
        return result
    except OSCError as exc:
        return _err(str(exc), status=exc.status, body=exc.body)
    except OSError:
        return _err("Could not read an upload file; check server-local access. No automatic retry was made.")
    except httpx.HTTPError:
        return _err("OSC transport failed; outcome may be uncertain. Read current state before retrying.")


async def _multipart_checks(method_u: str, path: str, files: dict[str, str]) -> list[dict[str, Any]]:
    """Route and file checks for a multipart write (shared by preview and send)."""
    checks: list[dict[str, Any]] = []
    route_check: dict[str, Any] = {"field": None, "path": path, "ok": False}
    try:
        spec = await _get_client().get_spec()
    except OSCError as exc:
        route_check["problem"] = f"cannot load the OSC spec to verify the route: {exc}"
        checks.append(route_check)
    else:
        view = SpecView(spec)
        route, operation = find_operation(spec, view, path, method_u)
        rb = view.resolve(operation.get("requestBody", {})) if operation else {}
        if route is None:
            route_check["problem"] = "no OSC route matches this path"
        elif not operation:
            route_check["problem"] = f"route {route} has no {method_u} operation"
        elif "multipart/form-data" not in rb.get("content", {}):
            route_check["problem"] = f"{method_u} {route} does not advertise multipart/form-data"
        elif view.unresolved:
            route_check["problem"] = "unresolved schema references; inspect the endpoint before writing"
        else:
            route_check.update(ok=True, route=route)
        checks.append(route_check)
    checks.extend(_check_uploads(files, _config.upload_roots if _config else ()))
    return checks


def main() -> None:
    """Console-script / module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
