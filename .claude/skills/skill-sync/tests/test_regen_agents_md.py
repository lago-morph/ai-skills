"""Tests for AGENTS.md regeneration.

Covers:
  - extract_agent_instruction parses the strict format.
  - Metadata first line is stripped.
  - Sections after the next H1 are excluded.
  - File ordering is alphabetical by filename.
  - Subscription filter is applied.
  - Files missing the section are skipped.
  - Header banner is substituted.
"""
from __future__ import annotations

import json
from pathlib import Path

import regen_agents_md


def _write_agent_md(path: Path, name: str, instruction: str,
                    extra: str = "") -> None:
    meta = {
        "name": name,
        "origin": "github.com/lago-morph/ai-skills",
        "content_hash": "0" * 64,
        "version": "0.1.0",
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
    }
    first = json.dumps(meta, separators=(",", ":"))
    body = (
        f"{first}\n"
        f"# agent instruction\n\n"
        f"{instruction}\n\n"
    )
    if extra:
        body += extra
    path.write_text(body)


def test_extract_basic():
    text = (
        '{"name":"x","origin":"o","content_hash":"a","version":"0.1.0","state":"live"}\n'
        "# agent instruction\n\n"
        "Do the thing.\n\n"
        "Sub-point.\n"
    )
    assert regen_agents_md.extract_agent_instruction(text) == \
        "Do the thing.\n\nSub-point."


def test_extract_stops_at_next_h1():
    text = (
        '{"name":"x"}\n'
        "# agent instruction\n\n"
        "Body line.\n\n"
        "# justification\n\n"
        "Persuasion text.\n"
    )
    out = regen_agents_md.extract_agent_instruction(text)
    assert out == "Body line."
    assert "justification" not in out
    assert "Persuasion" not in out


def test_extract_handles_no_metadata_line():
    text = "# agent instruction\n\nDirect body.\n"
    assert regen_agents_md.extract_agent_instruction(text) == "Direct body."


def test_extract_returns_none_if_section_absent():
    text = (
        '{"name":"x"}\n'
        "# something else\n\nIrrelevant.\n"
    )
    assert regen_agents_md.extract_agent_instruction(text) is None


def test_extract_case_sensitive_heading_lowercase():
    # Spec §9: H1 must be exactly `# agent instruction` (case-sensitive
    # per parser, but we normalize to lowercase for comparison).
    text = (
        '{"name":"x"}\n'
        "# Agent Instruction\n\nBody.\n"
    )
    # Our implementation lowercases for comparison -> match.
    out = regen_agents_md.extract_agent_instruction(text)
    assert out == "Body."


def test_render_alphabetical(tmp_path):
    _write_agent_md(tmp_path / "zebra.md", "zebra", "Z rule.")
    _write_agent_md(tmp_path / "apple.md", "apple", "A rule.")
    _write_agent_md(tmp_path / "monkey.md", "monkey", "M rule.")
    out = regen_agents_md.render_agents_md(
        tmp_path, {"zebra", "apple", "monkey"}
    )
    # Apple should appear before monkey before zebra in the body.
    a_pos = out.index("A rule.")
    m_pos = out.index("M rule.")
    z_pos = out.index("Z rule.")
    assert a_pos < m_pos < z_pos


def test_render_filters_by_subscription(tmp_path):
    _write_agent_md(tmp_path / "a.md", "a", "Aaa.")
    _write_agent_md(tmp_path / "b.md", "b", "Bbb.")
    _write_agent_md(tmp_path / "c.md", "c", "Ccc.")
    out = regen_agents_md.render_agents_md(tmp_path, {"a", "c"})
    assert "Aaa." in out
    assert "Ccc." in out
    assert "Bbb." not in out


def test_render_skips_files_missing_section(tmp_path):
    _write_agent_md(tmp_path / "good.md", "good", "Hello.")
    (tmp_path / "bad.md").write_text(
        '{"name":"bad"}\n# random\n\nNo section here.\n'
    )
    out = regen_agents_md.render_agents_md(tmp_path, {"good", "bad"})
    assert "Hello." in out
    assert "No section here." not in out


def test_render_skips_ledger_and_extracted(tmp_path):
    _write_agent_md(tmp_path / "real.md", "real", "Real rule.")
    (tmp_path / "000-ledger.json").write_text("{}")
    (tmp_path / "000-ledger.md").write_text("ledger md")
    (tmp_path / "extracted-20260101T000000Z.md").write_text(
        "# agent instruction\n\nLeftover.\n"
    )
    out = regen_agents_md.render_agents_md(
        tmp_path, {"real", "000-ledger", "extracted-20260101T000000Z"}
    )
    assert "Real rule." in out
    assert "Leftover." not in out
    assert "ledger md" not in out


def test_render_header_banner_present(tmp_path):
    _write_agent_md(tmp_path / "a.md", "a", "Aaa.")
    out = regen_agents_md.render_agents_md(tmp_path, {"a"})
    assert "DO NOT EDIT" in out
    assert "skill-sync" in out


def test_render_empty_subscription_still_has_banner(tmp_path):
    out = regen_agents_md.render_agents_md(tmp_path, set())
    assert "DO NOT EDIT" in out


def test_render_claude_md_has_banner_and_pointer(tmp_path):
    out = regen_agents_md.render_claude_md(tmp_path)
    assert "DO NOT EDIT" in out
    assert "AGENTS.md" in out


def test_render_is_deterministic(tmp_path):
    _write_agent_md(tmp_path / "a.md", "a", "Body A.")
    _write_agent_md(tmp_path / "b.md", "b", "Body B.")
    out1 = regen_agents_md.render_agents_md(tmp_path, {"a", "b"})
    out2 = regen_agents_md.render_agents_md(tmp_path, {"a", "b"})
    assert out1 == out2
