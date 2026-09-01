r"""Regenerate references/endpoints.md from the live OSC OpenAPI spec.

Run with the osc-api MCP server's venv python, so `osc_mcp` and its
git-ignored `.env` are available:

    <repo>\shared\mcp\osc-api\.venv\Scripts\python.exe `
        .claude\skills\osc-api\scripts\generate_endpoints.py

The spec location comes from OSC_SWAGGER_URL (environment / `.env` beside the
osc-api package). Org guardrail: no server name, address, or credential may
land in the repo — this script writes only paths, methods, summaries,
parameter names, and schema property names, and refuses to write at all if
any host string from the configuration appears in the rendered output.

Regenerate whenever Companion Systems moves the API version; the header of
the output records the spec version it was built from.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from osc_mcp.config import load_config

WRITE_METHODS = {"post", "put", "patch", "delete"}

# Schemas worth carrying property names for. The full component list is much
# larger; widen this tuple and regenerate if another entity becomes relevant.
CORE_SCHEMA_KEYWORDS = (
    "job", "activity", "client", "contact", "variation", "defect",
    "inspection", "document", "alert", "message", "workflow", "location",
)


def main() -> None:
    cfg = load_config()
    if not cfg.swagger_url:
        sys.exit("OSC_SWAGGER_URL is not set; cannot fetch the spec.")
    resp = httpx.get(cfg.swagger_url, verify=cfg.verify_tls, timeout=cfg.timeout)
    resp.raise_for_status()
    spec = resp.json()

    info = spec.get("info", {})
    lines: list[str] = [
        "# OSC API endpoints (generated — do not edit by hand)",
        "",
        f"Built from the OSCAPI OpenAPI spec, version `{info.get('version', '?')}`.",
        "Regenerate with `scripts/generate_endpoints.py` (see its docstring).",
        "Host and credentials are configuration (`OSC_*` env), never recorded here.",
        "",
        "`[WRITE]` marks operations that change the system of record — those go",
        "through `osc_write`, which is gated (see SKILL.md).",
        "",
    ]

    # ---- endpoints, grouped by tag ----------------------------------------
    by_tag: dict[str, list[str]] = {}
    endpoint_count = 0
    for path in sorted(spec.get("paths", {})):
        for method, op in spec["paths"][path].items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            endpoint_count += 1
            tag = (op.get("tags") or ["(untagged)"])[0]
            params = [p.get("name", "?") for p in op.get("parameters", [])]
            bits = [f"`{method.upper()} {path}`"]
            if method.lower() in WRITE_METHODS:
                bits.insert(0, "**[WRITE]**")
            summary = (op.get("summary") or "").strip()
            if summary:
                bits.append(f"— {summary}")
            if params:
                bits.append(f"(params: {', '.join(params)})")
            if "requestBody" in op:
                bits.append("(json body)")
            by_tag.setdefault(tag, []).append("- " + " ".join(bits))

    for tag in sorted(by_tag):
        lines += [f"## {tag}", ""] + by_tag[tag] + [""]

    # ---- core schema property names ----------------------------------------
    # Schema names in this spec are fully-qualified .NET type names; keep only
    # the class name (last dotted segment, '+' nested classes joined with '.').
    def short_name(dotnet_name: str) -> str | None:
        if "`" in dotnet_name:  # generic wrappers (PagedList`1[[...]]) — noise
            return None
        tail = dotnet_name.rsplit(".", 1)[-1]
        return tail.replace("+", ".")

    seen: set[tuple[str, tuple[str, ...]]] = set()
    core: list[tuple[str, list[str]]] = []
    for name, schema in sorted(spec.get("components", {}).get("schemas", {}).items()):
        short = short_name(name)
        props = schema.get("properties")
        if not short or not isinstance(props, dict):
            continue
        if not any(k in short.lower() for k in CORE_SCHEMA_KEYWORDS):
            continue
        key = (short, tuple(sorted(props)))
        if key in seen:
            continue
        seen.add(key)
        core.append((short, list(props)))

    if core:
        lines += [
            "## Core schema fields",
            "",
            "Property names for the entities queries touch most (use with",
            "`$select` / `$filter` / `$orderby`). Full schemas: widen",
            "`CORE_SCHEMA_KEYWORDS` in the generator and re-run.",
            "",
            "Collection GETs wrap results in a paging envelope:",
            "`currentPage, pagedItems, sourceCollectionCount` (or OData",
            "`@odata.context, @odata.count, value`).",
            "",
        ]
        for short, props in sorted(core):
            lines += [f"- **{short}**: {', '.join(props)}"]
        lines.append("")

    text = "\n".join(lines)

    # ---- host-leak guard ----------------------------------------------------
    for url in (cfg.base_url, cfg.swagger_url or ""):
        parsed = urlparse(url)
        for fragment in {parsed.hostname or "", parsed.netloc}:
            if fragment and fragment in text:
                sys.exit("refusing to write: a configured host appears in the output")

    out = Path(__file__).resolve().parent.parent / "references" / "endpoints.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"wrote references/{out.name}: {endpoint_count} endpoints, "
        f"{len(core)} core schemas, spec version {info.get('version', '?')}"
    )


if __name__ == "__main__":
    main()
