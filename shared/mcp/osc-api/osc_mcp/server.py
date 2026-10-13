"""FastMCP server exposing the production OnSite Companion (OSC) API to Claude Code.

Tool surface
------------
Read (safe to allow-list):
  osc_token_info       - environment, granted scope, write switch, live-data check
  osc_list_endpoints   - list endpoints from the OpenAPI spec (filterable)
  osc_describe_endpoint- parameters / request body / responses for one endpoint
  osc_get              - GET any endpoint (supports OData query + body-filter GETs)
  osc_prepare_write    - check a change and word its confirmation; sends nothing
  osc_cancel_write     - discard a prepared change

Write (the only tool that changes OSC; the host keeps it on `ask`):
  osc_confirm_write    - send a prepared change, given its confirmation code and
                         the person's own "yes"; then read it back

The gate itself (approved changes, job check, current values, smallest safe
request, re-check before sending, read-back) is in gate.py.
"""
from __future__ import annotations

import logging
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp >= 2.0 renamed FastMCP -> MCPServer; the API is the same
    from mcp.server.mcpserver import MCPServer as FastMCP

from .client import WRITE_METHODS, OSCClient, OSCError
from .config import Config, ConfigError, load_config
from .gate import Gate, GateError, render
from .spec import SpecView

mcp = FastMCP("osc-api-prod")

# httpx logs every request with its full URL at INFO, which would put the
# production host name in the MCP log. Keep it to warnings.
logging.getLogger("httpx").setLevel(logging.WARNING)

_client: OSCClient | None = None
_gate: Gate | None = None
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


def _get_gate() -> Gate:
    global _gate
    client = _get_client()
    if _gate is None or _gate.client is not client or _gate.config is not _config:
        _gate = Gate(client, _config)
    return _gate


def _err(message: str, **extra: Any) -> dict[str, Any]:
    out = {"ok": False, "error": message}
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def osc_token_info() -> dict[str, Any]:
    """Pre-flight: environment, write switch, granted scope and a live-data check.

    Call this first in any OSC task. `config.environment` must be
    "production" and `live_check.live` must be true; when it is false the
    connection is answering from a stale copy and no change will be written.
    """
    try:
        client = _get_client()
        info = await client.token_info()
        try:
            live = await _get_gate().live_check(force=True)
        except GateError as exc:
            live = {"live": False, "reason": str(exc)}
        return {"ok": True, "config": _config.redacted() if _config else None, "token": info,
                "live_check": live}
    except OSCError as exc:
        return _err(str(exc), status=exc.status, body=exc.body,
                    config=_config.redacted() if _config else None)


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
# Changes: prepare (read-only) -> person replies -> confirm (writes)
# ---------------------------------------------------------------------------
@mcp.tool()
async def osc_prepare_write(
    method: str,
    path: str,
    job_id: str = "",
    body: dict | None = None,
    form: dict[str, str] | None = None,
    files: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Check an OnSite Companion change and word its confirmation. SENDS NOTHING.

    Reads the target from OSC, refuses anything that is not an approved
    contract-intake change, not tied to the named job, ambiguous, or touching a
    protected field (contract price, contract number, region, DataBuild code).
    Works out exactly which fields change, with their current values, and the
    smallest request that changes only those (custom fields are sent as the full
    set so none is dropped).

    Show `confirmation_text` to the person exactly as written and wait for
    their reply. Only after a plain yes, call osc_confirm_write with
    `confirmation_code` and their reply. If they ask for anything different,
    prepare the changed request again: a new check replaces the old code.

    Args:
        method: POST | PATCH | PUT.
        path:   endpoint path with real IDs, e.g. "/api/Jobs/<jobID>".
        job_id: the ID of the job this change is for. Required except when
            creating a new client, person or job.
        body:   JSON fields to change (only the fields being changed).
        form:   message fields: Subject, Body, Documents[0].description.
        files:  message attachments: {"Documents[0].file": "<absolute path under runtime\\>"}.
    """
    if _config is None:
        return _err(_config_error or "OSC MCP is not configured.")
    try:
        gate = _get_gate()
    except OSCError as exc:
        return _err(str(exc))
    plan = await gate.build_plan(method, path, job_id, body, form, files)
    out: dict[str, Any] = {
        "environment": _config.environment,
        "job": plan.job_label or None,
        "change": plan.headline or None,
        "changes": [{k: v for k, v in c.items() if not k.endswith("_shown")} for c in plan.changes],
        "notes": plan.notes,
        "warnings": plan.warnings,
        "blocked": plan.blocked,
        "would_send": {"method": plan.method, "path": plan.path, **plan.request} if plan.request else None,
    }
    if plan.checks:
        out["checks"] = plan.checks
    if plan.blocked:
        out.update(ok=False, confirmation_code=None, confirmation_text=render(plan, _config.environment))
        return out
    text = render(plan, _config.environment)
    if not _config.enable_writes:
        out.update(ok=False, confirmation_code=None, confirmation_text=text,
                   error="Writing to OnSite Companion is switched off for this chat, so this change can be "
                         "shown but not sent.")
        return out
    code = gate.register(plan)
    out.update(ok=True, confirmation_code=code, confirmation_text=text,
               expires_in_minutes=_config.approval_minutes,
               next_step="Show confirmation_text to the person exactly as written. Only after they reply "
                         "with a plain yes, call osc_confirm_write with this code and their reply.")
    return out


@mcp.tool()
async def osc_confirm_write(confirmation_code: str, user_reply: str) -> dict[str, Any]:
    """Send a prepared OnSite Companion change. WRITE - on `ask` in the host.

    Only after the person has read the confirmation from osc_prepare_write
    and answered it. Pass their reply exactly as they typed it. Anything other
    than a plain yes sends nothing ("no" cancels). The target is read again
    first; if anything differs from what they confirmed, nothing is sent and a
    new confirmation comes back to show them. The request sent is the one
    that was prepared, then the record is read back and checked.

    Args:
        confirmation_code: the code osc_prepare_write returned.
        user_reply: the person's own reply to the confirmation, verbatim.
    """
    if _config is None:
        return _err(_config_error or "OSC MCP is not configured.")
    try:
        gate = _get_gate()
    except OSCError as exc:
        return _err(str(exc))
    return await gate.confirm(confirmation_code, user_reply)


@mcp.tool()
async def osc_cancel_write(confirmation_code: str) -> dict[str, Any]:
    """Discard a prepared change (the person said no, or the request is being redone). Sends nothing."""
    if _config is None:
        return _err(_config_error or "OSC MCP is not configured.")
    try:
        gate = _get_gate()
    except OSCError as exc:
        return _err(str(exc))
    found = gate.cancel(confirmation_code)
    return {"ok": True, "cancelled": found,
            "result_text": "Cancelled. Nothing was changed in OnSite Companion." if found else
                           "There was no pending change under that code. Nothing was changed."}


def main() -> None:
    """Console-script / module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
