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
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp >= 2.0 renamed FastMCP -> MCPServer; the API is the same
    from mcp.server.mcpserver import MCPServer as FastMCP

from .client import WRITE_METHODS, OSCClient, OSCError
from .config import Config, ConfigError, load_config

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

    Read-only. Use this before osc_write to see the required request body shape.
    """
    try:
        spec = await _get_client().get_spec()
    except OSCError as exc:
        return _err(str(exc), status=exc.status)

    ops = spec.get("paths", {}).get(path)
    if ops is None:
        return _err(f"Path not found in spec: {path}. Try osc_list_endpoints.")

    wanted = method.lower()
    described = {}
    for m, op in ops.items():
        if m.lower() not in {"get", "post", "put", "patch", "delete"}:
            continue
        if wanted and m.lower() != wanted:
            continue
        body_types = None
        rb = op.get("requestBody")
        if rb:
            body_types = list(rb.get("content", {}).keys())
        described[m.upper()] = {
            "summary": op.get("summary"),
            "description": (op.get("description") or "")[:800],
            "parameters": [
                {"name": p.get("name"), "in": p.get("in"), "required": p.get("required", False)}
                for p in op.get("parameters", [])
            ],
            "request_body_content_types": body_types,
            "responses": list(op.get("responses", {}).keys()),
            "is_write": m.upper() in WRITE_METHODS,
        }
    if not described:
        return _err(f"No matching method on {path}.")
    return {"ok": True, "path": path, "operations": described}


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
    """
    method_u = method.upper()
    if method_u not in WRITE_METHODS:
        return _err(f"osc_write only handles {sorted(WRITE_METHODS)}; use osc_get for GET.")

    if _config is None:
        return _err(_config_error or "OSC MCP is not configured.")

    preview = {"method": method_u, "path": path, "query": query, "body": body}

    if not _config.enable_writes:
        return _err(
            "Writes are disabled. Start the server with OSC_ENABLE_WRITES=true to "
            "allow write calls (and only against the intended environment).",
            would_send=preview,
        )

    if not confirm:
        return {
            "ok": True,
            "dry_run": True,
            "would_send": preview,
            "note": "Nothing was sent. Re-call with confirm=true to execute.",
        }

    try:
        client = _get_client()
        result = await client.request(method_u, path, params=query, json_body=body)
        result["dry_run"] = False
        return result
    except OSCError as exc:
        return _err(str(exc), status=exc.status, body=exc.body)


def main() -> None:
    """Console-script / module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
