#!/usr/bin/env python3
"""Regenerate AGENTS.md from the agents-md directory.

See ai/skill-management-v1.md §7.2.1 (step 5) and §9.

Rules:
  - Read every .md file in the agents-md directory (excluding the
    ledger files 000-ledger.* and any `extracted-*.md` candidates).
  - For each file:
      1. Strip the first line (single-line JSON metadata).
      2. Find the `# agent instruction` H1 section.
      3. Concatenate that section's body (up to but not including the
         next `#` heading) into the output.
  - Sort by filename (alphabetical, posix).
  - Prepend the AGENTS.md banner template with `__AGENTS_MD_DIR__`
    substituted.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"

H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_AGENT_INSTRUCTION_HEADING = "agent instruction"


def _strip_first_line(text: str) -> str:
    nl = text.find("\n")
    if nl == -1:
        return ""
    return text[nl + 1:]


def extract_agent_instruction(file_text: str) -> Optional[str]:
    """Return the body of the `# agent instruction` H1 section, with
    leading/trailing whitespace stripped. None if the section is absent.

    The file is expected to begin with a single-line JSON metadata
    object. If that line is present it is stripped before parsing.
    """
    if file_text.lstrip().startswith("{"):
        # Probably metadata first line — strip it.
        first_nl = file_text.find("\n")
        if first_nl != -1:
            file_text = file_text[first_nl + 1:]

    lines = file_text.splitlines()
    in_target = False
    body: list[str] = []
    for line in lines:
        m = H1_RE.match(line)
        if m:
            heading = m.group(1).strip().lower()
            if in_target:
                # We hit the NEXT H1 — stop collecting.
                break
            if heading == _AGENT_INSTRUCTION_HEADING:
                in_target = True
                continue
            # Some other H1 before we found ours — ignore.
            continue
        if in_target:
            body.append(line)
    if not in_target:
        return None
    return "\n".join(body).strip()


def _is_ledger_or_candidate(name: str) -> bool:
    if name.startswith("000-ledger"):
        return True
    if name.startswith("extracted-") and name.endswith(".md"):
        return True
    return False


def render_agents_md(agents_md_dir: Path, subscribed_names: set[str]) -> str:
    """Render the canonical AGENTS.md.

    `subscribed_names` filters: only files whose stem appears in this
    set are included. Pass `set` of all stems to include everything.
    """
    header_path = RESOURCES_DIR / "agents-md-header.md"
    header = header_path.read_text(encoding="utf-8").replace(
        "__AGENTS_MD_DIR__", agents_md_dir.as_posix()
    )

    pieces: list[str] = [header.rstrip() + "\n"]
    files = sorted(
        p for p in agents_md_dir.glob("*.md")
        if not _is_ledger_or_candidate(p.name)
    )
    for p in files:
        stem = p.stem
        if stem not in subscribed_names:
            continue
        body = extract_agent_instruction(
            p.read_text(encoding="utf-8", errors="replace")
        )
        if not body:
            continue
        pieces.append("")
        pieces.append(body.rstrip())
        pieces.append("")
    return "\n".join(pieces).rstrip() + "\n"


def render_claude_md(agents_md_dir: Path) -> str:
    tpl = (RESOURCES_DIR / "claude-md-template.md").read_text(encoding="utf-8")
    return tpl.replace("__AGENTS_MD_DIR__", agents_md_dir.as_posix())
