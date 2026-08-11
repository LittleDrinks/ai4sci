#!/usr/bin/env python3
"""Exercise the official Matbench task lifecycle with a mean baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from matbench.bench import MatbenchBenchmark


TASK = "matbench_expt_gap"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def record_baseline(task) -> None:
    for fold in task.folds:
        _, train_y = task.get_train_and_val_data(fold)
        test_x = task.get_test_data(fold)
        value = float(train_y.mean())
        task.record(fold, [value] * len(test_x), params={"baseline": "train_mean"})


def report(task) -> dict:
    return {
        "task": TASK, "rows": len(task.df), "folds": len(task.folds),
        "metadata": dict(task.metadata), "scores": dict(task.scores),
        "validated": True,
    }


def run(output: Path) -> dict:
    benchmark = MatbenchBenchmark(autoload=False, subset=[TASK])
    task = benchmark.matbench_expt_gap
    task.load()
    record_baseline(task)
    task.validate()
    output.mkdir(parents=True, exist_ok=True)
    benchmark.to_file(output / "mean-baseline.json.gz")
    return report(task)


def main() -> int:
    args = parse_args()
    result = run(args.output)
    path = args.output / "report.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
