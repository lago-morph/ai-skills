#!/usr/bin/env python3
"""Interactive walkthrough of `/incoming/` reports.

See resources/skill-management-v1.md §7.1.1 — `process-incoming` mode.

This is the only script in the registry that needs human-in-the-loop
interaction AND that performs ledger / artifact writes. It is invoked
by the agent under direct user supervision: the agent reads each
report, may augment its "AI analysis" + "Disposition recommendation"
sections, then asks the user for a final disposition.

Because v1 is run by a single user driving the agent, the interactive
flow is implemented as helper functions that the agent calls — not as
a standalone `input()` loop. The agent uses AskUserQuestion at the
right moments and then calls the apply function with the chosen
disposition.

Public entry points (called from the agent during process-incoming mode):

    list_pending(repo_root) -> list[PendingItem]
    apply_disposition(repo_root, item, disposition, *, new_name=None,
                      new_version=None, description=None,
                      merge_result_path=None) -> dict

A `PendingItem` is a namedtuple-ish dict:
    {
      "artifact_type": "skills" | "skill-specs" | "adrs" | "agents-md",
      "name": "<kebab>",                  # name AFTER UID strip
      "source": "<org>/<repo>",
      "incoming_path": Path,              # file OR dir
      "report_path": Path,                # the *-semantic-diff.md report
      "registry_path": Path | None,       # existing registry artifact, if any
    }

Disposition values:
    "discard"      -> add incoming hash to discarded_hashes
    "replace"      -> overwrite registry artifact with incoming
    "merge"        -> replace with `merge_result_path` content
    "add-as-new"   -> add brand-new artifact (may include a name change
                      to resolve a kebab-name clash; record name_clash
                      on the EXISTING entry, one-way)

All disposition functions:
  - Update the ledger (validate before save).
  - Write a canonical-JSON ledger.
  - Remove the incoming artifact and its semantic-diff report.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_json
import hash_single_file
import hash_skill
import validate as _v


SINGLE_FILE_TYPES = ("skill-specs", "adrs", "agents-md")
ORIGIN = "github.com/lago-morph/ai-skills"

_PRE_INGESTION_RE = re.compile(
    r"^(?:SKILL-SPEC|ADR|AGENTS-MD)-[0-9a-f]{10}-(?P<n>[a-z0-9][a-z0-9-]*[a-z0-9])\.md$"
)


@dataclass
class PendingItem:
    artifact_type: str
    name: str
    source: str
    incoming_path: Path
    report_path: Path
    registry_path: Optional[Path]


# ---------- discovery ----------

def _strip_pre_ingestion(filename: str) -> str:
    m = _PRE_INGESTION_RE.match(filename)
    return m.group("n") if m else filename.rsplit(".md", 1)[0]


def _registry_artifact(repo_root: Path, artifact_type: str, name: str) -> Optional[Path]:
    if artifact_type == "skills":
        p = repo_root / "skills" / name
        return p if p.is_dir() else None
    p = repo_root / artifact_type / f"{name}.md"
    return p if p.is_file() else None


def list_pending(repo_root: Path) -> list[PendingItem]:
    out: list[PendingItem] = []
    inc = repo_root / "incoming"
    if not inc.exists():
        return out
    for org_dir in sorted(p for p in inc.iterdir() if p.is_dir()):
        for repo_dir in sorted(p for p in org_dir.iterdir() if p.is_dir()):
            src = f"{org_dir.name}/{repo_dir.name}"

            # Skills
            sdir = repo_dir / "skills"
            if sdir.exists():
                for skill in sorted(p for p in sdir.iterdir() if p.is_dir()):
                    report = skill.with_name(skill.name + "-semantic-diff.md")
                    out.append(PendingItem(
                        artifact_type="skills",
                        name=skill.name,
                        source=src,
                        incoming_path=skill,
                        report_path=report,
                        registry_path=_registry_artifact(repo_root, "skills", skill.name),
                    ))

            # Single-file types
            for at in SINGLE_FILE_TYPES:
                tdir = repo_dir / at
                if not tdir.exists():
                    continue
                for f in sorted(p for p in tdir.iterdir() if p.is_file()):
                    if f.name.endswith("-semantic-diff.md"):
                        continue
                    name = _strip_pre_ingestion(f.name)
                    report = f.with_name(f"{f.stem}-semantic-diff.md")
                    out.append(PendingItem(
                        artifact_type=at,
                        name=name,
                        source=src,
                        incoming_path=f,
                        report_path=report,
                        registry_path=_registry_artifact(repo_root, at, name),
                    ))
    return out


# ---------- helpers ----------

def _load_ledger(repo_root: Path, artifact_type: str) -> dict:
    p = repo_root / artifact_type / "000-ledger.json"
    if p.exists():
        data = canonical_json.load(p)
    else:
        data = {"artifact_type": artifact_type, "items": {}}
    _v.validate("ledger", data)
    return data


def _save_ledger(repo_root: Path, artifact_type: str, data: dict) -> None:
    _v.validate("ledger", data)
    p = repo_root / artifact_type / "000-ledger.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    canonical_json.write(p, data)


def _compute_incoming_hash(item: PendingItem) -> str:
    if item.artifact_type == "skills":
        # Strip the metadata file from the hash (consistent with §3.1).
        return hash_skill.hash_skill(item.incoming_path)
    raw = item.incoming_path.read_bytes()
    # Retrospective form has no metadata line; hash the raw bytes.
    first_nl = raw.find(b"\n")
    if first_nl != -1:
        try:
            json.loads(raw[:first_nl].decode("utf-8"))
            return hash_single_file.hash_single_file(item.incoming_path)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            pass
    return hash_single_file.hash_bytes_no_metadata(raw)


def _cleanup(item: PendingItem) -> None:
    if item.incoming_path.is_dir():
        shutil.rmtree(item.incoming_path)
    elif item.incoming_path.exists():
        item.incoming_path.unlink()
    if item.report_path.exists():
        item.report_path.unlink()


def _metadata_first_line(meta: dict) -> str:
    ordered = {}
    for k in ["name", "origin", "content_hash", "version", "state",
              "implemented_as", "merged_into"]:
        if k in meta:
            ordered[k] = meta[k]
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False)


# ---------- dispositions ----------

def disposition_discard(repo_root: Path, item: PendingItem) -> dict:
    h = _compute_incoming_hash(item)
    ledger = _load_ledger(repo_root, item.artifact_type)
    items = ledger["items"]
    entry = items.get(item.name)
    if entry is None:
        # No existing entry: create a "skeletal" discard marker so future
        # sweeps dedup. We need to satisfy the schema, which requires
        # current_version + current_hash + versions[]. We treat this as
        # version 0.0.0 + state="live" with an empty description placeholder
        # — but actually, the cleanest representation of "we never accepted
        # this artifact at all" is to refuse the discard with no anchor.
        raise ValueError(
            f"cannot discard `{item.name}`: no existing ledger entry. "
            "Pick `add-as-new` instead, or rename the incoming item if it "
            "is a kebab-name clash with a different artifact."
        )
    if h not in entry["discarded_hashes"]:
        entry["discarded_hashes"].append(h)
    _save_ledger(repo_root, item.artifact_type, ledger)
    _cleanup(item)
    return {"action": "discard", "hash": h}


def _bump_or_validate_version(current: str, requested: str) -> str:
    """Ensure `requested` is strictly greater than `current` (semver).
    Normalize `1` -> `1.0.0`, `1.2` -> `1.2.0`."""
    parts = requested.split("-", 1)
    base = parts[0].split(".")
    while len(base) < 3:
        base.append("0")
    normalized = ".".join(base) + (f"-{parts[1]}" if len(parts) == 2 else "")
    # Re-use canonical_json's semver key for comparison.
    import canonical_json as _cj
    if _cj._semver_key(normalized) <= _cj._semver_key(current):
        raise ValueError(
            f"requested version {normalized} must be strictly greater than current {current}"
        )
    return normalized


def _install_to_registry(repo_root: Path, item: PendingItem,
                         meta_for_single_file: dict | None = None) -> None:
    """Copy incoming artifact into the registry, stripping pre-ingestion
    name prefix for single-file types. For skills, write
    resources/000-metadata.json with the registry metadata."""
    if item.artifact_type == "skills":
        dst = repo_root / "skills" / item.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(item.incoming_path, dst)
        # Hash AFTER install (metadata is created in caller; here we just
        # ensure resources/ exists for the caller).
        (dst / "resources").mkdir(exist_ok=True)
    else:
        dst = repo_root / item.artifact_type / f"{item.name}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        # If meta_for_single_file given, prepend it; otherwise copy as-is.
        body = item.incoming_path.read_bytes()
        # Strip existing first-line metadata, if any.
        first_nl = body.find(b"\n")
        if first_nl != -1:
            try:
                json.loads(body[:first_nl].decode("utf-8"))
                body = body[first_nl + 1:]
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                pass
        if meta_for_single_file is not None:
            line = _metadata_first_line(meta_for_single_file).encode("utf-8")
            dst.write_bytes(line + b"\n" + body)
        else:
            dst.write_bytes(body)


def _write_skill_metadata(skill_dir: Path, name: str, content_hash: str) -> None:
    meta = {
        "name": name,
        "origin": ORIGIN,
        "content_hash": content_hash,
        "version": "0.1.0",  # caller overwrites after computing
        "state": "live",
        "implemented_as": None,
        "merged_into": None,
        "hash_exclude": ["resources/000-metadata.json"],
    }
    (skill_dir / "resources").mkdir(exist_ok=True)
    canonical_json.write(skill_dir / "resources" / "000-metadata.json", meta)


def _add_or_update_version(entry: dict, version: str, h: str, commit: str) -> None:
    entry["versions"].append({"version": version, "hash": h, "commit": commit})
    entry["current_version"] = version
    entry["current_hash"] = h


def disposition_replace(repo_root: Path, item: PendingItem, *,
                        new_version: str,
                        description: str | None = None,
                        commit: str = "pending") -> dict:
    """Overwrite existing artifact with incoming."""
    ledger = _load_ledger(repo_root, item.artifact_type)
    items = ledger["items"]
    if item.name not in items:
        raise ValueError(f"`replace` requires an existing entry for `{item.name}`")
    entry = items[item.name]
    normalized = _bump_or_validate_version(entry["current_version"], new_version)

    if item.artifact_type == "skills":
        # Install -> compute hash WITH metadata excluded.
        dst = repo_root / "skills" / item.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(item.incoming_path, dst)
        # Strip any pre-existing metadata; we'll regenerate.
        meta_file = dst / "resources" / "000-metadata.json"
        if meta_file.exists():
            meta_file.unlink()
        # Compute Option A hash.
        h = hash_skill.hash_skill(dst, ["resources/000-metadata.json"])
        meta = {
            "name": item.name,
            "origin": ORIGIN,
            "content_hash": h,
            "version": normalized,
            "state": entry["state"],
            "implemented_as": entry.get("implemented_as"),
            "merged_into": entry.get("merged_into"),
            "hash_exclude": ["resources/000-metadata.json"],
        }
        (dst / "resources").mkdir(exist_ok=True)
        canonical_json.write(dst / "resources" / "000-metadata.json", meta)
    else:
        # Compute hash on the raw (no metadata) bytes
        body = item.incoming_path.read_bytes()
        first_nl = body.find(b"\n")
        if first_nl != -1:
            try:
                json.loads(body[:first_nl].decode("utf-8"))
                body = body[first_nl + 1:]
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                pass
        h = hash_single_file.hash_bytes_no_metadata(body)
        meta = {
            "name": item.name,
            "origin": ORIGIN,
            "content_hash": h,
            "version": normalized,
            "state": entry["state"],
            "implemented_as": entry.get("implemented_as"),
            "merged_into": entry.get("merged_into"),
        }
        dst = repo_root / item.artifact_type / f"{item.name}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        line = _metadata_first_line(meta).encode("utf-8")
        dst.write_bytes(line + b"\n" + body)

    _add_or_update_version(entry, normalized, h, commit)
    if description is not None:
        entry["description"] = description
    _save_ledger(repo_root, item.artifact_type, ledger)
    _cleanup(item)
    return {"action": "replace", "version": normalized, "hash": h}


def disposition_merge(repo_root: Path, item: PendingItem, *,
                      merge_result_path: Path, new_version: str,
                      description: str | None = None,
                      commit: str = "pending") -> dict:
    """Replace registry artifact with the AI-merged result.

    `merge_result_path` is a tmp-dir copy that the agent wrote after the
    user accepted/rejected each proposed delta. Behaves exactly like
    `replace` once the merged artifact has been chosen.
    """
    # Repoint incoming_path to the merged result for the install step.
    proxy = PendingItem(
        artifact_type=item.artifact_type,
        name=item.name,
        source=item.source,
        incoming_path=merge_result_path,
        report_path=item.report_path,
        registry_path=item.registry_path,
    )
    res = disposition_replace(repo_root, proxy, new_version=new_version,
                              description=description, commit=commit)
    _cleanup(item)  # also remove the original incoming + report
    res["action"] = "merge"
    return res


def disposition_add_as_new(repo_root: Path, item: PendingItem, *,
                           new_version: str,
                           description: str,
                           new_name: str | None = None,
                           commit: str = "pending") -> dict:
    """Add a never-before-seen artifact. If `new_name` is given, it
    represents resolution of a kebab-name clash; record name_clash on the
    EXISTING (clashing) entry."""
    ledger = _load_ledger(repo_root, item.artifact_type)
    items = ledger["items"]

    target_name = new_name if new_name else item.name
    if target_name in items:
        raise ValueError(
            f"`add-as-new` cannot create `{target_name}`: name already exists. "
            "Pass a different `new_name`."
        )

    # Normalize version, no lower-bound check (no prior version).
    parts = new_version.split("-", 1)
    base = parts[0].split(".")
    while len(base) < 3:
        base.append("0")
    normalized = ".".join(base) + (f"-{parts[1]}" if len(parts) == 2 else "")

    # Install (overwrite proxy name)
    proxy = PendingItem(
        artifact_type=item.artifact_type,
        name=target_name,
        source=item.source,
        incoming_path=item.incoming_path,
        report_path=item.report_path,
        registry_path=None,
    )
    if proxy.artifact_type == "skills":
        dst = repo_root / "skills" / target_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(proxy.incoming_path, dst)
        meta_file = dst / "resources" / "000-metadata.json"
        if meta_file.exists():
            meta_file.unlink()
        h = hash_skill.hash_skill(dst, ["resources/000-metadata.json"])
        meta = {
            "name": target_name,
            "origin": ORIGIN,
            "content_hash": h,
            "version": normalized,
            "state": "live",
            "implemented_as": None,
            "merged_into": None,
            "hash_exclude": ["resources/000-metadata.json"],
        }
        (dst / "resources").mkdir(exist_ok=True)
        canonical_json.write(dst / "resources" / "000-metadata.json", meta)
    else:
        body = proxy.incoming_path.read_bytes()
        first_nl = body.find(b"\n")
        if first_nl != -1:
            try:
                json.loads(body[:first_nl].decode("utf-8"))
                body = body[first_nl + 1:]
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                pass
        h = hash_single_file.hash_bytes_no_metadata(body)
        meta = {
            "name": target_name,
            "origin": ORIGIN,
            "content_hash": h,
            "version": normalized,
            "state": "live",
            "implemented_as": None,
            "merged_into": None,
        }
        dst = repo_root / proxy.artifact_type / f"{target_name}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        line = _metadata_first_line(meta).encode("utf-8")
        dst.write_bytes(line + b"\n" + body)

    new_entry = {
        "current_version": normalized,
        "current_hash": h,
        "state": "live",
        "description": description,
        "implemented_as": None,
        "merged_into": None,
        "name_clash": [],
        "versions": [{"version": normalized, "hash": h, "commit": commit}],
        "discarded_hashes": [],
    }
    items[target_name] = new_entry

    # If this was a clash resolution, record the one-way pointer on the
    # ORIGINAL clashing entry.
    if new_name and item.name in items and target_name != item.name:
        original = items[item.name]
        if target_name not in original["name_clash"]:
            original["name_clash"].append(target_name)

    _save_ledger(repo_root, item.artifact_type, ledger)
    _cleanup(item)
    return {"action": "add-as-new", "name": target_name,
            "version": normalized, "hash": h}


def apply_disposition(repo_root: Path, item: PendingItem,
                      disposition: str, **kwargs) -> dict:
    if disposition == "discard":
        return disposition_discard(repo_root, item)
    if disposition == "replace":
        return disposition_replace(repo_root, item, **kwargs)
    if disposition == "merge":
        return disposition_merge(repo_root, item, **kwargs)
    if disposition == "add-as-new":
        return disposition_add_as_new(repo_root, item, **kwargs)
    raise ValueError(f"unknown disposition: {disposition}")


def main() -> None:
    """Print the pending list so the agent can drive the conversation."""
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent.parent.parent
    pending = list_pending(repo_root)
    if not pending:
        print("(no pending incoming items)")
        return
    for i, item in enumerate(pending, 1):
        registry = "<new>" if item.registry_path is None else str(
            item.registry_path.relative_to(repo_root)
        )
        print(f"[{i}] {item.artifact_type}: {item.name}")
        print(f"    source:   {item.source}")
        print(f"    incoming: {item.incoming_path.relative_to(repo_root)}")
        print(f"    report:   {item.report_path.relative_to(repo_root)}")
        print(f"    registry: {registry}")


if __name__ == "__main__":
    main()
