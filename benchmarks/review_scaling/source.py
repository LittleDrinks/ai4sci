"""Load SearchBench full-run artifacts without exposing secrets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _usage(row: dict[str, Any]) -> dict[str, int]:
    usage = row.get("payload", {}).get("response", {}).get("usage", {})
    return {key: int(usage.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def _trace_file(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    usage = {key: 0 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    for row in rows:
        for key, value in _usage(row).items():
            usage[key] += value
    return {
        "name": path.name,
        "relative_path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "events": len(rows),
        "usage": usage,
        "lines": lines,
    }


def _traces(root: Path, run_id: str) -> list[dict[str, Any]]:
    trace_dir = root / "traces" / run_id
    return [_trace_file(path) for path in sorted(trace_dir.glob("trace_*.jsonl"))]


def load_source(root: Path) -> dict[str, Any]:
    results = sorted(read_jsonl(root / "results.jsonl"), key=lambda row: row["run_id"])
    events = read_jsonl(root / "graph_events.jsonl")
    events.sort(key=lambda row: (row["run_id"], row.get("session_index", -1), row["event"]))
    traces = {row["run_id"]: _traces(root, row["run_id"]) for row in results}
    return {"root": str(root), "results": results, "events": events, "traces": traces}


def select_window(source: dict[str, Any], run_count: int) -> dict[str, Any]:
    results = source["results"][:run_count]
    run_ids = {row["run_id"] for row in results}
    events = [row for row in source["events"] if row["run_id"] in run_ids]
    traces = {run_id: source["traces"][run_id] for run_id in run_ids}
    return {"results": results, "events": events, "traces": traces, "run_count": len(results)}
