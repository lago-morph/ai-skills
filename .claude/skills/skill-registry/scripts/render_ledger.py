#!/usr/bin/env python3
"""Render a 000-ledger.json to 000-ledger.md.

Designed to run from a GitHub Action triggered on changes to a specific
ledger JSON file. Idempotent: re-running with the same input produces
the same output.

CLI:
    render_ledger.py PATH_TO_LEDGER_JSON
    render_ledger.py --all     # render every 000-ledger.json under cwd

The script:
  1. Loads the ledger.
  2. Validates against the schema.
  3. Re-saves the JSON in canonical form (sorts keys; sorts known arrays
     like versions by semver).
  4. Writes the sibling 000-ledger.md.

Step 3 means the action that triggered on a manual edit also normalizes
the JSON on its way through. Output is byte-stable for unchanged input.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sibling imports work when the script is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_json
import validate as _v


def render_md(ledger: dict) -> str:
    lines: list[str] = []
    artifact_type = ledger["artifact_type"]
    lines.append(f"# Ledger: {artifact_type}")
    lines.append("")
    lines.append("> Auto-generated from `000-ledger.json`. Do not edit by hand.")
    lines.append("")
    items = ledger["items"]
    if not items:
        lines.append("_No items yet._")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Name | Version | State | Description |")
    lines.append("|------|---------|-------|-------------|")
    for name in sorted(items.keys()):
        it = items[name]
        desc = it.get("description", "").replace("\n", " ").replace("|", "\\|")
        state = it["state"]
        if it.get("merged_into"):
            state = f"{state} → `{it['merged_into']}`"
        if it.get("implemented_as"):
            state = f"{state} → `{it['implemented_as']}`"
        lines.append(f"| `{name}` | {it['current_version']} | {state} | {desc} |")
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    for name in sorted(items.keys()):
        it = items[name]
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(f"- **Current version:** `{it['current_version']}`")
        lines.append(f"- **Current hash:** `{it['current_hash']}`")
        lines.append(f"- **State:** `{it['state']}`")
        if it.get("merged_into"):
            lines.append(f"- **Merged into:** `{it['merged_into']}`")
        if it.get("implemented_as"):
            lines.append(f"- **Implemented as:** `{it['implemented_as']}`")
        if it.get("name_clash"):
            joined = ", ".join(f"`{n}`" for n in it["name_clash"])
            lines.append(f"- **Name-clash pointers:** {joined}")
        lines.append("")
        lines.append(f"  {it.get('description', '')}")
        lines.append("")
        lines.append("  **Version history:**")
        lines.append("")
        for v in it["versions"]:
            lines.append(
                f"  - `{v['version']}` — hash `{v['hash']}` "
                f"(commit `{v['commit']}`)"
            )
        if it.get("discarded_hashes"):
            lines.append("")
            lines.append("  **Discarded hashes:**")
            lines.append("")
            for h in it["discarded_hashes"]:
                lines.append(f"  - `{h}`")
        lines.append("")
    return "\n".join(lines)


def render_one(json_path: Path) -> None:
    ledger = canonical_json.load(json_path)
    _v.validate("ledger", ledger)
    # Re-save in canonical form (idempotent if already canonical).
    canonical_json.write(json_path, ledger)
    md_path = json_path.with_name("000-ledger.md")
    md_path.write_text(render_md(ledger))


def render_all(root: Path) -> int:
    count = 0
    for p in root.rglob("000-ledger.json"):
        # Skip anything inside _workflows, schemas, etc.
        if any(part.startswith(".") for part in p.parts if part != "."):
            # Allow .claude/skills hits but skip dotfiles/dot-dirs in general.
            pass
        render_one(p)
        count += 1
    return count


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: render_ledger.py PATH | --all")
    if sys.argv[1] == "--all":
        n = render_all(Path.cwd())
        print(f"rendered {n} ledger(s)")
    else:
        render_one(Path(sys.argv[1]))
        print("ok")


if __name__ == "__main__":
    main()
