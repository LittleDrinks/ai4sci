"""Fixed review questions and deterministic event-field scoring."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any


QUESTIONS = [
    {"id": "fact_counts", "question": "在输入窗口中，最终 audit=accepted 的 run 数和 execution=completed 的 run 数分别是多少？"},
    {"id": "impact_scope", "question": "哪些 run_id 最终被拒绝或跳过 execution，构成受影响范围？"},
    {"id": "todo_status", "question": "哪些确定性字段表明仍有待办？请给出 method_family_status、pairwise_adjudication、isolated 数和跳过执行数。"},
    {"id": "tail_fact", "question": "如果上下文包含 run_id=r-s2-c2，它的最终 audit 与 execution 状态是什么？没有直接证据时返回 unsupported。"},
]


def _row(window: dict[str, Any], run_id: str) -> dict[str, Any] | None:
    return next((row for row in window["results"] if row["run_id"] == run_id), None)


def _states(window: dict[str, Any]) -> dict[str, dict[str, str]]:
    states = {row["run_id"]: {} for row in window["results"]}
    for event in window["events"]:
        if event["event"] == "audit_completed":
            states[event["run_id"]]["audit"] = event["status"]
        if event["event"] == "execution_completed":
            states[event["run_id"]]["execution"] = event["execution"]["status"]
    return states


def _gold_fact(window: dict[str, Any]) -> dict[str, Any]:
    states = _states(window)
    return {"supported": bool(states), "answer": {
        "accepted_final_count": sum(state.get("audit") == "accepted" for state in states.values()),
        "execution_completed_count": sum(state.get("execution") == "completed" for state in states.values()),
    }}


def _gold_impact(window: dict[str, Any]) -> dict[str, Any]:
    states = _states(window)
    impacted = [run_id for run_id, state in states.items() if state.get("audit") != "accepted" or state.get("execution") != "completed"]
    return {"supported": bool(states), "answer": {"run_ids": sorted(impacted)}}


def _gold_todo(window: dict[str, Any]) -> dict[str, Any]:
    rows = window["results"]
    states = _states(window)
    statuses = sorted({f"method_family_status={row['method_family_status']}" for row in rows})
    statuses += sorted({f"pairwise_adjudication={row['pairwise_adjudication']}" for row in rows})
    skipped = sum(state.get("execution") == "skipped" for state in states.values())
    isolated = sum(event["event"] == "candidate_isolated" for event in window["events"])
    return {"supported": bool(states), "answer": {"fields": statuses, "isolated_count": isolated, "execution_skipped_count": skipped}}


def _gold_tail(window: dict[str, Any]) -> dict[str, Any]:
    row = _row(window, "r-s2-c2")
    state = _states(window).get("r-s2-c2")
    if row is None or not state:
        return {"supported": False, "answer": {}}
    return {"supported": True, "answer": {"audit": state["audit"], "execution": state["execution"]}}


def gold_answers(window: dict[str, Any]) -> dict[str, dict[str, Any]]:
    builders = (_gold_fact, _gold_impact, _gold_todo, _gold_tail)
    return {question["id"]: builder(window) for question, builder in zip(QUESTIONS, builders)}


def prompt_questions() -> str:
    return "\n".join(f"{question['id']}: {question['question']}" for question in QUESTIONS)


def parse_json(text: str) -> dict[str, Any]:
    candidates = [text.strip()]
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value.get("answers", value) if isinstance(value.get("answers", value), dict) else {}
    return {}


def _bool(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "yes", "1"}


def _text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value


def _scalars(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _scalars(child)]
    if isinstance(value, list):
        return [item for child in value for item in _scalars(child)]
    return [value]


def _numbers(value: Any) -> list[int]:
    return [int(item) for item in _scalars(value) if isinstance(item, (int, float)) and not isinstance(item, bool)]


def _fact_ok(value: Any, answer: dict[str, Any]) -> bool:
    return Counter(_numbers(value)) >= Counter(answer.values())


def _impact_ok(value: Any, answer: dict[str, Any]) -> bool:
    text = _text(value)
    found = set(re.findall(r"[a-z][a-z_]*-s\d+-c\d+", text))
    return found == set(answer["run_ids"])


def _todo_ok(value: Any, answer: dict[str, Any]) -> bool:
    text = _text(value)
    statuses = [field.split("=", 1)[1] for field in answer["fields"]]
    expected_counts = [answer["isolated_count"], answer["execution_skipped_count"]]
    return all(status in text for status in statuses) and Counter(_numbers(value)) >= Counter(expected_counts)


def _tail_ok(value: Any, answer: dict[str, Any]) -> bool:
    return Counter(str(item) for item in _scalars(value)) >= Counter(answer.values())


def _answer_ok(question_id: str, value: Any, answer: dict[str, Any]) -> bool:
    checks = {"fact_counts": _fact_ok, "impact_scope": _impact_ok, "todo_status": _todo_ok, "tail_fact": _tail_ok}
    return checks[question_id](value, answer)


def _score_item(question: dict[str, Any], value: Any, expected: dict[str, Any]) -> dict[str, Any]:
    value = value if isinstance(value, dict) else {"answer": value}
    answer = value.get("answer", value)
    unsupported = _bool(value.get("unsupported", False))
    supported = expected["supported"]
    answer_correct = not supported or _answer_ok(question["id"], answer, expected["answer"])
    return {"question_id": question["id"], "correct": unsupported == (not supported) and answer_correct, "answer_correct": answer_correct, "unsupported": unsupported, "gold_unsupported": not supported}


def score_response(raw: str, gold: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    parsed = parse_json(raw)
    return [_score_item(question, parsed.get(question["id"], {}), gold[question["id"]]) for question in QUESTIONS]
