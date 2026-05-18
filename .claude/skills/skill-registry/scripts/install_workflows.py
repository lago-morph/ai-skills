#!/usr/bin/env python3
"""Install / refresh the skill-registry's GitHub Action workflows.

Run on every invocation of the skill (self-bootstrap, see
ai/skill-management-v1.md §8).

Behavior:
  - For each `.yml` template in `resources/_workflows/`:
      1. Render: substitute `__SKILL_PATH__` with the actual skill path
         relative to the repo root.
      2. Compare to the corresponding file in `.github/workflows/`.
      3. If missing or differing, overwrite.
  - Idempotent on a steady state.

CLI:
    install_workflows.py [--dry-run] [--force]
"""
from __future__ import annotations

import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError(f"no git root above {start}")


def find_skill_path(repo_root: Path) -> str:
    """Return POSIX path of the registry skill, relative to repo root.

    Searches the two well-known locations: `.claude/skills/skill-registry/`
    (authoring) and `/skills/skill-registry/` (after the first sweep folds
    it into the registry). Authoring location wins if both exist (the
    workflow installer should always re-install the most recently edited
    copy).
    """
    candidates = [
        repo_root / ".claude" / "skills" / "skill-registry",
        repo_root / "skills" / "skill-registry",
    ]
    for c in candidates:
        if c.is_dir() and (c / "resources" / "_workflows").is_dir():
            return c.relative_to(repo_root).as_posix()
    raise RuntimeError("skill-registry not found in either known location")


def install(dry_run: bool = False, force: bool = False) -> int:
    here = Path(__file__).resolve().parent
    repo_root = find_repo_root(here)
    skill_path = find_skill_path(repo_root)

    workflows_src = repo_root / skill_path / "resources" / "_workflows"
    workflows_dst = repo_root / ".github" / "workflows"
    workflows_dst.mkdir(parents=True, exist_ok=True)

    changed = 0
    for tpl in sorted(workflows_src.glob("*.yml")):
        text = tpl.read_text(encoding="utf-8")
        rendered = text.replace("__SKILL_PATH__", skill_path)
        dst = workflows_dst / tpl.name
        existing = dst.read_text(encoding="utf-8") if dst.exists() else None
        if existing == rendered and not force:
            continue
        if dry_run:
            print(f"WOULD update {dst.relative_to(repo_root)}")
        else:
            dst.write_text(rendered)
            print(f"updated {dst.relative_to(repo_root)}")
        changed += 1
    return changed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    n = install(dry_run=dry_run, force=force)
    print(f"{n} workflow(s) {'would be ' if dry_run else ''}updated")


if __name__ == "__main__":
    main()
