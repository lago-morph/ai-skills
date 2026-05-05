#!/usr/bin/env python3
"""Run an offline trigger evaluation for a Codex skill description.

This script does not invoke a model. It provides a deterministic approximation
that is useful for finding obvious description gaps before doing human review
or environment-specific trigger testing.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from scripts.utils import parse_skill_md


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for",
    "from", "has", "have", "in", "into", "is", "it", "of", "on", "or",
    "should", "that", "the", "this", "to", "use", "user", "when", "with",
    "wants", "want", "needs", "need", "skill", "codex",
}


def find_project_root() -> Path:
    """Return the current working directory.

    Kept for compatibility with run_loop.py, which passes a project root into
    run_eval. Offline evaluation does not need project discovery.
    """
    return Path.cwd()


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower())
        if token not in STOPWORDS
    ]


def extract_keywords(skill_name: str, description: str, max_terms: int = 60) -> set[str]:
    text = f"{skill_name.replace('-', ' ')} {description}"
    counts = Counter(tokenize(text))
    return {term for term, _ in counts.most_common(max_terms)}


def query_matches(query: str, keywords: set[str]) -> bool:
    query_terms = set(tokenize(query))
    if not query_terms or not keywords:
        return False

    overlap = query_terms & keywords
    if len(overlap) >= 2:
        return True

    if len(overlap) == 1:
        term = next(iter(overlap))
        return len(term) >= 6

    return False


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Return whether the offline matcher predicts the skill should trigger."""
    del timeout, project_root, model
    return query_matches(query, extract_keywords(skill_name, skill_description))


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return deterministic offline results."""
    del num_workers, timeout, project_root, runs_per_query, trigger_threshold, model
    keywords = extract_keywords(skill_name, description)
    results = []

    for item in eval_set:
        query = item["query"]
        should_trigger = bool(item["should_trigger"])
        triggered = query_matches(query, keywords)
        did_pass = triggered == should_trigger
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": 1.0 if triggered else 0.0,
            "triggers": 1 if triggered else 0,
            "runs": 1,
            "pass": did_pass,
            "matched_terms": sorted(set(tokenize(query)) & keywords),
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "matcher": "offline-keyword-overlap",
        "keywords": sorted(keywords),
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run offline trigger evaluation for a Codex skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=1, help="Accepted for compatibility; ignored")
    parser.add_argument("--timeout", type=int, default=30, help="Accepted for compatibility; ignored")
    parser.add_argument("--runs-per-query", type=int, default=1, help="Accepted for compatibility; ignored")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Accepted for compatibility; ignored")
    parser.add_argument("--model", default=None, help="Accepted for compatibility; ignored")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, _ = parse_skill_md(skill_path)
    description = args.description or original_description
    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=find_project_root(),
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for result in output["results"]:
            status = "PASS" if result["pass"] else "FAIL"
            print(
                f"  [{status}] expected={result['should_trigger']} "
                f"matched={','.join(result['matched_terms']) or '-'}: {result['query'][:70]}",
                file=sys.stderr,
            )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
