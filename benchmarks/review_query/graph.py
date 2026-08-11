"""Read-only typed queries over folded SearchBench event state."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from inspect_ai.tool import Tool

from source import load_source, select_window


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _trace_usage(traces: list[dict[str, Any]]) -> dict[str, int]:
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    return {key: sum(trace["usage"][key] for trace in traces) for key in keys}


def _base_row(row: dict[str, Any], traces: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = row.get("final", {}).get("candidate", {})
    return {
        "run_id": row["run_id"], "strategy": row["strategy"], "seed": row["seed"],
        "candidate_index": row["candidate_index"], "title": candidate.get("title"),
        "audit": None, "execution": None, "isolated": False,
        "method_family_status": row["method_family_status"],
        "pairwise_adjudication": row["pairwise_adjudication"],
        "trace_events": sum(trace["events"] for trace in traces), "usage": _trace_usage(traces),
        "event_count": 0,
    }


def _apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    state["event_count"] += 1
    if event["event"] == "audit_completed":
        state["audit"] = event["status"]
    elif event["event"] == "execution_completed":
        state["execution"] = event["execution"]["status"]
    elif event["event"] == "candidate_isolated":
        state["isolated"] = True


def fold_window(window: dict[str, Any]) -> dict[str, Any]:
    rows = {row["run_id"]: _base_row(row, window["traces"][row["run_id"]]) for row in window["results"]}
    events = []
    for event in window["events"]:
        if event["run_id"] not in rows:
            continue
        _apply_event(rows[event["run_id"]], event)
        events.append(event)
    return {"scale": window["run_count"], "rows": dict(sorted(rows.items())), "events": events}


def load_graph(root: Path, scale: int) -> dict[str, Any]:
    source = load_source(root)
    return fold_window(select_window(source, scale))


def _not_found(scale: int, run_id: str | None = None) -> str:
    value = {"found": False, "scale": scale}
    if run_id is not None:
        value["run_id"] = run_id
    return _json(value)


def _check(graphs: dict[int, dict[str, Any]], scale: int) -> dict[str, Any] | None:
    return graphs.get(scale)


def aggregate_json(graphs: dict[int, dict[str, Any]], scale: int) -> str:
    graph = _check(graphs, scale)
    if graph is None:
        return _not_found(scale)
    rows = list(graph["rows"].values())
    fields = ("audit", "execution", "method_family_status", "pairwise_adjudication")
    counts = {field: dict(sorted(Counter(row[field] for row in rows).items())) for field in fields}
    impacted = [row["run_id"] for row in rows if row["audit"] != "accepted" or row["execution"] != "completed"]
    isolated_count = sum(event["event"] == "candidate_isolated" for event in graph["events"])
    return _json({"found": True, "scale": scale, "run_count": len(rows), "counts": counts,
                  "isolated_count": isolated_count, "impacted_run_ids": impacted})


def get_json(graphs: dict[int, dict[str, Any]], scale: int, run_id: str) -> str:
    graph = _check(graphs, scale)
    row = graph["rows"].get(run_id) if graph else None
    return _json({"found": True, "scale": scale, "record": row}) if row else _not_found(scale, run_id)


def impact_json(graphs: dict[int, dict[str, Any]], scale: int) -> str:
    graph = _check(graphs, scale)
    if graph is None:
        return _not_found(scale)
    records = []
    for row in graph["rows"].values():
        if row["audit"] == "accepted" and row["execution"] == "completed":
            continue
        records.append({"run_id": row["run_id"], "audit": row["audit"], "execution": row["execution"],
                        "isolated": row["isolated"]})
    return _json({"found": True, "scale": scale, "count": len(records), "records": records})


def subgraph_json(graphs: dict[int, dict[str, Any]], scale: int, run_id: str, depth: int) -> str:
    graph = _check(graphs, scale)
    if graph is None or run_id not in graph["rows"]:
        return _not_found(scale, run_id)
    events = [event for event in graph["events"] if event["run_id"] == run_id]
    nodes = [{"id": run_id, "kind": "run", **graph["rows"][run_id]}]
    nodes.extend({"id": f"{run_id}/e{index}", "kind": event["event"], "event": event}
                 for index, event in enumerate(events[: max(depth, 0)]))
    edges = [{"from": run_id, "to": node["id"], "relation": "records"} for node in nodes[1:]]
    return _json({"found": True, "scale": scale, "run_id": run_id, "depth": depth, "nodes": nodes, "edges": edges})


def _aggregate_tool(graphs: dict[int, dict[str, Any]]) -> "Tool":
    from inspect_ai.tool import tool

    @tool(name="aggregate")
    def aggregate_tool() -> Tool:
        async def execute(scale: int) -> str:
            """Return deterministic counts and impacted IDs for a graph window.

            Args: scale: Number of SearchBench runs in the window.
            """
            return aggregate_json(graphs, scale)
        return execute
    return aggregate_tool()


def _get_tool(graphs: dict[int, dict[str, Any]]) -> "Tool":
    from inspect_ai.tool import tool

    @tool(name="get")
    def get_tool() -> Tool:
        async def execute(scale: int, run_id: str) -> str:
            """Return one folded run record, or found=false for an unknown ID.

            Args: scale: Window size. run_id: Exact run identifier.
            """
            return get_json(graphs, scale, run_id)
        return execute
    return get_tool()


def _impact_tool(graphs: dict[int, dict[str, Any]]) -> "Tool":
    from inspect_ai.tool import tool

    @tool(name="impact")
    def impact_tool() -> Tool:
        async def execute(scale: int) -> str:
            """Return runs whose audit or execution state is not complete.

            Args: scale: Number of SearchBench runs in the window.
            """
            return impact_json(graphs, scale)
        return execute
    return impact_tool()


def _subgraph_tool(graphs: dict[int, dict[str, Any]]) -> "Tool":
    from inspect_ai.tool import tool

    @tool(name="subgraph")
    def subgraph_tool() -> Tool:
        async def execute(scale: int, run_id: str, depth: int) -> str:
            """Return a bounded run-centered event subgraph.

            Args: scale: Window size. run_id: Exact ID. depth: Event limit.
            """
            return subgraph_json(graphs, scale, run_id, depth)
        return execute
    return subgraph_tool()


def make_tools(graphs: dict[int, dict[str, Any]]) -> list["Tool"]:
    return [_aggregate_tool(graphs), _get_tool(graphs), _impact_tool(graphs), _subgraph_tool(graphs)]
