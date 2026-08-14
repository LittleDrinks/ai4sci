from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TextIO

import httpx

from .clients import EmbeddingClient, McpClient, SearchBroker
from .config import load_settings
from .project_profile import initialize_project, project_slug
from .runner import HttpRunnerController
from .tools import ToolBroker
from .world import World


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rw")
    groups = root.add_subparsers(dest="group", required=True)
    _project_parser(groups)
    _demo_parser(groups)
    _doctor_parser(groups)
    serve = groups.add_parser("serve")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", default=8095, type=int)
    return root


def _project_parser(groups) -> None:
    project = groups.add_parser("project").add_subparsers(dest="action", required=True)
    create = project.add_parser("create")
    create.add_argument("--file", type=Path)
    for action in ("sync", "show"):
        project.add_parser(action).add_argument("--project", required=True)


def _demo_parser(groups) -> None:
    demo = groups.add_parser("demo")
    demo.add_argument("--run", action="store_true")
    demo.add_argument("--export", action="store_true")


def _doctor_parser(groups) -> None:
    doctor = groups.add_parser("doctor")
    for flag in ("model", "embedding", "mcp", "runner"):
        doctor.add_argument(f"--{flag}", action="store_true")


def main(argv: list[str] | None = None, world: World | None = None,
         output: TextIO | None = None, error: TextIO | None = None) -> int:
    args = parser().parse_args(argv)
    output, error = output or sys.stdout, error or sys.stderr
    try:
        data = dispatch(args, world or default_world())
        print(json.dumps({"schema_version": "1", "ok": True, "data": data}), file=output)
        return 0
    except Exception as exc:
        body = {"schema_version": "1", "ok": False, "error": {"code": "command_failed", "message": str(exc)}}
        print(json.dumps(body), file=error)
        return 2


def dispatch(args, world: World):
    if args.group == "project":
        return project_command(args, world)
    if args.group == "demo":
        return demo_command(world, args.run, args.export)
    if args.group == "doctor":
        return doctor(args)
    return serve(args)


def project_command(args, world: World):
    if args.action == "create":
        value = read_json(args.file)
        root = load_settings().projects_root / project_slug(value["name"])
        initialize_project(root)
        return world.create_project(value["name"], root, value["question"])
    project = world.project_by_name(args.project)
    return world.sync_project(project["id"]) if args.action == "sync" else project


def demo_command(world: World, execute: bool, export: bool = False) -> dict:
    from .demo import curated_directions, seed
    projects = seed(world)
    if export:
        return export_demo(world, projects)
    if not execute:
        return {"projects": projects}
    loop = runtime_research_loop(world)
    cycles = [_run_demo_project(loop, world, project, curated_directions) for project in projects]
    return {"projects": projects, "cycles": cycles}


def _run_demo_project(loop, world: World, project: dict, directions) -> dict:
    question_id = int(project["name"][1:4])
    planned = loop.plan_project(project["id"], directions(question_id))
    return loop.admit_and_run(choose_demo_direction(world, project, planned)["id"])


def choose_demo_direction(world: World, project: dict, directions: list[dict]) -> dict:
    question_id = int(project["name"][1:4])
    desired = {1: "proof_boundary", 2: "proof_boundary", 13: "forecast", 17: "wet_lab_proposal",
               49: "simulation", 55: "open_world_search", 88: "engineering_design",
               95: "conceptual_discrimination"}[question_id]
    return next(item for item in directions if item["payload"]["workflow"] == desired)


def export_demo(world: World, projects: list[dict]) -> dict:
    from .dossier import DossierExporter
    from .research import ResearchState
    state, exporter = ResearchState(world), DossierExporter(world)
    values = [_export_project(state, exporter, project) for project in projects]
    return {"exports": values}


def _export_project(state, exporter, project: dict) -> dict:
    cycle = next(item for item in reversed(state.cycles(project["id"])) if item["status"] == "completed")
    return {"project_id": project["id"], **exporter.export(project["id"], cycle["id"])}


def runtime_research_loop(world: World):
    from .agent_runtime import ContainerAgents
    from .research_loop import ResearchLoop
    settings = load_settings()
    require_model(settings)
    controller = runner_controller()
    agents = ContainerAgents(controller, settings.model_api_base, settings.model_api_key)
    search = SearchBroker(ToolBroker(world, McpClient()))
    return ResearchLoop(world, agents, search, controller)


def doctor(args) -> dict:
    settings = load_settings()
    names = [name for name in ("model", "embedding", "mcp", "runner") if getattr(args, name)]
    if not names:
        names = ["model", "mcp", "runner"]
    return {name: doctor_check(name, settings) for name in names}


def doctor_check(name: str, settings) -> dict:
    if name == "model":
        return doctor_model(settings)
    if name == "embedding":
        require_model(settings)
        return {"dimensions": len(EmbeddingClient(settings.model_api_base, settings.model_api_key)("orbit")), "ok": True}
    if name == "mcp":
        return doctor_mcp(settings)
    response = httpx.post(runner_controller().url + "/doctor", timeout=60)
    response.raise_for_status()
    return response.json()


def doctor_model(settings) -> dict:
    require_model(settings)
    body = {"model": "qwen3.7-flash", "messages": [{"role": "user", "content": "Reply OK"}], "max_tokens": 8}
    headers = {"Authorization": f"Bearer {settings.model_api_key}"}
    response = httpx.post(settings.model_api_base.rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=60)
    response.raise_for_status()
    return {"model": response.json()["model"], "ok": True}


def doctor_mcp(settings) -> dict:
    configs = sorted(settings.projects_root.glob("*/.mcp.json"))
    if not configs:
        raise FileNotFoundError("no project .mcp.json found")
    servers = json.loads(configs[0].read_text())["mcpServers"]
    tools = {name: [tool["name"] for tool in McpClient().list_tools(config)] for name, config in servers.items()}
    return {"servers": tools, "ok": True}


def require_model(settings) -> None:
    if not settings.model_api_base or not settings.model_api_key:
        raise RuntimeError("MODEL_API_BASE and MODEL_API_KEY are required")


def runner_controller() -> HttpRunnerController:
    return HttpRunnerController(os.getenv("RUNNER_CONTROLLER_URL", "http://127.0.0.1:8096"))


def read_json(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path else json.load(sys.stdin)


def serve(args):
    import uvicorn
    uvicorn.run("server.app:app", host=args.host, port=args.port)
    return {"stopped": True}


def default_world() -> World:
    settings = load_settings()
    return World(settings.database, settings.artifacts)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
