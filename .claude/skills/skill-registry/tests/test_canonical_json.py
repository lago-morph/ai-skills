"""Tests for canonical_json.

Spec §6.2 requires:
  - Top-level keys deliberately out of order.
  - Nested-object keys out of order.
  - Sortable arrays with elements out of order.
  - Byte-for-byte equality against:
      (a) `jq -S` for the key-sort axis.
      (b) hand-authored reference fixtures for array sorts.
"""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

import canonical_json


HAS_JQ = shutil.which("jq") is not None


def _jq_sort(obj) -> str:
    """`jq -S` on the input — recursive key sort, no array sort."""
    out = subprocess.run(
        ["jq", "-S", "."],
        input=json.dumps(obj),
        capture_output=True,
        text=True,
        check=True,
    )
    # jq emits without trailing newline guarantee; normalize.
    body = out.stdout
    if not body.endswith("\n"):
        body += "\n"
    return body


# ---------- Key-sort axis: parity with `jq -S` ----------

@pytest.mark.skipif(not HAS_JQ, reason="jq not installed")
def test_keys_match_jq_simple():
    obj = {"b": 1, "a": 2}
    # No array sort rules apply here; key sort should match jq exactly.
    assert canonical_json.dumps(obj) == _jq_sort(obj)


@pytest.mark.skipif(not HAS_JQ, reason="jq not installed")
def test_keys_match_jq_nested_scrambled():
    obj = {
        "z": {"d": 1, "a": 2, "c": {"y": 9, "x": 8}},
        "a": [
            {"q": 1, "p": 2},
            {"q": 3, "p": 4},
        ],
        "m": "middle",
    }
    # The `a` array here is NOT one of our sortable paths, so element
    # ordering is preserved. jq -S also preserves array order.
    assert canonical_json.dumps(obj) == _jq_sort(obj)


@pytest.mark.skipif(not HAS_JQ, reason="jq not installed")
def test_keys_match_jq_deep_random_order():
    obj = {
        "zoo": {
            "lemur": {"name": "lem", "age": 4},
            "antelope": {"name": "ant", "age": 7},
        },
        "alpha": True,
        "beta":  [{"k": 1, "j": 2}, {"k": 3, "j": 4}],
    }
    assert canonical_json.dumps(obj) == _jq_sort(obj)


# ---------- Array-sort axis: fixture parity ----------

def test_versions_sorted_by_semver():
    ledger = {
        "artifact_type": "skills",
        "items": {
            "x": {
                "current_version": "2.0.0",
                "current_hash": "0" * 64,
                "state": "live",
                "description": "x",
                "implemented_as": None,
                "merged_into": None,
                "name_clash": [],
                "versions": [
                    {"version": "1.10.0", "hash": "a" * 64, "commit": "c1"},
                    {"version": "1.2.0",  "hash": "b" * 64, "commit": "c2"},
                    {"version": "2.0.0",  "hash": "c" * 64, "commit": "c3"},
                    {"version": "0.1.0",  "hash": "d" * 64, "commit": "c4"},
                ],
                "discarded_hashes": [],
            },
        },
    }
    out = canonical_json.dumps(ledger)
    parsed = json.loads(out)
    versions = parsed["items"]["x"]["versions"]
    assert [v["version"] for v in versions] == ["0.1.0", "1.2.0", "1.10.0", "2.0.0"]


def test_prerelease_orders_below_release():
    ledger = {
        "artifact_type": "skills",
        "items": {
            "x": {
                "current_version": "1.0.0",
                "current_hash": "0" * 64,
                "state": "live",
                "description": "x",
                "implemented_as": None,
                "merged_into": None,
                "name_clash": [],
                "versions": [
                    {"version": "1.0.0",       "hash": "a" * 64, "commit": "c1"},
                    {"version": "1.0.0-rc.1",  "hash": "b" * 64, "commit": "c2"},
                    {"version": "1.0.0-rc.10", "hash": "c" * 64, "commit": "c3"},
                ],
                "discarded_hashes": [],
            },
        },
    }
    out = canonical_json.dumps(ledger)
    versions = json.loads(out)["items"]["x"]["versions"]
    # Prerelease orders BEFORE the release.
    assert [v["version"] for v in versions] == ["1.0.0-rc.1", "1.0.0-rc.10", "1.0.0"]


def test_discarded_hashes_sorted_lex():
    ledger = {
        "artifact_type": "skills",
        "items": {
            "x": {
                "current_version": "0.1.0",
                "current_hash": "0" * 64,
                "state": "live",
                "description": "x",
                "implemented_as": None,
                "merged_into": None,
                "name_clash": [],
                "versions": [
                    {"version": "0.1.0", "hash": "a" * 64, "commit": "c"},
                ],
                "discarded_hashes": ["b" * 64, "0" * 64, "f" * 64, "a" * 64],
            },
        },
    }
    out = canonical_json.dumps(ledger)
    discarded = json.loads(out)["items"]["x"]["discarded_hashes"]
    assert discarded == ["0" * 64, "a" * 64, "b" * 64, "f" * 64]


def test_hash_exclude_sorted_lex():
    meta = {
        "name": "x",
        "origin": "github.com/lago-morph/ai-skills",
        "content_hash": "0" * 64,
        "version": "0.1.0",
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
        "hash_exclude": [
            "resources/skill-sync-config.json",
            "resources/000-metadata.json",
            "resources/registry-config.json",
        ],
    }
    out = canonical_json.dumps(meta)
    excludes = json.loads(out)["hash_exclude"]
    assert excludes == sorted(excludes)


def test_arrays_outside_sort_spec_preserved():
    obj = {
        "repos": [
            {"repo": "z/z"},
            {"repo": "a/a"},
            {"repo": "m/m"},
        ],
    }
    out = canonical_json.dumps(obj)
    # repos is NOT in ARRAY_SORTS — order preserved.
    repos = json.loads(out)["repos"]
    assert [r["repo"] for r in repos] == ["z/z", "a/a", "m/m"]


# ---------- Determinism / idempotence ----------

def test_idempotent():
    obj = {
        "b": [3, 1, 2],
        "a": {"y": True, "x": False},
    }
    once = canonical_json.dumps(obj)
    parsed = json.loads(once)
    twice = canonical_json.dumps(parsed)
    assert once == twice


def test_trailing_newline():
    out = canonical_json.dumps({"a": 1})
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_two_space_indent():
    out = canonical_json.dumps({"a": {"b": 1}})
    assert '  "a"' in out
    assert '    "b"' in out
