#!/usr/bin/env python3
"""Generate the markdown semantic-diff report for one incoming artifact.

See ai/skill-management-v1.md §7.1.1 — `semantic-diff` mode.

The report is a deterministic, AI-friendly markdown document. It contains:

  - Header: artifact type, name, source repo, registry presence
  - For single-file artifacts: a unified diff (registry vs incoming).
  - For skills: a per-file diff matrix, including added/removed/changed
    files.
  - A placeholder section "## AI analysis" that the AI fills in when
    `process-incoming` walks the report.

This script does NOT call any LLM. AI reasoning is performed by the
agent running `process-incoming`, who reads the report, the original
artifact, and the incoming artifact and writes the analysis section
inline. Keeping LLM calls out of `reconcile` makes that mode
deterministic and CI-safe.

CLI:
    semantic_diff.py TYPE REGISTRY_PATH INCOMING_PATH [--org O] [--repo R]
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hash_skill
import hash_single_file


def _unified_diff(a_lines: list[str], b_lines: list[str],
                  a_label: str, b_label: str) -> str:
    return "".join(difflib.unified_diff(
        a_lines, b_lines, fromfile=a_label, tofile=b_label, n=3,
    ))


def _read_lines(p: Path | None) -> list[str]:
    if p is None or not p.exists():
        return []
    return p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def _skill_file_inventory(skill_dir: Path | None) -> dict[str, str]:
    """Map of POSIX-relative path -> file hash. Excludes the metadata
    file (consistent with the skill's hash exclude list)."""
    if skill_dir is None or not skill_dir.is_dir():
        return {}
    import hashlib
    out: dict[str, str] = {}
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir).as_posix()
        if rel == "resources/000-metadata.json":
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _diff_skill(reg: Path | None, inc: Path) -> str:
    reg_files = _skill_file_inventory(reg)
    inc_files = _skill_file_inventory(inc)

    all_keys = sorted(set(reg_files) | set(inc_files))
    added, removed, changed, unchanged = [], [], [], []
    for k in all_keys:
        in_reg = k in reg_files
        in_inc = k in inc_files
        if in_reg and not in_inc:
            removed.append(k)
        elif in_inc and not in_reg:
            added.append(k)
        elif reg_files[k] != inc_files[k]:
            changed.append(k)
        else:
            unchanged.append(k)

    lines = []
    lines.append("## File-tree summary")
    lines.append("")
    lines.append(f"- registry files: {len(reg_files)}")
    lines.append(f"- incoming files: {len(inc_files)}")
    lines.append(f"- added (in incoming only): {len(added)}")
    lines.append(f"- removed (in registry only): {len(removed)}")
    lines.append(f"- changed (different hash): {len(changed)}")
    lines.append(f"- unchanged: {len(unchanged)}")
    lines.append("")

    if added:
        lines.append("### Added")
        for k in added:
            lines.append(f"- `{k}`")
        lines.append("")
    if removed:
        lines.append("### Removed")
        for k in removed:
            lines.append(f"- `{k}`")
        lines.append("")
    if changed:
        lines.append("### Changed (unified diffs)")
        lines.append("")
        for k in changed:
            reg_lines = (reg / k).read_text(encoding="utf-8",
                                             errors="replace").splitlines(keepends=True)
            inc_lines = (inc / k).read_text(encoding="utf-8",
                                             errors="replace").splitlines(keepends=True)
            diff = _unified_diff(reg_lines, inc_lines,
                                 f"registry/{k}", f"incoming/{k}")
            lines.append(f"#### `{k}`")
            lines.append("")
            lines.append("```diff")
            lines.append(diff.rstrip("\n"))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def _diff_single_file(reg: Path | None, inc: Path) -> str:
    reg_lines = _read_lines(reg)
    # If incoming has a metadata first line, strip it for diff purposes.
    raw = inc.read_text(encoding="utf-8", errors="replace")
    # Heuristic: if first line parses as JSON object starting with {, strip it.
    inc_lines = raw.splitlines(keepends=True)
    if inc_lines and inc_lines[0].lstrip().startswith("{"):
        try:
            import json
            json.loads(inc_lines[0])
            inc_lines = inc_lines[1:]
        except (json.JSONDecodeError, ValueError):
            pass

    # Also strip metadata line from registry version, if any.
    if reg_lines and reg_lines[0].lstrip().startswith("{"):
        try:
            import json
            json.loads(reg_lines[0])
            reg_lines = reg_lines[1:]
        except (json.JSONDecodeError, ValueError):
            pass

    diff = _unified_diff(reg_lines, inc_lines,
                         "registry" if reg else "/dev/null", "incoming")
    if not diff.strip():
        return "_(no content diff after stripping metadata lines)_\n"
    lines = ["## Unified diff",
             "",
             "```diff",
             diff.rstrip("\n"),
             "```",
             ""]
    return "\n".join(lines)


