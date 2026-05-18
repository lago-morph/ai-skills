"""Tests for the schema validators."""
from __future__ import annotations

import pytest

import validate


# ---------- ledger ----------

def _valid_ledger() -> dict:
    return {
        "artifact_type": "skills",
        "items": {
            "foo": {
                "current_version": "1.2.0",
                "current_hash": "a" * 64,
                "state": "live",
                "description": "A test skill.",
                "implemented_as": None,
                "merged_into": None,
                "name_clash": [],
                "versions": [
                    {"version": "1.2.0", "hash": "a" * 64, "commit": "deadbeef"},
                ],
                "discarded_hashes": [],
            },
        },
    }


def test_ledger_valid_minimal():
    validate.validate("ledger", _valid_ledger())


def test_ledger_bad_artifact_type():
    bad = _valid_ledger()
    bad["artifact_type"] = "nonsense"
    with pytest.raises(Exception):
        validate.validate("ledger", bad)


def test_ledger_bad_state():
    bad = _valid_ledger()
    bad["items"]["foo"]["state"] = "active"
    with pytest.raises(Exception):
        validate.validate("ledger", bad)


def test_ledger_bad_hash_length():
    bad = _valid_ledger()
    bad["items"]["foo"]["current_hash"] = "a" * 63
    with pytest.raises(Exception):
        validate.validate("ledger", bad)


def test_ledger_bad_semver():
    bad = _valid_ledger()
    bad["items"]["foo"]["current_version"] = "1.2"
    with pytest.raises(Exception):
        validate.validate("ledger", bad)


def test_ledger_accepts_prerelease():
    ok = _valid_ledger()
    ok["items"]["foo"]["current_version"] = "1.0.0-rc.1"
    ok["items"]["foo"]["versions"] = [
        {"version": "1.0.0-rc.1", "hash": "a" * 64, "commit": "x"},
    ]
    validate.validate("ledger", ok)


def test_ledger_empty_items_allowed():
    validate.validate("ledger", {"artifact_type": "adrs", "items": {}})


# ---------- registry-config ----------

def _valid_registry_config() -> dict:
    return {
        "defaults": {
            "skills":      [".claude/skills/*/"],
            "agents_md":   [".claude/agents-md/*.md"],
            "adrs":        ["ai/adr/*.md"],
            "skill_specs": ["retrospective/*/SKILL-SPEC-*.md"],
        },
        "repos": [{"repo": "lago-morph/ai-skills"}],
    }


def test_registry_config_valid():
    validate.validate("registry-config", _valid_registry_config())


def test_registry_config_bad_repo_format():
    bad = _valid_registry_config()
    bad["repos"][0]["repo"] = "not-a-slug"
    with pytest.raises(Exception):
        validate.validate("registry-config", bad)


def test_registry_config_per_repo_paths_partial():
    """Per-key replace allowed — repo can override one path and omit others."""
    ok = _valid_registry_config()
    ok["repos"].append({
        "repo": "owner/other",
        "paths": {"skills": ["custom/path/*/"]},
    })
    validate.validate("registry-config", ok)


# ---------- skill metadata ----------

def test_skill_metadata_valid():
    validate.validate("skill-metadata", {
        "name": "self-retrospective",
        "origin": "github.com/lago-morph/ai-skills",
        "content_hash": "f" * 64,
        "version": "0.1.0",
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
        "hash_exclude": ["resources/000-metadata.json"],
    })


def test_skill_metadata_extra_field_rejected():
    with pytest.raises(Exception):
        validate.validate("skill-metadata", {
            "name": "x",
            "origin": "y",
            "content_hash": "f" * 64,
            "version": "0.1.0",
            "state": "live",
            "hash_exclude": [],
            "extra": "nope",
        })
