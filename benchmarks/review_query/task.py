"""Inspect task for querying folded SearchBench review state."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.log import ToolEvent, transcript
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import Solver, TaskState, generate, solver, use_tools

CODE_DIR = Path(os.environ["REVIEW_SCALING_CODE"])
sys.path.insert(0, str(CODE_DIR))
from questions import QUESTIONS, gold_answers, score_response

from graph import load_graph, make_tools


def _scales(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item.strip()]


def _question_input(scale: int, question: dict[str, str]) -> str:
    shape = "answer must be a JSON object with the requested fields and numeric counts" if question["id"] == "todo_status" else "answer may be an object, array, or scalar"
    return ("你是研究审查代理，只能使用图谱查询工具，不得猜测或读取原始轨迹。"
            f"先调用至少一个工具查询 scale={scale}，再只返回一个 JSON 对象。问题 id={question['id']}。"
            f"问题：{question['question']}。{shape}。格式：{{\"answers\":{{\"{question['id']}\":"
            "{\"answer\":...,\"unsupported\":true|false}}}。")


def _samples(graphs: dict[int, dict[str, Any]]) -> list[Sample]:
    samples = []
    for scale in sorted(graphs):
        gold = gold_answers({"run_count": scale, "results": list(graphs[scale]["rows"].values()),
                             "events": graphs[scale]["events"], "traces": {}})
        for question in QUESTIONS:
            samples.append(Sample(id=f"s{scale}-{question['id']}", input=_question_input(scale, question),
                                  target=json.dumps(gold, ensure_ascii=False), metadata={"scale": scale, "question_id": question["id"]}))
    return samples


@solver
def graph_tools(graphs: dict[int, dict[str, Any]]) -> Solver:
    return use_tools(make_tools(graphs))


def _usage(state: TaskState) -> dict[str, int]:
    usage = state.output.usage
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    return {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "total_tokens": usage.total_tokens}


def _tool_calls() -> list[str]:
    return [event.function for event in transcript().events if isinstance(event, ToolEvent)]


@scorer(metrics=[accuracy()])
def review_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        metadata = state.metadata
        question_id = metadata["question_id"]
        result = next(item for item in score_response(state.output.completion, json.loads(target.text)) if item["question_id"] == question_id)
        calls = _tool_calls()
        value = CORRECT if result["correct"] else INCORRECT
        return Score(value=value, answer=state.output.completion, explanation=json.dumps(result, ensure_ascii=False),
                     metadata={"question_id": question_id, "tool_calls": calls, "usage": _usage(state)})
    return score


@task
def review_query(source_root: str | None = None, scales: str | None = None) -> Task:
    root = Path(source_root or os.environ["SEARCHBENCH_SOURCE_ROOT"])
    selected = _scales(scales or os.environ.get("REVIEW_QUERY_SCALES", "12,36"))
    graphs = {scale: load_graph(root, scale) for scale in selected}
    return Task(dataset=_samples(graphs), setup=graph_tools(graphs), solver=generate(), scorer=review_scorer(),
                metadata={"benchmark": "ReviewScaling-v3", "scales": selected, "tool_names": ["aggregate", "get", "impact", "subgraph"]})
