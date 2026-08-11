from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from researchharness import create_agent

from .config import Settings
from .prompts import SUBMISSION_KINDS, task_prompt


def prepare_workspace(root: Path, task: dict[str, Any]) -> Path:
    workspace = root / task["id"] / task["attempt_id"]
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "traces").mkdir(exist_ok=True)
    if task["job"]["revision"] > 0:
        remove_outputs(workspace)
    context = {key: task[key] for key in ("job", "agent", "project", "subject", "context")}
    data = json.dumps(context, ensure_ascii=False, indent=2)
    (workspace / "context.json").write_text(data, encoding="utf-8")
    return workspace


def remove_outputs(workspace: Path) -> None:
    for name in ("submission.json", "report.html", "audit.json"):
        path = workspace / name
        if path.exists():
            path.unlink()


def build_agent(settings: Settings, task: dict[str, Any], workspace: Path):
    return create_agent(
        model_name=task["agent"]["model"],
        api_key=settings.api_key,
        api_base=settings.api_base,
        max_rounds=8,
        max_runtime_seconds=600,
        workspace_root=str(workspace),
        trace_dir=str(workspace / "traces"),
        role_prompt=task["agent"]["instructions"],
        require_env=False,
    )


def run_harness(settings: Settings, task: dict[str, Any], workspace: Path) -> str:
    agent = build_agent(settings, task, workspace)
    messages = prior_messages(task, workspace)
    session = agent._run_session(
        task_prompt(task["job"]),
        workspace_root=str(workspace),
        prior_messages=messages,
    )
    return session["result_text"]


def prior_messages(task: dict[str, Any], workspace: Path) -> list[dict[str, Any]] | None:
    if task["job"]["revision"] == 0 or task["job"]["review_mode"] == "restart":
        return None
    path = latest_session_state(workspace)
    return json.loads(path.read_text(encoding="utf-8"))["messages"]


def latest_session_state(workspace: Path) -> Path:
    paths = list((workspace / "traces").glob("session_state_*.json"))
    if not paths:
        raise FileNotFoundError("revision requires a prior ResearchHarness session")
    return max(paths, key=lambda path: path.stat().st_mtime_ns)


def read_submission(workspace: Path) -> dict[str, Any]:
    value = json.loads((workspace / "submission.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("submission.json must contain an object")
    return value


def read_audit(workspace: Path) -> dict[str, Any]:
    value = json.loads((workspace / "audit.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("audit.json must contain an object")
    return value


def collect_outputs(task: dict[str, Any], workspace: Path, result: str) -> dict[str, Any]:
    if task["job"]["kind"] == "audit":
        return {"result_text": result, "audit": read_audit(workspace)}
    submission = read_submission(workspace)
    expected = SUBMISSION_KINDS[task["job"]["kind"]]
    if submission.get("kind") != expected:
        raise ValueError(f"{task['job']['kind']} jobs require kind={expected} submissions")
    html = None
    if task["job"]["kind"] == "html_report":
        html = (workspace / "report.html").read_text(encoding="utf-8")
    return {"result_text": result, "submission": submission, "html": html}
