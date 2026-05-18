"""Tests for hash_skill (Option A)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import hash_skill


def _make_skill(tmp_path: Path, name: str, files: dict[str, bytes]) -> Path:
    skill = tmp_path / name
    skill.mkdir()
    for rel, data in files.items():
        p = skill / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return skill


def _expected_hash(files: dict[str, bytes], exclude: set[str]) -> str:
    tuples = []
    for rel, data in files.items():
        if rel in exclude:
            continue
        tuples.append((rel, hashlib.sha256(data).hexdigest()))
    tuples.sort(key=lambda t: t[0])
    canonical = "".join(f"{p}\n{h}\n" for p, h in tuples).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def test_basic(tmp_path):
    skill = _make_skill(tmp_path, "s", {
        "SKILL.md":           b"# skill\n",
        "scripts/foo.py":     b"print('hi')\n",
        "resources/r.txt":    b"resource\n",
    })
    got = hash_skill.hash_skill(skill, ["resources/000-metadata.json"])
    expected = _expected_hash({
        "SKILL.md":           b"# skill\n",
        "scripts/foo.py":     b"print('hi')\n",
        "resources/r.txt":    b"resource\n",
    }, set())
    assert got == expected


def test_metadata_file_excluded(tmp_path):
    skill = _make_skill(tmp_path, "s", {
        "SKILL.md": b"x",
        "resources/000-metadata.json": b'{"content_hash":"deadbeef"}',
    })
    # Adding the metadata file should NOT affect the hash, because the
    # default exclude list contains it.
    got_with    = hash_skill.hash_skill(skill, ["resources/000-metadata.json"])
    # Remove the metadata file and re-hash; should match.
    (skill / "resources" / "000-metadata.json").unlink()
    got_without = hash_skill.hash_skill(skill, ["resources/000-metadata.json"])
    assert got_with == got_without


def test_rename_changes_hash(tmp_path):
    skill_a = _make_skill(tmp_path, "a", {
        "SKILL.md": b"body",
        "alpha.md": b"content",
    })
    skill_b = _make_skill(tmp_path, "b", {
        "SKILL.md": b"body",
        "beta.md":  b"content",  # same content, different name
    })
    h_a = hash_skill.hash_skill(skill_a, ["resources/000-metadata.json"])
    h_b = hash_skill.hash_skill(skill_b, ["resources/000-metadata.json"])
    # Per spec §3.1 — rename IS a content change. Different hash.
    assert h_a != h_b


def test_directory_reorganization_changes_hash(tmp_path):
    flat = _make_skill(tmp_path, "flat", {
        "SKILL.md": b"hi",
        "a.md":     b"A",
        "b.md":     b"B",
    })
    nested = _make_skill(tmp_path, "nested", {
        "SKILL.md":     b"hi",
        "sub/a.md":     b"A",
        "sub/b.md":     b"B",
    })
    assert hash_skill.hash_skill(flat,   ["resources/000-metadata.json"]) != \
           hash_skill.hash_skill(nested, ["resources/000-metadata.json"])


def test_byte_change_changes_hash(tmp_path):
    s1 = _make_skill(tmp_path, "v1", {"SKILL.md": b"hello"})
    s2 = _make_skill(tmp_path, "v2", {"SKILL.md": b"hellz"})
    assert hash_skill.hash_skill(s1, []) != hash_skill.hash_skill(s2, [])


def test_path_order_independence(tmp_path):
    """Files created in different orders produce the same hash because
    the algorithm sorts before hashing."""
    s1 = _make_skill(tmp_path, "s1", {})
    (s1 / "SKILL.md").write_bytes(b"x")
    (s1 / "z.md").write_bytes(b"z")
    (s1 / "a.md").write_bytes(b"a")

    s2 = _make_skill(tmp_path, "s2", {})
    (s2 / "a.md").write_bytes(b"a")
    (s2 / "SKILL.md").write_bytes(b"x")
    (s2 / "z.md").write_bytes(b"z")

    assert hash_skill.hash_skill(s1, []) == hash_skill.hash_skill(s2, [])
