#!/usr/bin/env python3
"""Reconcile incoming artifacts.

See ai/skill-management-v1.md §7.1.1 — `reconcile` mode.

For every artifact in /incoming/<org>/<repo>/<type>/<name>(.md|/):
    1. Find the corresponding registry artifact, if any (by name).
    2. Run semantic_diff.run() to produce a markdown report.
    3. Write <name>-semantic-diff.md next to the incoming artifact.

This mode is BATCH and NON-INTERACTIVE. It never modifies the ledger or
the registry artifacts. Idempotent: re-running produces the same reports.

The interactive disposition happens later in `process_incoming.py`.

CLI:
    reconcile.py [--root REPO_ROOT]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import semantic_diff


SINGLE_FILE_TYPES = ("skill-specs", "adrs", "agents-md")


def _report_path_for(incoming_path: Path) -> Path:
    """For an incoming artifact, return where its semantic-diff report
    should live.

    For single-file artifacts (e.g. `incoming/o/r/adrs/foo.md`):
        -> `incoming/o/r/adrs/foo-semantic-diff.md`
    For skills (e.g. `incoming/o/r/skills/foo/`):
        -> `incoming/o/r/skills/foo-semantic-diff.md`  (sibling to dir)
    """
    if incoming_path.is_dir():
        return incoming_path.with_name(incoming_path.name + "-semantic-diff.md")
    stem = incoming_path.stem
    return incoming_path.with_name(f"{stem}-semantic-diff.md")


def _registry_artifact_for(repo_root: Path, type_dir: str, name: str) -> Path | None:
    """Locate the corresponding registry artifact, if any.

    Filename in the registry uses the stripped kebab form. For incoming
    items with a pre-ingestion UID prefix, the caller has already stripped
    the prefix via _kebab_from_filename when computing `name`. Here we just
    look it up.
    """
    if type_dir == "skills":
        p = repo_root / "skills" / name
        return p if p.is_dir() else None
    # Single-file types: try `<name>.md` in the registry directory.
    p = repo_root / type_dir / f"{name}.md"
    return p if p.is_file() else None


def _strip_pre_ingestion_prefix(filename: str) -> str:
    """Mirror of sweep.PRE_INGESTION_RE handling. Single source of truth
    is in sweep.py, this is a local copy for reconcile-only use."""
    import re
    m = re.match(
        r"^(?:SKILL-SPEC|ADR|AGENTS-MD)-[0-9a-f]{10}-(?P<n>[a-z0-9][a-z0-9-]*[a-z0-9])\.md$",
        filename,
    )
    return f"{m.group('n')}.md" if m else filename


def reconcile(repo_root: Path) -> dict:
    summary = {"reports_written": 0, "reports_skipped": 0}
    incoming = repo_root / "incoming"
    if not incoming.exists():
        return summary

    for org_dir in sorted(p for p in incoming.iterdir() if p.is_dir()):
        if org_dir.name == ".gitkeep":
            continue
        for repo_dir in sorted(p for p in org_dir.iterdir() if p.is_dir()):

            # Skills (directories)
            skills_dir = repo_dir / "skills"
            if skills_dir.exists():
                for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
                    name = skill.name
                    report = _report_path_for(skill)
                    if report.exists():
                        summary["reports_skipped"] += 1
                        continue
                    reg = _registry_artifact_for(repo_root, "skills", name)
                    body = semantic_diff.run("skill", reg, skill,
                                             org=org_dir.name, repo=repo_dir.name)
                    report.write_text(body)
                    summary["reports_written"] += 1

            # Single-file types
            for type_dir in SINGLE_FILE_TYPES:
                tdir = repo_dir / type_dir
                if not tdir.exists():
                    continue
                for f in sorted(p for p in tdir.iterdir() if p.is_file()):
                    if f.name.endswith("-semantic-diff.md"):
                        continue
                    stripped = _strip_pre_ingestion_prefix(f.name)
                    name = stripped.rsplit(".md", 1)[0]
                    report = _report_path_for(f)
                    if report.exists():
                        summary["reports_skipped"] += 1
                        continue
                    reg = _registry_artifact_for(repo_root, type_dir, name)
                    body = semantic_diff.run(type_dir, reg, f,
                                             org=org_dir.name, repo=repo_dir.name)
                    report.write_text(body)
                    summary["reports_written"] += 1

    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    repo_root = (Path(args.root).resolve() if args.root
                 else here.parent.parent.parent.parent)

    summary = reconcile(repo_root)
    print(f"reconcile: {summary}")


if __name__ == "__main__":
    main()
