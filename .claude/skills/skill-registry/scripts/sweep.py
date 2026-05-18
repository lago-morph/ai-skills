#!/usr/bin/env python3
"""Sweep tracked repos for new artifact candidates.

See ai/skill-management-v1.md §7.1.1 — `sweep` mode.

For each repo in `registry-config.json`:
  1. git clone --depth 1 into /tmp/skill-sweep-<run-id>/<org>/<repo>
  2. For each artifact-type and each configured glob in that repo:
     - Locate candidate files / directories.
     - Compute their hash.
     - Look up name + hash in the registry ledger.
       * known live/deprecated -> skip silently
       * known merged/implemented -> skip silently (artifact retired)
       * known via discarded_hashes -> skip silently
       * known via name_clash transitive lookup -> skip silently
       * unknown -> copy into /incoming/<org>/<repo>/<type>/<name>/...
  3. After all repos processed, auto-invoke `reconcile.py` to produce
     semantic-diff reports next to each incoming item.

This script does NOT modify the registry's ledgers. It only writes into
`/incoming/`. The actual ledger updates happen later in `process_incoming`.

CLI:
    sweep.py [--config PATH] [--no-reconcile] [--repo OWNER/NAME]

Filename-pattern recognition (v1):
    Pre-ingestion form: TYPE-<10hex>-<kebab>.md  (UID kept immutable)
    Registry    form:               <kebab>.md
Both are accepted from any configured source path. The 10-hex UID prefix
is stripped at promotion time (during process_incoming), NEVER here.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_json
import validate as _v
import hash_skill
import hash_single_file


PRE_INGESTION_RE = re.compile(
    r"^(?P<type>SKILL-SPEC|ADR|AGENTS-MD)-[0-9a-f]{10}-(?P<name>[a-z0-9][a-z0-9-]*[a-z0-9])\.md$"
)


def _kebab_from_filename(filename: str) -> str:
    """Strip the pre-ingestion UID prefix if present; otherwise return
    the basename without .md extension."""
    m = PRE_INGESTION_RE.match(filename)
    if m:
        return m.group("name")
    return filename.rsplit(".md", 1)[0]


def _kebab_from_dirname(dirname: str) -> str:
    return dirname


def _ledger_for(repo_root: Path, artifact_type: str) -> dict:
    ledger_path = repo_root / artifact_type / "000-ledger.json"
    if not ledger_path.exists():
        return {"artifact_type": artifact_type, "items": {}}
    data = canonical_json.load(ledger_path)
    _v.validate("ledger", data)
    return data


def _all_known_hashes(ledger: dict, name: str) -> set[str]:
    """Return the union of (versions[*].hash, current_hash, discarded_hashes)
    for the given name."""
    items = ledger.get("items", {})
    item = items.get(name)
    if not item:
        return set()
    hashes = {item["current_hash"]}
    for v in item.get("versions", []):
        hashes.add(v["hash"])
    for h in item.get("discarded_hashes", []):
        hashes.add(h)
    return hashes


def _is_known(ledger: dict, name: str, content_hash: str) -> bool:
    """Lookup with name-clash transitive resolution (one-way pointers)."""
    if content_hash in _all_known_hashes(ledger, name):
        return True
    item = ledger.get("items", {}).get(name)
    if not item:
        return False
    # State 'merged' / 'implemented' also means "stop bothering me about this".
    if item.get("state") in ("merged", "implemented"):
        # Even if hash is unknown, we never re-ingest. The artifact retired.
        return True
    # Transitive name-clash lookup.
    for renamed in item.get("name_clash", []):
        if content_hash in _all_known_hashes(ledger, renamed):
            return True
    return False


def _git_clone(repo: str, dest: Path) -> None:
    url = f"https://github.com/{repo}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        capture_output=True,
    )


def _resolve_paths_for_repo(config: dict, repo: str) -> dict[str, list[str]]:
    defaults = config["defaults"]
    for r in config["repos"]:
        if r["repo"] == repo:
            overrides = r.get("paths", {})
            return {k: overrides.get(k, defaults[k]) for k in defaults}
    return dict(defaults)


def _glob_under(root: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        for match in glob.glob(str(root / pat), recursive=True):
            p = Path(match)
            out.append(p)
    return out


def _copy_skill(src_skill: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src_skill.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src_skill, target)


def _copy_file_strip_filename_uid(src: Path, dst_dir: Path) -> Path:
    """Copy a single-file artifact into `dst_dir`. Filename keeps its
    pre-ingestion UID prefix (we do NOT strip until ingestion)."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst


