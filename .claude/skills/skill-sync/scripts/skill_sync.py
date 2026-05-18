#!/usr/bin/env python3
"""Sync subscribed artifacts from the ai-skills registry into the
current (consumer) repository.

See resources/skill-management-v1.md §7.2.

CLI:
    skill_sync.py [--config PATH] [--no-clone] [--registry-clone PATH]
                  [--dry-run]

Algorithm:
  1. Ensure `skill-sync-config.json` exists; copy the Claude template
     into place if it does not.
  2. Load config, schema-lint.
  3. Clone the registry repo to /tmp (unless --registry-clone provided).
  4. Load all four registry ledgers (validated against the registry's
     ledger schema).
  5. For each subscribed item, in (skills, agents_md, adrs) order:
       a. Resolve version to a specific (version, commit, hash).
       b. Compare to local. Install / upgrade / clash / noop.
       c. Emit warnings for `deprecated` (latest only) and for
          `merged` / `implemented` items.
  6. If subscriptions.agents_md is non-empty, regenerate AGENTS.md and
     CLAUDE.md. Capture any inline diffs into
     `<paths.agents_md>/extracted-<UTC>.md`.

Returns a structured report (also printed) so the agent can summarize
to the user.

This script is fully deterministic and does NOT call any LLM. Any
human-in-the-loop decisions (name clashes, "should I overwrite this")
are surfaced as items in the report; the agent then drives those with
AskUserQuestion and re-invokes the relevant disposition helper.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_json
import regen_agents_md
import validate as _v


RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources"


@dataclass
class SyncReport:
    installed: list[dict] = field(default_factory=list)
    upgraded:  list[dict] = field(default_factory=list)
    noop:      list[dict] = field(default_factory=list)
    name_clashes: list[dict] = field(default_factory=list)
    deprecated_warnings: list[dict] = field(default_factory=list)
    merged_warnings: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)
    agents_md_regenerated: bool = False
    agents_md_extracted_path: Optional[str] = None
    claude_md_regenerated: bool = False
    claude_md_extracted_path: Optional[str] = None


def _ensure_user_config(repo_root: Path) -> Path:
    """Make sure skill-sync-config.json exists alongside the templates."""
    user = RESOURCES_DIR / "skill-sync-config.json"
    if user.exists():
        return user
    tpl = RESOURCES_DIR / "skill-sync-config-template-claude.json"
    shutil.copyfile(tpl, user)
    return user


def _clone_registry(registry_repo: str, ref: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="skill-sync-registry-"))
    subprocess.run(
        ["git", "clone", "--quiet", f"https://github.com/{registry_repo}.git",
         str(tmp)],
        check=True,
    )
    if ref != "main":
        subprocess.run(["git", "checkout", "--quiet", ref], cwd=tmp, check=True)
    return tmp


def _load_registry_ledger(registry_root: Path, artifact_type: str) -> dict:
    p = registry_root / artifact_type / "000-ledger.json"
    if not p.exists():
        return {"artifact_type": artifact_type, "items": {}}
    return canonical_json.load(p)


def _resolve_version(ledger: dict, name: str, version: str) -> Optional[dict]:
    """Return a dict with `version`, `hash`, `commit` for the requested
    version, or None if missing."""
    items = ledger.get("items", {})
    entry = items.get(name)
    if entry is None:
        return None
    if version == "latest":
        return {
            "version": entry["current_version"],
            "hash":    entry["current_hash"],
            "commit":  entry["versions"][-1]["commit"] if entry["versions"] else "?",
            "state":   entry["state"],
            "description": entry.get("description", ""),
            "merged_into": entry.get("merged_into"),
            "implemented_as": entry.get("implemented_as"),
        }
    for v in entry["versions"]:
        if v["version"] == version:
            return {
                "version": v["version"],
                "hash":    v["hash"],
                "commit":  v["commit"],
                "state":   entry["state"],
                "description": entry.get("description", ""),
                "merged_into": entry.get("merged_into"),
                "implemented_as": entry.get("implemented_as"),
            }
    return None


def _fetch_single_file_at_commit(registry_root: Path, commit: str,
                                  artifact_type: str, name: str) -> Optional[bytes]:
    """Fetch the bytes of <artifact_type>/<name>.md at the given commit."""
    rel = f"{artifact_type}/{name}.md"
    try:
        out = subprocess.run(
            ["git", "show", f"{commit}:{rel}"],
            cwd=registry_root,
            check=True,
            capture_output=True,
        )
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def _fetch_skill_at_commit(registry_root: Path, commit: str,
                           name: str) -> Optional[Path]:
    """Materialize the skill `name` at the given commit into a tmp dir
    and return that path. Uses `git archive`."""
    tmp = Path(tempfile.mkdtemp(prefix="skill-sync-fetch-"))
    rel = f"skills/{name}"
    try:
        archive = subprocess.run(
            ["git", "archive", commit, rel],
            cwd=registry_root,
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError:
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    # Pipe the archive into tar -x in tmp.
    proc = subprocess.run(
        ["tar", "-x", "-C", str(tmp)],
        input=archive,
        check=True,
    )
    materialized = tmp / rel
    if not materialized.exists():
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    return materialized


def _local_origin(metadata_path: Path) -> Optional[str]:
    if not metadata_path.exists():
        return None
    try:
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return meta.get("origin")


def _local_hash_skill(skill_dir: Path) -> Optional[str]:
    """Read content_hash from the local skill's metadata, if any."""
    mp = skill_dir / "resources" / "000-metadata.json"
    if not mp.exists():
        return None
    try:
        meta = json.loads(mp.read_text(encoding="utf-8"))
        return meta.get("content_hash")
    except (OSError, json.JSONDecodeError):
        return None


