from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .config import ROOT, load_settings
from .orchestrator import WorkflowManager
from .world import World


def create_app(world: World) -> FastAPI:
    app = FastAPI(title="Research World", version="2")
    project_routes(app, world)
    graph_routes(app, world)
    conversation_routes(app, world)
    frontend_routes(app)
    return app


def project_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/health")
    async def health():
        return {"ok": True}

    @app.get("/api/v1/projects")
    async def projects():
        return project_cards(world)

    @app.post("/api/v1/projects", status_code=201)
    async def create_project(request: Request):
        value = await request.json()
        return world.create_project(value["name"], Path(value["root"]), value["question"])

    @app.get("/api/v1/bootstrap")
    async def bootstrap(project_id: str | None = None):
        return bootstrap_data(world, project_id)

    @app.patch("/api/v1/projects/{project_id}")
    async def update_project(project_id: str, request: Request):
        value = await request.json()
        return world.set_auto(project_id, bool(value["auto"]))


def graph_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/nodes/{node_id}")
    async def node(node_id: str):
        return get_or_404(world.node, node_id)

    @app.post("/api/v1/projects/{project_id}/nodes", status_code=201)
    async def create_node(project_id: str, request: Request):
        value = await request.json()
        state = {key: value[key] for key in NODE_STATE_KEYS if key in value}
        return world.create_node(project_id, value["kind"], value["payload"], **state)

    @app.patch("/api/v1/nodes/{node_id}")
    async def update_node(node_id: str, request: Request):
        value = await request.json()
        state = {key: value[key] for key in UPDATE_KEYS if key in value}
        return world.update_node(node_id, value.get("payload"), **state)

    @app.post("/api/v1/projects/{project_id}/edges", status_code=201)
    async def create_edge(project_id: str, request: Request):
        value = await request.json()
        ensure_project_node(world, project_id, value["source"])
        return world.add_edge(value["source"], value["target"], value["polarity"])


def conversation_routes(app: FastAPI, world: World) -> None:
    manager = WorkflowManager(world)

    @app.get("/api/v1/projects/{project_id}/messages")
    async def messages(project_id: str, node_id: str):
        return world.messages(project_id, node_id)

    @app.post("/api/v1/projects/{project_id}/messages", status_code=201)
    async def send_message(project_id: str, request: Request):
        value = await request.json()
        return manager.assist(project_id, value["node_id"], value["message"])

    @app.post("/api/v1/projects/{project_id}/drafts/materialize", status_code=201)
    async def materialize(project_id: str, request: Request):
        value = await request.json()
        return manager.materialize(project_id, value["node_id"], value["kind"], value["payload"])


NODE_STATE_KEYS = {"parent_id", "lineage_id", "life_state", "direction_status", "working"}
UPDATE_KEYS = {"life_state", "direction_status", "working", "rejection_reason", "rebuttal"}


def bootstrap_data(world: World, project_id: str | None) -> dict:
    projects = project_cards(world)
    selected = project_id or (projects[0]["id"] if projects else None)
    if not selected:
        return {"projects": [], "active_project_id": None, "nodes": [], "edges": []}
    get_or_404(world.project, selected)
    return {"projects": projects, "active_project_id": selected,
            "nodes": world.nodes(selected), "edges": world.edges(selected)}


def project_cards(world: World) -> list[dict]:
    cards = []
    for project in world.projects():
        nodes = world.nodes(project["id"])
        cards.append({**project, "title": project["name"], "node_count": len(nodes)})
    return cards


def ensure_project_node(world: World, project_id: str, node_id: str) -> None:
    if get_or_404(world.node, node_id)["project_id"] != project_id:
        raise HTTPException(400, "node belongs to another project")


def get_or_404(getter, value: str):
    try:
        return getter(value)
    except KeyError as error:
        raise HTTPException(404, "not found") from error


def frontend_routes(app: FastAPI) -> None:
    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        dist = ROOT / "web" / "dist"
        asset = dist / path
        if path and asset.is_file():
            return FileResponse(asset)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        raise HTTPException(404, "frontend not built")


settings = load_settings()
app = create_app(World(settings.database, settings.artifacts))
