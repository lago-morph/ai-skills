#!/usr/bin/env python3
"""Schema validator for skill-sync config."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: `jsonschema` is required.\n")
    sys.exit(2)


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "resources" / "schemas"


def _load_schema(name: str) -> dict:
    with open(SCHEMA_DIR / f"{name}.schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


def validate(kind: str, instance: Any) -> None:
    schema = _load_schema(kind)
    jsonschema.validate(instance=instance, schema=schema)


def validate_file(kind: str, path: Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate(kind, data)


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: validate.py KIND PATH")
    try:
        validate_file(sys.argv[1], Path(sys.argv[2]))
    except (jsonschema.ValidationError, json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"FAIL {sys.argv[1]} {sys.argv[2]}: {e}\n")
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
