"""Build ReviewEval representations and run non-human preflight checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from dataset import DEFAULT_SOURCE, load_dataset
from eval import QUESTIONS, evaluate_representation, representations
from proxy import run_proxy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=Path("revieweval-report.json"))
    parser.add_argument("--proxy", choices=("auto", "api", "heuristic"), default="auto")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    return parser.parse_args()


def build_report(args, dataset, reps, checks, proxy):
    return {
        "benchmark": "ReviewEval-preflight", "version": "2026-08-09",
        "source_asset": str(args.source), "source_asset_status": "reused_prototype_ui_fixture",
        "fixture_status": "synthetic_fixed_questions_and_answers",
        "evaluation_scope": "representation_completeness_preflight_only",
        "real_searchbench_events": False, "human_readability_validated": False,
        "human_participants": 0, "human_evaluation": "not_run", "model_requested": args.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_counts": {"artifacts": len(dataset["artifacts"]), "events": len(dataset["events"])},
        "questions": QUESTIONS,
        "representations": [{key: value for key, value in rep.items() if key != "text"} for rep in reps],
        "completeness": checks,
        "proxy_preflight": [{"representation": rep["id"], **result} for rep, result in zip(reps, proxy)],
        "passed": all(item["passed"] for item in checks),
    }


def write_reports(output, report, reps):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path = output.with_name("representations.json")
    path.write_text(json.dumps(reps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    dataset = load_dataset(args.source)
    reps = representations(dataset)
    checks = [evaluate_representation(rep, dataset) for rep in reps]
    proxy = [run_proxy(rep, args.model, args.env_file, args.proxy) for rep in reps]
    report = build_report(args, dataset, reps, checks, proxy)
    write_reports(args.output, report, reps)
    print(json.dumps({"output": str(args.output), "representations": len(reps), "passed": report["passed"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
