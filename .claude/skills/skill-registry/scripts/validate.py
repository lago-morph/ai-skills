#!/usr/bin/env python3
"""Validate JSON files against the skill-registry schemas.

Used both as a library (called by every script that reads or writes a
config/ledger/metadata file) and as a CLI for CI.

CLI:
    validate.py ledger PATH
    validate.py skill-metadata PATH
    validate.py single-file-metadata PATH
    validate.py registry-config PATH

Each prints "ok" and exits 0 on success, prints the error and exits 1
on failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: `jsonschema` is required. Install with `pip install jsonschema`.\n"
    )
    sys.exit(2)


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "resources" / "schemas"

_SCHEMA_FILES = {
    "ledger": "ledger.schema.json",
    "skill-metadata": "skill-metadata.schema.json",
    "single-file-metadata": "single-file-metadata.schema.json",
    "registry-config": "registry-config.schema.json",
}


def _load_schema(kind: str) -> dict:
    schema_path = SCHEMA_DIR / _SCHEMA_FILES[kind]
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(kind: str, instance: Any) -> None:
    """Raise jsonschema.ValidationError if invalid."""
    if kind not in _SCHEMA_FILES:
        raise ValueError(f"unknown schema kind: {kind}")
    schema = _load_schema(kind)
    jsonschema.validate(instance=instance, schema=schema)


def validate_file(kind: str, path: Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate(kind, data)


def validate_first_line_metadata(path: Path) -> None:
    """Validate the single-line JSON metadata of a single-file artifact."""
    with open(path, "rb") as f:
        first = f.readline().decode("utf-8").rstrip("\n")
    data = json.loads(first)
    validate("single-file-metadata", data)


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    kind = sys.argv[1]
    path = Path(sys.argv[2])
    try:
        if kind == "single-file-metadata":
            validate_first_line_metadata(path)
        else:
            validate_file(kind, path)
    except (jsonschema.ValidationError, json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"FAIL {kind} {path}: {e}\n")
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
