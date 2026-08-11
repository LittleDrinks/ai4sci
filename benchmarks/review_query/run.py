#!/usr/bin/env python3
"""Run ReviewScaling-v3 through Inspect AI and summarize structured logs."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path
from typing import Any

from inspect_ai import eval as inspect_eval
from inspect_ai.log import EvalLog


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scales", default="12,36")
    parser.add_argument("--model", default="openai/gpt-5.4-mini")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model-base-url")
    parser.add_argument("--debug-errors", action="store_true")
    parser.add_argument("--max-connections", type=int, default=2)
    return parser.parse_args()


def _env(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    for line in path.read_text(encoding="utf-8").splitlines() if path else []:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip("'\""))
    return values


def _set_provider(values: dict[str, str]) -> None:
    if values.get("apikey"):
        os.environ["OPENAI_API_KEY"] = values["apikey"]
    if values.get("baseurl"):
        os.environ["OPENAI_BASE_URL"] = values["baseurl"]


def _sample_row(sample: Any) -> dict[str, Any]:
    score = next(iter(sample.scores.values())) if sample.scores else None
    metadata = score.metadata if score else {}
    return {"id": sample.id, "metadata": sample.metadata, "score": score.model_dump() if score else None,
            "tool_calls": metadata.get("tool_calls", []), "usage": metadata.get("usage", {})}


def _report(log: EvalLog, args: argparse.Namespace) -> dict[str, Any]:
    rows = [_sample_row(sample) for sample in log.samples or []]
    correct = sum(row["score"]["value"] == "C" for row in rows if row["score"])
    calls = sum(len(row["tool_calls"]) for row in rows)
    usage = {key: sum(row["usage"].get(key, 0) for row in rows) for key in ("input_tokens", "output_tokens", "total_tokens")}
    return {"benchmark": "ReviewScaling-v3", "model": args.model, "scales": args.scales,
            "samples": len(rows), "accuracy": correct / len(rows) if rows else 0, "tool_calls": calls,
            "usage": usage, "log_status": log.status, "log": log.location, "samples_detail": rows}


def _configure(args: argparse.Namespace) -> None:
    values = _env(args.env_file)
    _set_provider(values)
    os.environ["REVIEW_SCALING_CODE"] = os.environ.get("REVIEW_SCALING_CODE", str(Path(__file__).parents[1] / "review_scaling"))
    os.environ["SEARCHBENCH_SOURCE_ROOT"] = str(args.source_root)
    os.environ["REVIEW_QUERY_SCALES"] = args.scales
    args.output.mkdir(parents=True, exist_ok=True)


def _evaluate(args: argparse.Namespace) -> list[EvalLog]:
    return inspect_eval(
        "task.py@review_query", model=args.model, model_base_url=args.model_base_url,
        task_args={"source_root": str(args.source_root), "scales": args.scales},
        log_dir=str(args.output), display="none", log_format="eval", continue_on_fail=True,
        score_on_error=True, fail_on_error=False, debug_errors=args.debug_errors,
        max_connections=args.max_connections,
    )


def _write_error(args: argparse.Namespace, exc: BaseException) -> None:
    error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    (args.output / "run_error.json").write_text(json.dumps(error, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"error_type": type(exc).__name__, "error": str(exc)[:500]}, ensure_ascii=False))


def _write_report(args: argparse.Namespace, log: EvalLog) -> None:
    report = _report(log, args)
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("benchmark", "samples", "accuracy", "tool_calls", "usage", "log_status")}, ensure_ascii=False))


def main() -> int:
    args = _args()
    _configure(args)
    try:
        logs = _evaluate(args)
    except BaseException as exc:
        _write_error(args, exc)
        return 1
    _write_report(args, logs[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
