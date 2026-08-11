from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import ControlPlane


def publish_trace(api: ControlPlane, task: dict[str, Any], workspace: Path) -> None:
    for value in trace_rows(workspace):
        normalized = normalize(value)
        if normalized:
            api.event(task, normalized[0], normalized[1], **normalized[2])


def trace_rows(workspace: Path) -> list[dict[str, Any]]:
    paths = sorted((workspace / "traces").glob("trace_*.jsonl"))
    if not paths:
        return []
    return [json.loads(line) for line in paths[-1].read_text().splitlines() if line]


def normalize(value: dict[str, Any]) -> tuple[str, str, dict] | None:
    tools = value.get("tool_names") or []
    if tools:
        return "tool", f"Used {', '.join(tools)}", trace_payload(value)
    if value.get("role") == "tool":
        return "tool_result", concise(value.get("text", "")), trace_payload(value)
    if value.get("role") == "assistant" and value.get("text"):
        return "message", concise(value["text"]), trace_payload(value)
    return None


def trace_payload(value: dict[str, Any]) -> dict[str, Any]:
    return {"trace_event_index": value.get("event_index"), "trace_timestamp": value.get("timestamp")}


def concise(value: str, limit: int = 500) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[:limit] + "..."
