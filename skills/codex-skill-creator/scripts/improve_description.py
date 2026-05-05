#!/usr/bin/env python3
"""Suggest a Codex skill description based on offline eval results.

This helper is intentionally deterministic. It does not call a model; it
surfaces missed trigger vocabulary and near-miss negatives so the user or
agent can make a focused edit.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from scripts.run_eval import STOPWORDS, tokenize
from scripts.utils import parse_skill_md


def _top_terms(queries: list[str], limit: int = 12) -> list[str]:
    counts: Counter[str] = Counter()
    for query in queries:
        counts.update(tokenize(query))
    return [term for term, _ in counts.most_common(limit)]


def _clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:] if text else text


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str | None = None,
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Return a conservative improved description.

    The result is a draft, not a guaranteed optimal trigger description. Use it
    as a starting point and review it for false positives before applying.
    """
    del skill_content, history, model, test_results

    missed = [
        r["query"] for r in eval_results["results"]
        if r["should_trigger"] and not r["pass"]
    ]
    false_positive = [
        r["query"] for r in eval_results["results"]
        if not r["should_trigger"] and not r["pass"]
    ]

    missed_terms = [t for t in _top_terms(missed) if t not in STOPWORDS]
    false_terms = [t for t in _top_terms(false_positive, limit=8) if t not in STOPWORDS]

    base = current_description.rstrip(". ")
    additions: list[str] = []

    if missed_terms:
        additions.append(
            "Use when requests involve "
            + ", ".join(missed_terms[:8])
            + "."
        )

    if false_terms:
        additions.append(
            "Avoid using for adjacent requests centered on "
            + ", ".join(false_terms[:6])
            + " unless they also require this skill's workflow."
        )

    if not additions:
        additions.append("Use for concrete requests that need this specialized workflow, references, scripts, or packaged skill assets.")

    candidate = _clean_sentence(base + ". " + " ".join(additions))

    if len(candidate) > 1024:
        candidate = candidate[:1021].rstrip(" ,.;") + "..."

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(json.dumps({
            "iteration": iteration,
            "current_description": current_description,
            "missed_terms": missed_terms,
            "false_positive_terms": false_terms,
            "suggested_description": candidate,
        }, indent=2))

    return candidate


def main():
    parser = argparse.ArgumentParser(description="Suggest a Codex skill description from offline eval results")
    parser.add_argument("--eval-results", required=True, help="Path to eval results JSON from run_eval.py")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--history", default=None, help="Path to history JSON; accepted for compatibility")
    parser.add_argument("--model", default=None, help="Accepted for compatibility; ignored")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_results = json.loads(Path(args.eval_results).read_text())
    history = json.loads(Path(args.history).read_text()) if args.history else []
    name, _, content = parse_skill_md(skill_path)
    current_description = eval_results["description"]

    new_description = improve_description(
        skill_name=name,
        skill_content=content,
        current_description=current_description,
        eval_results=eval_results,
        history=history,
        model=args.model,
    )

    if args.verbose:
        print(f"Suggested: {new_description}", file=sys.stderr)

    output = {
        "description": new_description,
        "history": history + [{
            "description": current_description,
            "passed": eval_results["summary"]["passed"],
            "failed": eval_results["summary"]["failed"],
            "total": eval_results["summary"]["total"],
            "results": eval_results["results"],
        }],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
