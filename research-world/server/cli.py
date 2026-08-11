from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import TextIO

import httpx

from .app import app
from .clients import EmbeddingClient, HarnessAgents, McpClient, SearchBroker
from .config import load_settings
from .orchestrator import Orchestrator
from .runner import EnvironmentBuilder, ExperimentRunner, HttpRunnerController
from .tools import ToolBroker
from .world import World


OBJECT = {"type": "object"}
SCHEMAS = {
    "project.create": {**OBJECT, "required": ["name", "root", "question"]},
    "project.sync": {**OBJECT, "required": ["project"]},
    "project.show": {**OBJECT, "required": ["project"]},
    "project.apply": {**OBJECT, "required": ["project", "run"]},
    "run.start": {**OBJECT, "required": ["project", "question_id"]},
    "run.show": {**OBJECT, "required": ["run_id"]},
    "run.watch": {**OBJECT, "required": ["run_id"]},
    "review.resolve": {**OBJECT, "required": ["decision"]},
    "doctor": OBJECT,
    "task.show": {**OBJECT, "required": ["attempt"]},
    "task.event": {**OBJECT, "required": ["type", "entity", "payload"]},
    "graph.search": {**OBJECT, "required": ["attempt", "project", "query"]},
    "graph.get": {**OBJECT, "required": ["attempt", "node_id"]},
    "artifact.inspect": {**OBJECT, "required": ["attempt", "artifact_id"]},
    "artifact.read": {**OBJECT, "required": ["attempt", "artifact_id"]},
    "artifact.materialize": {**OBJECT, "required": ["attempt", "artifact_id", "path"]},
    "artifact.add": {**OBJECT, "required": ["attempt", "file", "media_type"]},
    "tools.list": {**OBJECT, "required": ["attempt"]},
    "tools.call": {**OBJECT, "required": ["server", "tool", "arguments"]},
    "source.acquire": {**OBJECT, "required": ["attempt", "url"]},
    "environment.build": {**OBJECT, "required": ["setup"]},
    "experiment.run": {**OBJECT, "required": ["environment_id", "command", "inputs"]},
    "submit.research-package": {**OBJECT, "required": ["generation_id", "strategy", "sources", "claims", "artifacts", "code"]},
}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rw")
    groups = root.add_subparsers(dest="group", required=True)
    _project_parser(groups)
    _run_parser(groups)
    _task_parser(groups)
    _graph_parser(groups)
    _artifact_parser(groups)
    _tools_parser(groups)
    _execution_parser(groups)
    _misc_parser(groups)
    return root


def _project_parser(groups) -> None:
    project = groups.add_parser("project").add_subparsers(dest="action", required=True)
    create = project.add_parser("create")
    create.add_argument("--file", type=Path)
    for action in ("sync", "show", "apply"):
        command = project.add_parser(action)
        command.add_argument("--project", required=True)
    project.choices["apply"].add_argument("--run", required=True)


def _run_parser(groups) -> None:
    run = groups.add_parser("run").add_subparsers(dest="action", required=True)
    start = run.add_parser("start")
    start.add_argument("--project", required=True)
    start.add_argument("--question-id", type=int, required=True)
    start.add_argument("--apply-selected", action="store_true")
    start.add_argument("--wait", action="store_true")
    for action in ("show", "watch"):
        command = run.add_parser(action)
        command.add_argument("run_id")


def _task_parser(groups) -> None:
    task = groups.add_parser("task").add_subparsers(dest="action", required=True)
    for action in ("show", "event"):
        command = task.add_parser(action)
        command.add_argument("--attempt", required=True)
        if action == "event":
            command.add_argument("--file", type=Path)


def _graph_parser(groups) -> None:
    graph = groups.add_parser("graph").add_subparsers(dest="action", required=True)
    search = graph.add_parser("search")
    search.add_argument("query")
    search.add_argument("--project", required=True)
    get = graph.add_parser("get")
    get.add_argument("node_id")
    for command in (search, get):
        command.add_argument("--attempt", required=True)


