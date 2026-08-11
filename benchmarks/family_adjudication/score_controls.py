#!/usr/bin/env python3
"""Score hidden Matbench family controls after pairwise adjudication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def expected(record: dict, gold: dict[str, str]) -> str:
    left = gold[record["candidate_a_source_id"]]
    right = gold[record["candidate_b_source_id"]]
    return "same" if left == right else "different"


def reviewer_accuracy(rows: list[dict], gold: dict, reviewer: str) -> float:
    correct = 0
    for row in rows:
        review = next(item for item in row["reviews"] if item["reviewer"] == reviewer)
        correct += review["judgment"] == expected(row, gold)
    return correct / len(rows)


def confusion(rows: list[dict], gold: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = f'{expected(row, gold)}->{row["provisional_judgment"]}'
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def score(rows: list[dict], gold: dict[str, str]) -> dict:
    correct = sum(row["provisional_judgment"] == expected(row, gold) for row in rows)
    return {
        "pairs": len(rows),
        "provisional_accuracy": correct / len(rows),
        "reviewer_a_accuracy": reviewer_accuracy(rows, gold, "A"),
        "reviewer_b_accuracy": reviewer_accuracy(rows, gold, "B"),
        "confusion": confusion(rows, gold),
    }


def main() -> int:
    args = parse_args()
    rows = read_jsonl(args.judgments)
    gold = json.loads(args.gold.read_text())
    report = score(rows, gold)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
