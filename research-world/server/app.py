from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse

from .config import ROOT, load_settings
from .world import World
from .research import ResearchState
from .project_profile import initialize_project, project_slug


def create_app(world: World, loop_factory=None) -> FastAPI:
    ResearchState(world).recover_interrupted()
    app = FastAPI(title="Research World", version="1")
    project_read_routes(app, world)
    project_write_routes(app, world)
    audit_routes(app, world)
    research_routes(app, world, loop_factory)
    frontend_routes(app)
    return app


def project_read_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/health")
    def health():
        return {"ok": True}

    @app.get("/api/v1/projects")
    def projects():
        return world.projects()

    @app.get("/api/v1/bootstrap")
    def bootstrap(project_id: str | None = None):
        projects = world.projects()
        selected = project_id or (projects[0]["id"] if projects else None)
        return bootstrap_data(world, projects, selected)


def project_write_routes(app: FastAPI, world: World) -> None:
    @app.post("/api/v1/projects")
    async def create_project(request: Request):
        value = await request.json()
        settings = load_settings()
        root = settings.projects_root / project_slug(value["name"])
        initialize_project(root)
        return world.create_project(value["name"], root, value["question"])

    @app.post("/api/v1/projects/{name}/snapshots")
    def sync_project(name: str):
        return world.sync_project(world.project_by_name(name)["id"])


def audit_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/attempts/{attempt_id}/log")
    def attempt_log(attempt_id: str):
        rows = world._rows("SELECT artifact_id FROM attempt_logs WHERE attempt_id=?", (attempt_id,))
        if not rows:
            raise HTTPException(404, "attempt log not found")
        return Response(world.artifacts.read(rows[0]["artifact_id"]), media_type="text/plain")


def research_routes(app: FastAPI, world: World, loop_factory) -> None:
    state = ResearchState(world)

    @app.post("/api/v1/projects/{project_id}/plan")
    def plan_project(project_id: str):
        return require_loop(loop_factory, world).plan_project(project_id)

    @app.post("/api/v1/directions/{direction_id}/admit-run")
    def run_direction(direction_id: str, tasks: BackgroundTasks):
        tasks.add_task(run_direction_task, loop_factory, world, direction_id)
        return {"direction_id": direction_id, "status": "queued"}

    @app.post("/api/v1/projects/{project_id}/messages")
    async def add_message(project_id: str, request: Request, tasks: BackgroundTasks):
        value = await request.json()
        tasks.add_task(handle_message_task, loop_factory, world, project_id, value["content"], value.get("node_id"))
        return {"project_id": project_id, "status": "queued"}


def require_loop(loop_factory, world: World):
    return loop_factory(world) if loop_factory else default_research_loop(world)


def run_direction_task(loop_factory, world: World, direction_id: str) -> None:
    try:
        require_loop(loop_factory, world).admit_and_run(direction_id)
    except Exception as error:
        direction = ResearchState(world).node(direction_id)
        ResearchState(world).add_message(direction["project_id"], "assistant", f"方向执行停止：{error}", direction_id)


def handle_message_task(loop_factory, world: World, project_id: str, content: str, node_id: str | None) -> None:
    try:
        require_loop(loop_factory, world).handle_message(project_id, content, node_id)
    except Exception as error:
        ResearchState(world).add_message(project_id, "assistant", f"Lead 无法处理这条指令：{error}", node_id)


def frontend_routes(app: FastAPI) -> None:
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        return frontend_file(path)


def bootstrap_data(world: World, projects: list[dict], selected: str | None) -> dict:
    if not selected:
        return {"projects": [], "active_project_id": None, "nodes": [], "edges": []}
    research = ResearchState(world).project_view(selected)
    nodes = world.project_nodes(selected)
    return {"projects": [{**item, "title": item["name"]} for item in projects], "active_project_id": selected,
            "nodes": nodes, "review_nodes": [node for node in nodes if node["status"] in {"proposed", "blocked"}],
            "edges": world.all_project_edges(selected), **research}


def frontend_file(path: str):
    dist = ROOT / "web" / "dist"
    asset = dist / path
    if path and asset.is_file():
        return FileResponse(asset)
    if (dist / "index.html").is_file():
        return FileResponse(dist / "index.html")
    raise HTTPException(404, "frontend not built")


settings = load_settings()
app = create_app(World(settings.database, settings.artifacts))


def default_research_loop(world: World):
    from .agent_runtime import ContainerAgents
    from .clients import McpClient, SearchBroker
    from .research_loop import ResearchLoop
    from .runner import HttpRunnerController
    from .tools import ToolBroker
    if not settings.model_api_base or not settings.model_api_key:
        raise RuntimeError("MODEL_API_BASE and MODEL_API_KEY are required")
    controller = HttpRunnerController(__import__("os").getenv("RUNNER_CONTROLLER_URL", "http://127.0.0.1:8096"))
    agents = ContainerAgents(controller, settings.model_api_base, settings.model_api_key)
    search = SearchBroker(ToolBroker(world, McpClient()))
    return ResearchLoop(world, agents, search, controller)