def _local_hash_single(file_path: Path) -> Optional[str]:
    if not file_path.exists():
        return None
    try:
        with open(file_path, "rb") as f:
            line = f.readline().decode("utf-8")
        meta = json.loads(line)
        return meta.get("content_hash")
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _install_skill(materialized: Path, dest_dir: Path) -> None:
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(materialized, dest_dir)


def _install_single_file(content: bytes, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)


def _sync_skills(repo_root: Path, registry_root: Path, config: dict,
                 ledger: dict, report: SyncReport) -> None:
    skills_dir = repo_root / config["paths"]["skills"]
    for sub in config["subscriptions"]["skills"]:
        name = sub["name"]
        wanted_ver = sub["version"]
        resolved = _resolve_version(ledger, name, wanted_ver)
        if resolved is None:
            report.missing.append({"type": "skill", "name": name,
                                   "version": wanted_ver})
            continue

        # Warnings on state.
        if resolved["state"] == "deprecated" and wanted_ver == "latest":
            report.deprecated_warnings.append({
                "type": "skill", "name": name,
                "description": resolved["description"],
            })
        if resolved["state"] in ("merged", "implemented"):
            report.merged_warnings.append({
                "type": "skill", "name": name,
                "state": resolved["state"],
                "merged_into": resolved.get("merged_into"),
                "implemented_as": resolved.get("implemented_as"),
            })

        dest = skills_dir / name
        local_hash = _local_hash_skill(dest)
        local_meta = dest / "resources" / "000-metadata.json"
        local_origin = _local_origin(local_meta)

        if dest.exists() and local_origin is None:
            # Name clash: same kebab, but no ai-skills origin metadata.
            report.name_clashes.append({
                "type": "skill", "name": name,
                "local_path": str(dest.relative_to(repo_root)),
                "registry_description": resolved["description"],
                "registry_version": resolved["version"],
                "registry_hash": resolved["hash"],
            })
            continue

        if local_hash == resolved["hash"]:
            report.noop.append({"type": "skill", "name": name,
                                "version": resolved["version"]})
            continue

        # Fetch and install.
        materialized = _fetch_skill_at_commit(
            registry_root, resolved["commit"], name
        )
        if materialized is None:
            report.missing.append({"type": "skill", "name": name,
                                   "version": resolved["version"]})
            continue
        _install_skill(materialized, dest)
        if local_hash is None:
            report.installed.append({"type": "skill", "name": name,
                                     "version": resolved["version"]})
        else:
            report.upgraded.append({"type": "skill", "name": name,
                                    "from_hash": local_hash,
                                    "to_version": resolved["version"]})


