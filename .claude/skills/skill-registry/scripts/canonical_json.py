#!/usr/bin/env python3
"""Canonical JSON dumper used by every v1 script that writes JSON.

Rules (see ai/skill-management-v1.md §6):
  - Object keys sorted recursively (lexicographic). Same axis as `jq -S`.
  - Arrays at known JSON-pointer paths are sorted per spec; others are
    left as-is (preserves semantic order in `repos`, `subscriptions.*`,
    etc.).
  - 2-space indentation, trailing newline, UTF-8, ensure_ascii=False.

The path spec uses "/" as the segment separator and "*" as a wildcard for
any object key. Array elements are matched with "*" at that depth.

Use:
    import canonical_json
    canonical_json.write(Path("foo.json"), data)
    s = canonical_json.dumps(data)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable


_SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.\-]+))?$"
)


def _semver_key(s: str) -> tuple:
    m = _SEMVER_RE.match(s)
    if not m:
        return (0, 0, 0, "")
    major = int(m["major"])
    minor = int(m["minor"])
    patch = int(m["patch"])
    # No prerelease ranks higher than any prerelease; use "~" sentinel.
    pre = m["pre"] or "~"
    return (major, minor, patch, pre)


def _version_obj_key(obj: dict) -> tuple:
    return _semver_key(obj.get("version", ""))


# JSON-pointer paths -> sort key function on each element.
ARRAY_SORTS: dict[str, Callable[[Any], Any]] = {
    "/items/*/versions": _version_obj_key,
    "/items/*/discarded_hashes": lambda s: s,
    "/items/*/name_clash": lambda s: s,
    "/hash_exclude": lambda s: s,
}


def _path_matches(spec: str, actual: str) -> bool:
    s = spec.strip("/").split("/")
    a = actual.strip("/").split("/")
    if len(s) != len(a):
        return False
    return all(sp == "*" or sp == ap for sp, ap in zip(s, a))


def _canon(node: Any, path: str) -> Any:
    if isinstance(node, dict):
        return {k: _canon(node[k], f"{path}/{k}") for k in sorted(node.keys())}
    if isinstance(node, list):
        children = [_canon(item, f"{path}/*") for item in node]
        for spec, keyfn in ARRAY_SORTS.items():
            if _path_matches(spec, path):
                # Sort using the per-spec keyfn applied to the (already-canonicalized) element.
                return sorted(children, key=keyfn)
        return children
    return node


def dumps(obj: Any) -> str:
    """Return canonical JSON string (with trailing newline)."""
    return json.dumps(_canon(obj, ""), indent=2, ensure_ascii=False) + "\n"


def dump(obj: Any, fp) -> None:
    fp.write(dumps(obj))


def write(path: Path, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        dump(obj, f)


def load(path: Path) -> Any:
    """Plain read. Validation is the caller's job."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys

    data = json.load(sys.stdin)
    sys.stdout.write(dumps(data))
