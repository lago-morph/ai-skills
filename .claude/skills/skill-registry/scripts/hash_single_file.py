#!/usr/bin/env python3
"""Single-file artifact hash.

See ai/skill-management-v1.md §3.2.

Strip first line, sha256 the remainder.

Also offers a modification check: read the first line as JSON metadata,
extract `content_hash`, recompute, compare. Mismatch -> the artifact was
edited downstream without going through the registry process.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def strip_first_line(data: bytes) -> bytes:
    nl = data.find(b"\n")
    if nl == -1:
        return b""
    return data[nl + 1:]


def hash_single_file(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(strip_first_line(data)).hexdigest()


def hash_bytes_no_metadata(content_bytes: bytes) -> str:
    """For raw, metadata-less content (e.g. pre-ingestion). Hashes as-is."""
    return hashlib.sha256(content_bytes).hexdigest()


def read_metadata(path: Path) -> dict:
    data = path.read_bytes()
    nl = data.find(b"\n")
    if nl == -1:
        raise ValueError(f"{path}: no newline; cannot extract metadata line")
    line = data[:nl].decode("utf-8")
    return json.loads(line)


def is_unmodified(path: Path) -> bool:
    """True if hash of (strip first line + remainder) matches stored
    content_hash in the metadata line."""
    meta = read_metadata(path)
    stored = meta.get("content_hash")
    if not stored:
        return False
    return hash_single_file(path) == stored


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: hash_single_file.py PATH [--check]")
    path = Path(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--check":
        ok = is_unmodified(path)
        print("ok" if ok else "modified")
        sys.exit(0 if ok else 1)
    print(hash_single_file(path))
