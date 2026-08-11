#!/usr/bin/env python3
"""Run the fixed-budget SearchBench review-scaling preflight."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from model import call_model
from questions import QUESTIONS, gold_answers, prompt_questions, score_response
from representations import build_representations
from source import load_source, select_window


MODEL = "gpt-5.4-mini"
DEFAULT_BUDGET_CHARS = 24_000
DEFAULT_OUTPUT_TOKENS = 700


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scales", default="12,36")
    parser.add_argument("--input-budget-chars", type=int, default=DEFAULT_BUDGET_CHARS)
    parser.add_argument("--output-budget-tokens", type=int, default=DEFAULT_OUTPUT_TOKENS)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--env-file", type=Path)
    return parser.parse_args()


def _scales(value: str) -> list[int]:
    values = sorted({int(item) for item in value.split(",") if item.strip()})
    if len(values) < 2 or any(value <= 0 for value in values):
        raise ValueError("--scales needs at least two positive run counts")
    return values


def _clip(text: str, limit: int) -> tuple[str, bool]:
    marker = "\n...[context truncated at fixed budget]...\n"
    if len(text) <= limit:
        return text, False
    return text[: max(0, limit - len(marker))] + marker, True


def _prompt(rep: dict[str, Any], context: str) -> str:
    return "\n\n".join((
        "你是 AI review preflight 代理，不是人类审查员。只使用给定表示中的事实。",
        "对每个问题返回 answer 和 unsupported；直接证据不在上下文时 unsupported=true，不要猜测。",
        '返回一个 JSON 对象，键为问题 id，值为 {"answer": ..., "unsupported": true|false}。',
        f"Questions:\n{prompt_questions()}",
        f"Representation kind: {rep['kind']}\nRepresentation:\n{context}",
    ))


def _approx_tokens(chars: int) -> int:
    return (chars + 3) // 4


def _score_summary(scores: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(item["correct"] for item in scores)
    unsupported = sum(item["unsupported"] for item in scores)
    gold_unsupported = sum(item["gold_unsupported"] for item in scores)
    return {"correct": correct, "total": len(scores), "accuracy": correct / len(scores), "unsupported": unsupported, "gold_unsupported": gold_unsupported}


def _case(rep: dict[str, Any], window: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    context, truncated = _clip(rep["text"], args.input_budget_chars)
    prompt = _prompt(rep, context)
    gold = gold_answers(window)
    result = {"text": "", "usage": {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}}
    error_type = None
    try:
        result = call_model(prompt, args.model, args.output_budget_tokens, args.env_file)
    except Exception as exc:  # noqa: BLE001 - preserve one failed case in the report
        error_type = type(exc).__name__
    scores = score_response(result["text"], gold)
    return {
        "scale": window["run_count"], "representation": rep["id"], "source_runs": window["run_count"],
        "representation_chars": len(rep["text"]), "context_chars": len(context), "context_truncated": truncated,
        "prompt_chars": len(prompt), "input_tokens_approx": _approx_tokens(len(prompt)),
        "output_budget_tokens": args.output_budget_tokens, "usage": result["usage"], "error_type": error_type,
        "response_status": result.get("response_status"), "model_answer": result["text"], "gold": gold,
        "scores": scores, "summary": _score_summary(scores),
    }


def _aggregate(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = {}
    for case in cases:
        key = (case["scale"], case["representation"])
        groups.setdefault(key, []).append(case)
    return [{"scale": key[0], "representation": key[1], "summary": _score_summary([score for case in values for score in case["scores"]])} for key, values in sorted(groups.items())]


def run(args: argparse.Namespace) -> dict[str, Any]:
    scales = _scales(args.scales)
    source = load_source(args.source_root.resolve())
    cases = []
    representation_meta = []
    for scale in scales:
        window = select_window(source, scale)
        for rep in build_representations(window):
            representation_meta.append({"scale": scale, "id": rep["id"], "chars": len(rep["text"])})
            cases.append(_case(rep, window, args))
    return {"benchmark": "ReviewScaling-preflight", "version": "2026-08-09", "source": str(args.source_root), "real_searchbench": True, "model": args.model, "questions": QUESTIONS, "input_budget_chars": args.input_budget_chars, "input_token_approximation": "ceil(prompt_chars/4)", "output_budget_tokens": args.output_budget_tokens, "scales": scales, "source_counts": {"results": len(source["results"]), "graph_events": len(source["events"]), "traces": sum(len(value) for value in source["traces"].values())}, "representation_meta": representation_meta, "cases": cases, "aggregate": _aggregate(cases), "generated_at": datetime.now(timezone.utc).isoformat()}


def _write_report(output: Path, report: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    report = run(args)
    _write_report(args.output, report)
    print(json.dumps({"output": str(args.output / 'report.json'), "cases": len(report["cases"]), "aggregate": report["aggregate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
