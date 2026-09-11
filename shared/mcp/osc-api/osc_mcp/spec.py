"""Local OpenAPI references for payload discovery; never fetch external refs."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import unquote


def route_pattern(route: str) -> str:
    """Regex for a spec route: literal segments escaped, `{param}` segments wildcarded."""
    return "/".join(
        "[^/]+" if part.startswith("{") and part.endswith("}") else re.escape(part)
        for part in route.split("/")
    )


def find_operation(spec: dict[str, Any], view: "SpecView", path: str, method: str
                   ) -> tuple[str | None, dict[str, Any]]:
    """Match a concrete request path (IDs filled in) to its spec route and operation.

    Returns (route, operation). A literal route beats a parameterised one, and
    among parameterised routes the one with fewer parameters wins. (None, {})
    when no route matches; (route, {}) when the route has no such method.
    """
    candidates = []
    for route, operations in spec.get("paths", {}).items():
        if re.fullmatch(route_pattern(route), path):
            ops = view.resolve(operations) if "$ref" in operations else operations
            candidates.append((route, ops))
    if not candidates:
        return None, {}
    candidates.sort(key=lambda item: (item[0] != path, item[0].count("{")))
    route, ops = candidates[0]
    return route, ops.get(method.lower(), {})


class SpecView:
    def __init__(self, spec: dict[str, Any]):
        self.spec = spec
        self.definitions: dict[str, Any] = {}
        self.unresolved: dict[str, str] = {}

    def lookup(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            self.unresolved[ref] = "external"
            return None
        node = self.spec
        try:
            for key in unquote(ref[2:]).split("/"):
                node = node[key.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            self.unresolved[ref] = "missing"
            return None
        return node

    def collect(self, node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref not in self.definitions and ref not in self.unresolved:
                target = self.lookup(ref)
                if target is not None:
                    self.definitions[ref] = deepcopy(target)
                    self.collect(target)
            for value in node.values():
                self.collect(value)
        elif isinstance(node, list):
            for value in node:
                self.collect(value)

    def resolve(self, node: dict[str, Any]) -> dict[str, Any]:
        """Dereference an object while leaving nested schemas as named refs."""
        self.collect(node)
        result = deepcopy(node)
        seen: set[str] = set()
        while isinstance(result.get("$ref"), str):
            ref = result["$ref"]
            if ref in seen:
                break
            seen.add(ref)
            target = self.lookup(ref)
            if not isinstance(target, dict):
                break
            result = {**deepcopy(target), **{k: v for k, v in result.items() if k != "$ref"}}
        return result
