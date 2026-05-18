"""Tests for skill-sync config validator."""
from __future__ import annotations

import pytest

import validate


def _valid_config() -> dict:
    return {
        "registry": {"repo": "lago-morph/ai-skills", "ref": "main"},
        "paths": {
            "skills":    ".claude/skills",
            "agents_md": ".claude/agents-md",
            "adrs":      "ai/adr",
        },
        "agents_md_output": {
            "agents_md": "AGENTS.md",
            "claude_md": "CLAUDE.md",
        },
        "subscriptions": {
            "skills":    [{"name": "self-retrospective", "version": "latest"}],
            "agents_md": [],
            "adrs":      [],
        },
    }


def test_valid():
    validate.validate("skill-sync-config", _valid_config())


def test_valid_pinned_semver():
    c = _valid_config()
    c["subscriptions"]["skills"][0]["version"] = "1.2.3"
    validate.validate("skill-sync-config", c)


def test_valid_prerelease_semver():
    c = _valid_config()
    c["subscriptions"]["skills"][0]["version"] = "1.0.0-rc.1"
    validate.validate("skill-sync-config", c)


def test_invalid_version_string():
    c = _valid_config()
    c["subscriptions"]["skills"][0]["version"] = "1.2"
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_invalid_version_word():
    c = _valid_config()
    c["subscriptions"]["skills"][0]["version"] = "newest"
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_invalid_kebab():
    c = _valid_config()
    c["subscriptions"]["skills"][0]["name"] = "Bad_Name"
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_invalid_repo_format():
    c = _valid_config()
    c["registry"]["repo"] = "nothing"
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_missing_subscription_key():
    c = _valid_config()
    del c["subscriptions"]["adrs"]
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_extra_property_rejected():
    c = _valid_config()
    c["extra"] = "not allowed"
    with pytest.raises(Exception):
        validate.validate("skill-sync-config", c)


def test_empty_subscriptions_all_valid():
    c = _valid_config()
    c["subscriptions"] = {"skills": [], "agents_md": [], "adrs": []}
    validate.validate("skill-sync-config", c)
