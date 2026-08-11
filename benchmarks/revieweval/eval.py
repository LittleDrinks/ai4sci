"""Representation completeness and proxy checks for ReviewEval."""

from __future__ import annotations

import json
from typing import Any


QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "q1",
        "question": "本周期形成的双时标机制是什么？",
        "answer": "快分量优先归于溶剂重排，慢分量交给离子富集复核。",
        "event_ids": ["evt-06", "evt-07", "evt-12"],
        "terms": ["快分量", "慢分量", "溶剂重排", "离子富集"],
        "proxy_terms": ["快分量", "慢分量"],
    },
    {
        "id": "q2",
        "question": "当前解释的失败或限制原因是什么？",
        "answer": "离子富集不能解释快分量，且参比电极漂移可能混入慢分量。",
        "event_ids": ["evt-11", "evt-13"],
        "terms": ["不能解释快分量", "参比电极漂移可能混入慢分量"],
        "proxy_terms": ["参比电极漂移", "慢分量"],
    },
    {
        "id": "q3",
        "question": "当前有哪些待执行行动？",
        "answer": "同位素替换、清洗复测、同步采集阻抗与时域 SFG。",
        "event_ids": ["evt-08", "evt-10", "evt-14"],
        "terms": ["同位素替换", "清洗复测", "同步阻抗"],
        "proxy_terms": ["同位素替换", "清洗复测", "同步"],
    },
    {
        "id": "q4",
        "question": "标定链缺口影响哪个后续行动？",
        "answer": "参比电极漂移可能混入慢分量，影响用于分离慢变量的同步阻抗行动。",
        "event_ids": ["evt-13", "evt-14"],
        "terms": ["参比电极漂移可能混入慢分量", "分离慢变量"],
        "proxy_terms": [["同步阻抗", "同步采集阻抗"], "参比漂移"],
    },
]


def _event_map(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {event["id"]: event for event in events}


def progressive_representation(dataset: dict[str, Any]) -> dict[str, Any]:
    events = dataset["events"]
    artifacts = dataset["artifacts"]
    stages = []
    for index in range(1, len(events) + 1):
        visible = events[:index]
        stages.append({"stage": index, "event_ids": [event["id"] for event in visible], "nodes": visible})
    text = json.dumps({"events": events, "artifacts": artifacts}, ensure_ascii=False, sort_keys=True)
    return {"id": "progressive_graph", "kind": "progressive_graph", "stages": stages, "text": text}


def flat_report_representation(dataset: dict[str, Any]) -> dict[str, Any]:
    event_lines = []
    for event in dataset["events"]:
        parents = ",".join(event.get("parents", [])) or "none"
        artifacts = ",".join(event.get("artifacts", [])) or "none"
        event_lines.append(
            f"{event['id']} | {event['at']} | {event['title']} | {event['nodeText']} | {event['detail']} | status={event['status']} | parents={parents} | artifacts={artifacts}"
        )
    artifact_lines = [f"{item['id']} | {item['source']} | {item['locator']} | {item['fact']}" for item in dataset["artifacts"]]
    text = "研究周期平铺报告\n" + "\n".join(event_lines) + "\n产物\n" + "\n".join(artifact_lines)
    return {"id": "flat_report", "kind": "flat_report", "text": text, "event_ids": [event["id"] for event in dataset["events"]]}


def raw_log_representation(dataset: dict[str, Any]) -> dict[str, Any]:
    lines = [json.dumps({"type": "event", **event}, ensure_ascii=False, sort_keys=True) for event in dataset["events"]]
    lines.extend(json.dumps({"type": "artifact", **item}, ensure_ascii=False, sort_keys=True) for item in dataset["artifacts"])
    return {"id": "raw_log", "kind": "raw_log", "text": "\n".join(lines), "event_ids": [event["id"] for event in dataset["events"]]}


def representations(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return [progressive_representation(dataset), flat_report_representation(dataset), raw_log_representation(dataset)]


def _serialized(rep: dict[str, Any]) -> str:
    return json.dumps(rep, ensure_ascii=False, sort_keys=True)


def completeness(rep: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    serialized = _serialized(rep)
    expected_events = {event["id"] for event in dataset["events"]}
    expected_artifacts = {item["id"] for item in dataset["artifacts"]}
    actual_events = {event_id for event_id in expected_events if event_id in serialized}
    actual_artifacts = {item_id for item_id in expected_artifacts if item_id in serialized}
    checks = [
        {"name": "all_event_ids", "passed": actual_events == expected_events, "missing": sorted(expected_events - actual_events)},
        {"name": "all_artifact_ids", "passed": actual_artifacts == expected_artifacts, "missing": sorted(expected_artifacts - actual_artifacts)},
    ]
    if rep["kind"] == "progressive_graph":
        checks.append(_progressive_edges(rep, expected_events))
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _progressive_edges(rep: dict[str, Any], expected_events: set[str]) -> dict[str, Any]:
    stages = rep["stages"]
    final_ids = set(stages[-1]["event_ids"]) if stages else set()
    edge_ok = all(set(node.get("parents", [])).issubset(expected_events) for node in stages[-1]["nodes"])
    return {"name": "progressive_edges", "passed": final_ids == expected_events and edge_ok, "stages": len(stages)}


def answer_precheck(rep: dict[str, Any], question: dict[str, Any]) -> dict[str, Any]:
    serialized = _serialized(rep)
    terms = [term for term in question["terms"] if term not in serialized]
    events = [event_id for event_id in question["event_ids"] if event_id not in serialized]
    return {
        "question_id": question["id"],
        "passed": not terms and not events,
        "missing_terms": terms,
        "missing_event_ids": events,
        "answer": question["answer"],
    }


def evaluate_representation(rep: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    checks = completeness(rep, dataset)
    answers = [answer_precheck(rep, question) for question in QUESTIONS]
    return {
        "representation": rep["id"],
        "completeness": checks,
        "answer_precheck": answers,
        "passed": checks["passed"] and all(answer["passed"] for answer in answers),
    }


def proxy_prompt(rep: dict[str, Any]) -> str:
    questions = "\n".join(f"{q['id']}: {q['question']}" for q in QUESTIONS)
    return (
        "You are a review preflight proxy. Use only the supplied research representation. "
        "Return JSON with one concise answer per question id; do not claim a human review.\n"
        f"Questions:\n{questions}\nRepresentation:\n{rep['text']}"
    )