def _artifact_parser(groups) -> None:
    artifact = groups.add_parser("artifact").add_subparsers(dest="action", required=True)
    for action in ("inspect", "read", "materialize"):
        command = artifact.add_parser(action)
        command.add_argument("artifact_id")
        command.add_argument("--attempt", required=True)
        if action == "materialize":
            command.add_argument("path", type=Path)
    add = artifact.add_parser("add")
    add.add_argument("--attempt", required=True)
    add.add_argument("--file", type=Path, required=True)
    add.add_argument("--media-type", required=True)


def _tools_parser(groups) -> None:
    tools = groups.add_parser("tools").add_subparsers(dest="action", required=True)
    for action in ("list", "call"):
        command = tools.add_parser(action)
        command.add_argument("--attempt", required=True)
        if action == "call":
            command.add_argument("--file", type=Path)


def _execution_parser(groups) -> None:
    source = groups.add_parser("source").add_subparsers(dest="action", required=True)
    acquire = source.add_parser("acquire")
    acquire.add_argument("url")
    acquire.add_argument("--attempt", required=True)
    environment = groups.add_parser("environment").add_subparsers(dest="action", required=True)
    build = environment.add_parser("build")
    build.add_argument("--attempt", required=True)
    build.add_argument("--file", type=Path)
    experiment = groups.add_parser("experiment").add_subparsers(dest="action", required=True)
    run = experiment.add_parser("run")
    run.add_argument("--attempt", required=True)
    run.add_argument("--file", type=Path)
    review = groups.add_parser("review").add_subparsers(dest="action", required=True)
    resolve = review.add_parser("resolve")
    resolve.add_argument("--run", required=True)
    resolve.add_argument("--file", type=Path)


def _misc_parser(groups) -> None:
    schema = groups.add_parser("schema")
    schema.add_argument("command", choices=sorted(SCHEMAS))
    serve = groups.add_parser("serve")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", default=8095, type=int)
    doctor = groups.add_parser("doctor")
    for flag in ("model", "embedding", "mcp", "runner"):
        doctor.add_argument(f"--{flag}", action="store_true")
    submit = groups.add_parser("submit").add_subparsers(dest="action", required=True)
    package = submit.add_parser("research-package")
    package.add_argument("--attempt", required=True)
    package.add_argument("--file", type=Path)


def main(argv: list[str] | None = None, world: World | None = None,
         output: TextIO | None = None, error: TextIO | None = None) -> int:
    args = parser().parse_args(argv)
    output, error = output or sys.stdout, error or sys.stderr
    world = world or default_world()
    try:
        if args.group == "run" and args.action == "watch":
            return watch_run(world, args.run_id, output)
        data = dispatch(args, world)
        print(json.dumps({"schema_version": "1", "ok": True, "data": data}), file=output)
        return 0
    except Exception as exc:
        body = {"schema_version": "1", "ok": False, "error": {"code": "command_failed", "message": str(exc)}}
        print(json.dumps(body), file=error)
        return 2


def dispatch(args, world: World):
    handlers = {"project": project_command, "run": run_command, "task": task_command,
                "graph": graph_command, "artifact": artifact_command, "tools": tools_command,
                "submit": submit_command, "source": source_command, "environment": environment_command,
                "experiment": experiment_command, "review": review_command}
    if args.group == "schema":
        return SCHEMAS[args.command]
    if args.group == "serve":
        return serve(args)
    if args.group == "doctor":
        return doctor(args)
    return handlers[args.group](args, world)


def project_command(args, world: World):
    if args.action == "create":
        value = read_json(args.file)
        return world.create_project(value["name"], project_root(value["root"]), value["question"])
    project = world.project_by_name(args.project)
    if args.action == "sync":
        return world.sync_project(project["id"])
    if args.action == "apply":
        return apply_project(world, project, args.run)
    return project


def run_command(args, world: World):
    if args.action == "start":
        project = world.project_by_name(args.project)
        run = world.create_run(project["id"], args.question_id, args.apply_selected)
        return wait_or_execute(world, run) if args.wait else run
    if args.action == "show":
        return run_detail(world, args.run_id)
    return world.events(args.run_id)


