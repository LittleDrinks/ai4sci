#!/usr/bin/env python3
"""Summarize reusable positive and negative labels in public trajectory data."""

import argparse
import collections
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telbench", type=Path, required=True)
    parser.add_argument("--tau-full", type=Path, required=True)
    parser.add_argument("--tau-failed", type=Path, required=True)
    return parser.parse_args()


def telbench_stats(path: Path) -> dict[str, object]:
    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    counts = collections.Counter(len(row["gold"]["error_span_ids"]) for row in rows)
    correct = sum(row["meta"]["answer_status"] == "correct" for row in rows)
    return {"rows": len(rows), "clean_gold": counts[0], "correct_with_errors": correct,
            "error_count_distribution": dict(sorted(counts.items()))}


def tau_stats(full_path: Path, failed_path: Path) -> dict[str, object]:
    full = json.loads(full_path.read_text(encoding="utf-8"))
    failed = json.loads(failed_path.read_text(encoding="utf-8"))
    rewards = collections.Counter(str(row["reward"]) for row in full)
    return {"full_rows": len(full), "failed_rows": len(failed),
            "reward_distribution": dict(sorted(rewards.items()))}


def main() -> None:
    args = parse_args()
    result = {"telbench": telbench_stats(args.telbench),
              "agentrx_tau": tau_stats(args.tau_full, args.tau_failed)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
