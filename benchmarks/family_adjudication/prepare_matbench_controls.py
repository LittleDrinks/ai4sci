#!/usr/bin/env python3
"""Adapt official Matbench submissions into family-adjudication controls."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CONTROLS = {
    "crabnet": ("matbench_v0.1_CrabNet", "matbench_v0.1_CrabNet_v1.2.1"),
    "modnet": ("matbench_v0.1_modnet_v0.1.12", "matbench_v0.1_modnet_v0.1.10"),
    "random_forest": ("matbench_v0.1_rf",),
    "constant_mean": ("matbench_v0.1_dummy",),
}
TASK = (
    "Predict experimental band gaps from chemical composition on the official "
    "Matbench matbench_expt_gap five-fold benchmark."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matbench-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def source_path(repo: Path, name: str) -> Path:
    return repo / "docs_src" / "Full Benchmark Data" / f"{name}.md"


def algorithm_description(text: str) -> str:
    pattern = r"### Algorithm description:\s*(.*?)\s*#### Notes:"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        raise ValueError("missing algorithm description")
    return " ".join(match.group(1).split())


def title(text: str) -> str:
    return text.splitlines()[0].removeprefix("# ").strip()


def candidate(repo: Path, name: str) -> dict:
    path = source_path(repo, name)
    text = path.read_text(encoding="utf-8")
    return {
        "candidate_id": name,
        "title": title(text),
        "mechanism": algorithm_description(text),
        "protocol": "Fit the documented algorithm on each official training fold and predict its held-out fold.",
        "code_plan": f"Run the official submission documented in {path.name} without changing its mechanism.",
        "validation": "Use the official fixed folds and Matbench recorder, validator, and regression scorer.",
        "expected_observation": "The official Matbench recorder produces five fold predictions and regression scores.",
        "falsifier": "A missing fold, invalid prediction vector, or scorer failure rejects the submitted result.",
        "dependencies": "Official Matbench submission environment and stored results.json.gz.",
        "compute_estimate": "Calibration reads stored official results and does not retrain the model.",
    }


def result_row(repo: Path, name: str) -> dict:
    fields = candidate(repo, name)
    return {
        "case_id": name,
        "policy": "official_control",
        "seed": None,
        "slot": None,
        "audit": {"status": "accepted"},
        "planner": {"candidate": fields},
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def run(repo: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    pairs = [(group, name) for group, names in CONTROLS.items() for name in names]
    write_jsonl(output / "results.jsonl", [result_row(repo, name) for _, name in pairs])
    gold = {name: group for group, name in pairs}
    (output / "gold.json").write_text(json.dumps(gold, indent=2) + "\n")
    (output / "task_info.json").write_text(json.dumps({"task": TASK}, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    run(args.matbench_repo.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