def _sync_single_files(repo_root: Path, registry_root: Path, config: dict,
                       ledger: dict, kind: str, sub_key: str,
                       artifact_dir_key: str, type_dir: str,
                       report: SyncReport) -> None:
    base = repo_root / config["paths"][artifact_dir_key]
    for sub in config["subscriptions"][sub_key]:
        name = sub["name"]
        wanted_ver = sub["version"]
        resolved = _resolve_version(ledger, name, wanted_ver)
        if resolved is None:
            report.missing.append({"type": kind, "name": name,
                                   "version": wanted_ver})
            continue

        if resolved["state"] == "deprecated" and wanted_ver == "latest":
            report.deprecated_warnings.append({
                "type": kind, "name": name,
                "description": resolved["description"],
            })
        if resolved["state"] in ("merged", "implemented"):
            report.merged_warnings.append({
                "type": kind, "name": name,
                "state": resolved["state"],
                "merged_into": resolved.get("merged_into"),
                "implemented_as": resolved.get("implemented_as"),
            })

        dest = base / f"{name}.md"
        local_hash = _local_hash_single(dest)
        local_origin = None
        if dest.exists():
            try:
                with open(dest, "rb") as f:
                    line = f.readline().decode("utf-8")
                local_origin = json.loads(line).get("origin")
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                local_origin = None

        if dest.exists() and local_origin is None:
            report.name_clashes.append({
                "type": kind, "name": name,
                "local_path": str(dest.relative_to(repo_root)),
                "registry_description": resolved["description"],
                "registry_version": resolved["version"],
                "registry_hash": resolved["hash"],
            })
            continue

        if local_hash == resolved["hash"]:
            report.noop.append({"type": kind, "name": name,
                                "version": resolved["version"]})
            continue

        content = _fetch_single_file_at_commit(
            registry_root, resolved["commit"], type_dir, name
        )
        if content is None:
            report.missing.append({"type": kind, "name": name,
                                   "version": resolved["version"]})
            continue
        _install_single_file(content, dest)
        if local_hash is None:
            report.installed.append({"type": kind, "name": name,
                                     "version": resolved["version"]})
        else:
            report.upgraded.append({"type": kind, "name": name,
                                    "from_hash": local_hash,
                                    "to_version": resolved["version"]})


def _regen_agents_md_files(repo_root: Path, config: dict,
                           report: SyncReport) -> None:
    """If agents_md subscription is non-empty, regenerate AGENTS.md and
    CLAUDE.md per spec §7.2.1 (steps 5-6)."""
    subs = config["subscriptions"]["agents_md"]
    if not subs:
        return

    agents_md_dir = repo_root / config["paths"]["agents_md"]
    agents_md_path = repo_root / config["agents_md_output"]["agents_md"]
    claude_md_path = repo_root / config["agents_md_output"]["claude_md"]
    subscribed_names = {s["name"] for s in subs}

    new_agents_md = regen_agents_md.render_agents_md(agents_md_dir, subscribed_names)

    if agents_md_path.exists():
        current = agents_md_path.read_text(encoding="utf-8")
        if current != new_agents_md:
            # Extract diff body into a candidate file.
            ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            extracted = agents_md_dir / f"extracted-{ts}.md"
            extracted.parent.mkdir(parents=True, exist_ok=True)
            extracted.write_text(_make_extracted_candidate(current, new_agents_md))
            report.agents_md_extracted_path = str(
                extracted.relative_to(repo_root)
            )

    agents_md_path.write_text(new_agents_md)
    report.agents_md_regenerated = True

    # CLAUDE.md
    new_claude_md = regen_agents_md.render_claude_md(agents_md_dir)
    if claude_md_path.exists():
        current = claude_md_path.read_text(encoding="utf-8")
        if current != new_claude_md:
            ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            extracted = agents_md_dir / f"extracted-claude-{ts}.md"
            extracted.parent.mkdir(parents=True, exist_ok=True)
            extracted.write_text(_make_extracted_candidate(current, new_claude_md))
            report.claude_md_extracted_path = str(
                extracted.relative_to(repo_root)
            )

    claude_md_path.write_text(new_claude_md)
    report.claude_md_regenerated = True


