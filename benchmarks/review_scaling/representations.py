"""Progressive graph, flat report, and raw-log views of SearchBench data."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _trace_summary(traces: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "files": len(traces),
        "events": sum(item["events"] for item in traces),
        "bytes": sum(item["bytes"] for item in traces),
        "usage": {key: sum(item["usage"][key] for item in traces) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
    }


def _run_node(row: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": row["run_id"],
        "kind": "run",
        "stage": 0,
        "strategy": row["strategy"],
        "seed": row["seed"],
        "candidate_index": row["candidate_index"],
        "final_audit": row["audit"]["status"],
        "execution": row["execution"]["status"],
        "method_family_status": row["method_family_status"],
        "pairwise_adjudication": row["pairwise_adjudication"],
        "trace": _trace_summary(traces),
    }


def _event_node(index: int, event: dict[str, Any]) -> dict[str, Any]:
    node = {key: value for key, value in event.items() if key not in {"run_id", "event"}}
    return {"id": f"{event['run_id']}/e{index}", "kind": event["event"], "stage": index + 1, "run_id": event["run_id"], **node}


def _graph_text(window: dict[str, Any]) -> str:
    nodes = []
    edges = []
    previous = None
    for row in window["results"]:
        run_id = row["run_id"]
        nodes.append(_run_node(row, window["traces"][run_id]))
    for index, event in enumerate(window["events"]):
        event_id = f"{event['run_id']}/e{index}"
        nodes.append(_event_node(index, event))
        edges.append({"from": event["run_id"], "to": event_id, "relation": "records"})
        if previous:
            edges.append({"from": previous, "to": event_id, "relation": "progresses"})
        previous = event_id
    return _json({"kind": "progressive_graph", "nodes": nodes, "edges": edges})


def _session_line(session: dict[str, Any]) -> str:
    fields = {
        "stage": session["stage"],
        "visibility": session["context"].get("visibility"),
        "audit": session["audit"]["status"],
        "family": session["audit"].get("family_id"),
        "candidate": session.get("candidate", {}),
        "usage": session["trace"].get("usage", {}),
    }
    return _json(fields)


def _report_line(row: dict[str, Any], traces: list[dict[str, Any]]) -> str:
    trace = _trace_summary(traces)
    sessions = ";".join(_session_line(session) for session in row["sessions"])
    return " | ".join((
        f"run_id={row['run_id']}",
        f"strategy={row['strategy']}",
        f"seed={row['seed']}",
        f"candidate_index={row['candidate_index']}",
        f"final_audit={row['audit']['status']}",
        f"execution={row['execution']['status']}",
        f"method_family_status={row['method_family_status']}",
        f"pairwise_adjudication={row['pairwise_adjudication']}",
        f"trace={_json(trace)}",
        f"sessions={sessions}",
    ))


def _flat_text(window: dict[str, Any]) -> str:
    lines = ["SEARCHBENCH FLAT REPORT", "source=results.jsonl + graph_events.jsonl + traces"]
    lines.extend(_report_line(row, window["traces"][row["run_id"]]) for row in window["results"])
    lines.append("GRAPH EVENTS")
    lines.extend(_json(event) for event in window["events"])
    return "\n".join(lines)


def _raw_text(window: dict[str, Any]) -> str:
    lines = ["# results.jsonl"]
    lines.extend(_json(row) for row in window["results"])
    lines.append("# graph_events.jsonl")
    lines.extend(_json(event) for event in window["events"])
    lines.append("# traces/*.jsonl")
    for run_id in sorted(window["traces"]):
        for trace in window["traces"][run_id]:
            lines.extend(f"{run_id}\t{trace['name']}\t{line}" for line in trace["lines"])
    return "\n".join(lines)


def _event_states(window: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states = {row["run_id"]: {"isolated": False} for row in window["results"]}
    for event in window["events"]:
        state = states[event["run_id"]]
        if event["event"] == "audit_completed":
            state["audit"] = event["status"]
        if event["event"] == "execution_completed":
            state["execution"] = event["execution"]["status"]
        if event["event"] == "candidate_isolated":
            state["isolated"] = True
    return states


def _review_row(row: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    candidate = row["final"].get("candidate", {})
    return {
        "id": row["run_id"], "strategy": row["strategy"], "audit": state.get("audit"),
        "execution": state.get("execution"), "isolated": state["isolated"],
        "method_family_status": row["method_family_status"],
        "pairwise_adjudication": row["pairwise_adjudication"], "title": candidate.get("title"),
    }


def _facets(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    fields = ("audit", "execution", "method_family_status", "pairwise_adjudication")
    return {field: dict(sorted(Counter(row[field] for row in rows).items())) for field in fields}


def _review_text(window: dict[str, Any]) -> str:
    states = _event_states(window)
    rows = [_review_row(row, states[row["run_id"]]) for row in window["results"]]
    exceptions = [row for row in rows if row["audit"] != "accepted" or row["execution"] != "completed" or row["isolated"]]
    view = {
        "kind": "derived_review_view", "run_count": len(rows), "facets": _facets(rows),
        "isolated_count": sum(row["isolated"] for row in rows), "exceptions": exceptions,
        "runs_by_id": {row["id"]: row for row in rows},
    }
    return _json(view)


def _representation(name: str, builder: Any, window: dict[str, Any]) -> dict[str, Any]:
    text = builder(window)
    return {"id": name, "kind": name, "text": text, "run_count": window["run_count"]}


def build_representations(window: dict[str, Any]) -> list[dict[str, Any]]:
    builders = (
        ("graph_dump", _graph_text), ("review_view", _review_text),
        ("flat_report", _flat_text), ("raw_log", _raw_text),
    )
    return [_representation(name, builder, window) for name, builder in builders]