def task_command(args, world: World):
    require_task(world, args.attempt)
    if args.action == "show":
        return world.attempt(args.attempt)
    value = read_json(args.file)
    attempt = world.attempt(args.attempt)
    return world.record_event(attempt["run_id"], attempt["generation_id"], attempt["id"], "agent", value["type"], value["entity"], value["payload"])


def graph_command(args, world: World):
    attempt = require_task(world, args.attempt)
    project_id = world.attempt_project(attempt["id"])["id"]
    if args.action == "search":
        if world.project_by_name(args.project)["id"] != project_id:
            raise PermissionError("task cannot search another project")
        return world.search(project_id, args.query)
    return world.admitted_node(args.node_id, project_id)


def artifact_command(args, world: World):
    attempt = require_task(world, args.attempt)
    if args.action == "add":
        artifact = world.add_artifact(task_path(args.file).read_bytes(), args.media_type)
        world.record_event(attempt["run_id"], attempt["generation_id"], attempt["id"], "agent", "artifact_added", {"type": "artifact", "id": artifact["id"]}, {})
        return artifact
    world.require_artifact_access(attempt["id"], args.artifact_id)
    if args.action == "inspect":
        return world.artifacts.get(args.artifact_id)
    content = world.artifacts.read(args.artifact_id)
    if args.action == "materialize":
        path = task_path(args.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return {"path": str(path), "size": len(content)}
    return {"content": content.decode(), "size": len(content)}


def tools_command(args, world: World):
    require_task(world, args.attempt)
    broker = ToolBroker(world, McpClient())
    if args.action == "list":
        return broker.list(args.attempt)
    value = read_json(args.file)
    return broker.call(args.attempt, value["server"], value["tool"], value["arguments"])


def submit_command(args, world: World):
    attempt = require_task(world, args.attempt)
    value = read_json(args.file)
    if value.get("generation_id") != attempt["generation_id"]:
        raise PermissionError("task can submit only its own generation")
    run = world.run(attempt["run_id"])
    return world.submit_package(run["project_id"], value)


def source_command(args, world: World):
    attempt = require_task(world, args.attempt)
    result = ToolBroker(world, McpClient()).call(args.attempt, "anysearch", "extract", {"url": args.url})
    content = result if isinstance(result, str) else json.dumps(result)
    artifact = world.add_artifact(content.encode(), "text/markdown")
    project_id = world.run(attempt["run_id"])["project_id"]
    lines = max(1, len(content.splitlines()))
    snapshot = world.add_source_snapshot(project_id, args.url, artifact, {"line_start": 1, "line_end": lines})
    world.record_event(attempt["run_id"], attempt["generation_id"], attempt["id"], "agent", "source_acquired", {"type": "artifact", "id": artifact["id"]}, {"snapshot_id": snapshot["id"]})
    return snapshot


def environment_command(args, world: World):
    attempt = require_task(world, args.attempt)
    value = read_json(args.file)
    project_id = world.run(attempt["run_id"])["project_id"]
    return EnvironmentBuilder(world, runner_controller()).build(project_id, args.attempt, value["setup"])


def experiment_command(args, world: World):
    attempt = require_task(world, args.attempt)
    value = read_json(args.file)
    project_id = world.run(attempt["run_id"])["project_id"]
    inputs = {path: Path(path).read_bytes() for path in value["inputs"]}
    environment = world.environment(value["environment_id"])
    return ExperimentRunner(world, runner_controller()).run(project_id, args.attempt, environment, value["command"], inputs, value.get("seed", 0))


def review_command(args, world: World):
    value = read_json(args.file)
    if value["decision"] == "terminate":
        return world.update_run(args.run, "terminated")
    if value["decision"] == "approve":
        return runtime_orchestrator(world).approve_conflict(args.run, value.get("feedback", "human approval"))
    return runtime_orchestrator(world).resolve_conflict(args.run, value["feedback"])


def execute_run(world: World, run: dict) -> dict:
    return runtime_orchestrator(world).execute(run["id"])


def runtime_orchestrator(world: World) -> Orchestrator:
    settings = load_settings()
    if not settings.model_api_base or not settings.model_api_key:
        raise RuntimeError("MODEL_API_BASE and MODEL_API_KEY are required")
    agents = HarnessAgents(settings.model_api_base, settings.model_api_key)
    broker = SearchBroker(ToolBroker(world, McpClient()))
    return Orchestrator(world, agents, broker, settings.artifacts.parent / "workspaces")


def wait_or_execute(world: World, run: dict) -> dict:
    claimed = world.claim_run(run["id"])
    if claimed:
        try:
            return execute_run(world, claimed)
        except Exception:
            world.update_run(run["id"], "failed")
            world.record_event(run["id"], None, None, "control", "run_failed", {"type": "run", "id": run["id"]}, {})
            raise
    for _ in range(1800):
        current = world.run(run["id"])
        if current["status"] in {"completed", "failed", "human_conflict", "terminated"}:
            return current
        time.sleep(1)
    raise TimeoutError("run did not finish within 30 minutes")


def run_detail(world: World, run_id: str) -> dict:
    return {**world.run(run_id), "generations": world.generations(run_id),
            "attempts": world.attempts(run_id), "events": world.events(run_id)}


def watch_run(world: World, run_id: str, output: TextIO) -> int:
    cursor = 0
    while True:
        for event in world.events(run_id, cursor):
            cursor = event["event_id"]
            print(json.dumps({"schema_version": "1", "ok": True, "data": event}), file=output, flush=True)
        if world.run(run_id)["status"] in {"completed", "failed", "human_conflict", "terminated"}:
            return 0
        time.sleep(1)


def apply_project(world: World, project: dict, run_id: str) -> dict:
    run = world.run(run_id)
    if run["project_id"] != project["id"] or run["status"] != "completed" or not run["apply_selected"]:
        raise PermissionError("run has no approved apply authorization")
    return {"project_id": project["id"], "run_id": run_id, "files": []}


def require_task(world: World, attempt_id: str) -> dict:
    token = os.getenv("RW_TASK_TOKEN", "")
    attempt = world.authorize_task(token, attempt_id)
    if not attempt:
        raise PermissionError("invalid task capability")
    return attempt


def task_path(path: Path) -> Path:
    if path.is_absolute() or ".." in path.parts:
        raise PermissionError("task paths must stay inside the attempt workspace")
    return path


def doctor(args) -> dict:
    settings = load_settings()
    selected = [name for name in ("model", "embedding", "mcp", "runner") if getattr(args, name)]
    return {name: doctor_check(name, settings) for name in selected}


def doctor_check(name: str, settings) -> dict:
    if name == "model":
        body = {"model": "qwen3.7-flash", "messages": [{"role": "user", "content": "Reply OK"}], "max_tokens": 8}
        response = httpx.post(settings.model_api_base.rstrip("/") + "/chat/completions", headers=model_headers(settings), json=body, timeout=60)
        response.raise_for_status()
        return {"model": response.json()["model"], "ok": True}
    if name == "embedding":
        return {"dimensions": len(EmbeddingClient(settings.model_api_base, settings.model_api_key)("orbit")), "ok": True}
    if name == "mcp":
        tools = McpClient().list_tools({"type": "http", "url": "https://api.anysearch.com/mcp"})
        return {"tools": [tool["name"] for tool in tools], "ok": True}
    response = httpx.post(os.getenv("RUNNER_CONTROLLER_URL", "http://127.0.0.1:8096") + "/doctor", timeout=60)
    response.raise_for_status()
    return response.json()


def model_headers(settings) -> dict:
    if not settings.model_api_base or not settings.model_api_key:
        raise RuntimeError("MODEL_API_BASE and MODEL_API_KEY are required")
    return {"Authorization": f"Bearer {settings.model_api_key}"}


def runner_controller() -> HttpRunnerController:
    return HttpRunnerController(os.getenv("RUNNER_CONTROLLER_URL", "http://127.0.0.1:8096"))


def read_json(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path else json.load(sys.stdin)


def project_root(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else load_settings().projects_root / path


def serve(args):
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
    return {"stopped": True}


def default_world() -> World:
    settings = load_settings()
    embedding = EmbeddingClient(settings.model_api_base, settings.model_api_key) if settings.model_api_base and settings.model_api_key else None
    return World(settings.database, settings.artifacts, embedding)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