def run(artifact_type: str, registry_path: Path | None, incoming_path: Path,
        org: str = "?", repo: str = "?") -> str:
    """Generate a semantic-diff report. Returns markdown text."""
    name = incoming_path.stem if incoming_path.is_file() else incoming_path.name
    # Strip pre-ingestion UID for display.
    import re
    m = re.match(
        r"^(?:SKILL-SPEC|ADR|AGENTS-MD)-[0-9a-f]{10}-(?P<n>[a-z0-9][a-z0-9-]*[a-z0-9])$",
        name,
    )
    display_name = m.group("n") if m else name

    lines = []
    lines.append(f"# Semantic diff: `{display_name}` ({artifact_type})")
    lines.append("")
    lines.append(f"- **Source:** `{org}/{repo}`")
    lines.append(f"- **Incoming path:** `{incoming_path}`")
    if registry_path:
        lines.append(f"- **Registry path:** `{registry_path}`")
        if incoming_path.is_dir():
            lines.append(f"- **Registry hash:** `{hash_skill.hash_skill(registry_path)}`")
            lines.append(f"- **Incoming hash:** `{hash_skill.hash_skill(incoming_path)}`")
        else:
            lines.append(f"- **Registry hash:** `{hash_single_file.hash_single_file(registry_path)}`")
            # Incoming may or may not have metadata; use no-metadata for retro form.
            raw = incoming_path.read_bytes()
            first_nl = raw.find(b"\n")
            try:
                if first_nl != -1:
                    import json
                    json.loads(raw[:first_nl].decode("utf-8"))
                    inc_hash = hash_single_file.hash_single_file(incoming_path)
                else:
                    inc_hash = hash_single_file.hash_bytes_no_metadata(raw)
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                inc_hash = hash_single_file.hash_bytes_no_metadata(raw)
            lines.append(f"- **Incoming hash:** `{inc_hash}`")
    else:
        lines.append("- **Registry path:** _(no current registry artifact — add-as-new candidate)_")
    lines.append("")

    if artifact_type == "skill" or (incoming_path.is_dir()):
        lines.append(_diff_skill(registry_path, incoming_path))
    else:
        lines.append(_diff_single_file(registry_path, incoming_path))

    lines.append("## AI analysis")
    lines.append("")
    lines.append(
        "_To be written by the agent running `process-incoming`. Should cover: "
        "what semantically changed, whether structure was reorganized without "
        "content changes, which differences are likely intentional improvements vs. "
        "drift / corruption, and any recommendation on disposition (discard / "
        "replace / merge / add-as-new)._"
    )
    lines.append("")
    lines.append("## Disposition recommendation")
    lines.append("")
    lines.append(
        "_To be written by the agent running `process-incoming`. One of: "
        "`discard`, `replace`, `merge`, `add-as-new`._"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("type")
    ap.add_argument("registry", type=lambda s: None if s in ("-", "") else Path(s))
    ap.add_argument("incoming", type=Path)
    ap.add_argument("--org", default="?")
    ap.add_argument("--repo", default="?")
    args = ap.parse_args()
    sys.stdout.write(run(args.type, args.registry, args.incoming,
                         org=args.org, repo=args.repo))


if __name__ == "__main__":
    main()
