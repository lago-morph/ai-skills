#!/usr/bin/env python3
"""Skill directory hash (Option A).

See resources/skill-management-v1.md §3.1.

Algorithm:
  1. Walk the directory tree.
  2. Exclude every POSIX-relative path in `hash_exclude` (read from
     `resources/000-metadata.json`, plus an always-implicit
     `resources/000-metadata.json`).
  3. For each remaining file: file_hash = sha256(file_bytes).
  4. Sort (posix_relative_path, file_hash) tuples lex by path.
  5. canonical = "".join(f"{p}\n{h}\n").encode("utf-8")
  6. content_hash = sha256(canonical).hexdigest()
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


METADATA_PATH = "resources/000-metadata.json"


def _read_hash_exclude(skill_dir: Path) -> list[str]:
    meta_path = skill_dir / METADATA_PATH
    if not meta_path.exists():
        return [METADATA_PATH]
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [METADATA_PATH]
    excludes = list(meta.get("hash_exclude", []))
    if METADATA_PATH not in excludes:
        excludes.append(METADATA_PATH)
    return excludes


def hash_skill(skill_dir: Path, hash_exclude: list[str] | None = None) -> str:
    skill_dir = skill_dir.resolve()
    if not skill_dir.is_dir():
        raise NotADirectoryError(skill_dir)
    if hash_exclude is None:
        hash_exclude = _read_hash_exclude(skill_dir)
    exclude = set(hash_exclude)
    tuples: list[tuple[str, str]] = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir).as_posix()
        if rel in exclude:
            continue
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        tuples.append((rel, file_hash))
    tuples.sort(key=lambda t: t[0])
    canonical = "".join(f"{p}\n{h}\n" for p, h in tuples).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


if __name__ == "__main__":
    skill_dir = Path(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2]:
        excludes = sys.argv[2].split(",")
    else:
        excludes = None
    print(hash_skill(skill_dir, excludes))