def sweep(repo_root: Path, config: dict, only_repo: str | None = None) -> dict:
    """Returns a summary dict of what was found vs copied."""
    summary: dict = {"repos": {}}
    incoming_root = repo_root / "incoming"
    incoming_root.mkdir(exist_ok=True)

    # Pre-load registry ledgers (one per artifact type).
    ledgers = {t: _ledger_for(repo_root, t)
               for t in ("skills", "skill-specs", "adrs", "agents-md")}

    run_id = uuid.uuid4().hex[:8]
    tmp_root = Path("/tmp") / f"skill-sweep-{run_id}"
    tmp_root.mkdir(parents=True, exist_ok=True)

    for repo_cfg in config["repos"]:
        repo = repo_cfg["repo"]
        if only_repo and repo != only_repo:
            continue
        org, name = repo.split("/", 1)
        clone_dst = tmp_root / org / name
        clone_dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            _git_clone(repo, clone_dst)
        except subprocess.CalledProcessError as e:
            summary["repos"][repo] = {"error": e.stderr.decode("utf-8", errors="replace")}
            continue

        paths = _resolve_paths_for_repo(config, repo)
        per_repo_inc = incoming_root / org / name

        repo_summary = {"skills": {"found": 0, "copied": 0},
                        "skill_specs": {"found": 0, "copied": 0},
                        "adrs": {"found": 0, "copied": 0},
                        "agents_md": {"found": 0, "copied": 0}}

        # --- skills (directories) ---
        for cand in _glob_under(clone_dst, paths["skills"]):
            if not cand.is_dir():
                continue
            repo_summary["skills"]["found"] += 1
            kebab = _kebab_from_dirname(cand.name)
            try:
                h = hash_skill.hash_skill(cand)
            except (OSError, NotADirectoryError):
                continue
            if _is_known(ledgers["skills"], kebab, h):
                continue
            _copy_skill(cand, per_repo_inc / "skills")
            repo_summary["skills"]["copied"] += 1

        # --- single-file types ---
        for art_key, type_dir, ledger_key in [
            ("skill_specs", "skill-specs", "skill-specs"),
            ("adrs", "adrs", "adrs"),
            ("agents_md", "agents-md", "agents-md"),
        ]:
            for cand in _glob_under(clone_dst, paths[art_key]):
                if not cand.is_file():
                    continue
                repo_summary[art_key]["found"] += 1
                kebab = _kebab_from_filename(cand.name)
                # Hash: if the file already has metadata-line format,
                # use hash_single_file (strip line 1); otherwise hash the
                # entire raw content. Heuristic: try strip-first-line
                # parse; if first line is JSON metadata, use that.
                # Simpler: just use the raw-no-metadata variant for
                # retrospective-format files (they have no metadata line).
                try:
                    h = hash_single_file.hash_bytes_no_metadata(cand.read_bytes())
                except OSError:
                    continue
                if _is_known(ledgers[ledger_key], kebab, h):
                    continue
                _copy_file_strip_filename_uid(cand, per_repo_inc / type_dir)
                repo_summary[art_key]["copied"] += 1

        summary["repos"][repo] = repo_summary

    return summary


def main() -> None:
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent.parent.parent  # scripts/ -> skill-registry/ -> skills/ -> .claude/ -> repo
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",
                    default=str(here.parent / "resources" / "registry-config.json"))
    ap.add_argument("--no-reconcile", action="store_true")
    ap.add_argument("--repo", default=None,
                    help="Only sweep this single repo (owner/name).")
    args = ap.parse_args()

    config = canonical_json.load(Path(args.config))
    _v.validate("registry-config", config)

    summary = sweep(repo_root, config, only_repo=args.repo)

    print("Sweep summary:")
    for repo, info in summary["repos"].items():
        print(f"  {repo}:")
        if "error" in info:
            print(f"    ERROR: {info['error'].splitlines()[0]}")
            continue
        for k, v in info.items():
            print(f"    {k}: found={v['found']} copied={v['copied']}")

    if not args.no_reconcile:
        import reconcile  # noqa: WPS433
        reconcile.reconcile(repo_root)


if __name__ == "__main__":
    main()