def _make_extracted_candidate(current: str, new: str) -> str:
    """Wrap whatever was in `current` but not in `new` as a candidate
    agents-md file in the strict two-section format."""
    return (
        "# agent instruction\n\n"
        "_The following text was found in the destination file at sync "
        "time but is not produced by the current agents-md sources. "
        "Review it and, if it should be a rule, edit it into the proper "
        "form (single rule, do/don't statement) and rename this file._\n\n"
        f"{current.strip()}\n\n"
        "# justification\n\n"
        "_TODO: add the persuasion text for this rule, or delete this file._\n"
    )


def run(repo_root: Path, config_path: Path,
        registry_clone: Optional[Path] = None,
        no_clone: bool = False,
        dry_run: bool = False) -> SyncReport:
    config = canonical_json.load(config_path)
    _v.validate("skill-sync-config", config)

    if registry_clone is not None:
        registry_root = registry_clone
    elif no_clone:
        raise RuntimeError("--no-clone requires --registry-clone")
    else:
        registry_root = _clone_registry(
            config["registry"]["repo"], config["registry"]["ref"]
        )

    skills_ledger    = _load_registry_ledger(registry_root, "skills")
    spec_ledger      = _load_registry_ledger(registry_root, "skill-specs")
    adrs_ledger      = _load_registry_ledger(registry_root, "adrs")
    agents_md_ledger = _load_registry_ledger(registry_root, "agents-md")

    report = SyncReport()

    if dry_run:
        # Just report what would happen.
        return report

    _sync_skills(repo_root, registry_root, config, skills_ledger, report)
    _sync_single_files(repo_root, registry_root, config, agents_md_ledger,
                       kind="agents-md", sub_key="agents_md",
                       artifact_dir_key="agents_md", type_dir="agents-md",
                       report=report)
    _sync_single_files(repo_root, registry_root, config, adrs_ledger,
                       kind="adr", sub_key="adrs",
                       artifact_dir_key="adrs", type_dir="adrs",
                       report=report)

    _regen_agents_md_files(repo_root, config, report)

    return report


def _print_report(report: SyncReport) -> None:
    print("=== skill-sync report ===")
    for label, items in [
        ("installed", report.installed),
        ("upgraded",  report.upgraded),
        ("noop",      report.noop),
        ("missing",   report.missing),
    ]:
        print(f"{label}: {len(items)}")
        for it in items:
            print(f"  {it}")
    if report.name_clashes:
        print(f"name clashes: {len(report.name_clashes)} -- requires user action")
        for nc in report.name_clashes:
            print(f"  {nc}")
    if report.deprecated_warnings:
        print("DEPRECATED items subscribed at `latest`:")
        for w in report.deprecated_warnings:
            print(f"  - {w['type']} `{w['name']}`: {w['description']}")
    if report.merged_warnings:
        print("MERGED / IMPLEMENTED items (artifact has been folded into "
              "another in the registry):")
        for w in report.merged_warnings:
            target = w.get("merged_into") or w.get("implemented_as") or "?"
            print(f"  - {w['type']} `{w['name']}` -> `{target}` (state: {w['state']})")
    if report.agents_md_regenerated:
        print("AGENTS.md regenerated.")
        if report.agents_md_extracted_path:
            print(f"  extracted prior inline edits to: {report.agents_md_extracted_path}")
    if report.claude_md_regenerated:
        print("CLAUDE.md regenerated.")
        if report.claude_md_extracted_path:
            print(f"  extracted prior inline edits to: {report.claude_md_extracted_path}")


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--no-clone", action="store_true")
    ap.add_argument("--registry-clone", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Default config path: resources/skill-sync-config.json (this skill's own).
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = _ensure_user_config(Path.cwd())

    # repo_root = git root of current dir
    repo_root = _find_repo_root(Path.cwd())

    rc = Path(args.registry_clone) if args.registry_clone else None
    report = run(repo_root, config_path,
                 registry_clone=rc,
                 no_clone=args.no_clone,
                 dry_run=args.dry_run)
    _print_report(report)


def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError(f"no git root above {start}")


if __name__ == "__main__":
    main()
