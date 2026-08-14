from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from .config import ROOT, load_settings
from .world import InvalidPackage, World


def create_app(world: World) -> FastAPI:
    app = FastAPI(title="Research World", version="1")
    project_read_routes(app, world)
    project_write_routes(app, world)
    run_routes(app, world)
    run_view_routes(app, world)
    graph_routes(app, world)
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
        return world.create_project(value["name"], Path(value["root"]), value["question"])

    @app.post("/api/v1/projects/{name}/snapshots")
    def sync_project(name: str):
        return world.sync_project(world.project_by_name(name)["id"])


def run_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/runs")
    def runs():
        return world.runs()

    @app.get("/api/v1/runs/{run_id}")
    def run(run_id: str):
        return {**world.run(run_id), "events": world.events(run_id)}

    @app.get("/api/v1/runs/{run_id}/generations/{generation_id}")
    def generation(run_id: str, generation_id: str):
        value = next(item for item in world.generations(run_id) if item["id"] == generation_id)
        value["attempts"] = [item for item in world.attempts(run_id) if item["generation_id"] == generation_id]
        return value


def run_view_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/runs/{run_id}/wire")
    def wire(run_id: str):
        return attempt_artifacts(world, run_id, "wire_artifact_id")

    @app.get("/api/v1/runs/{run_id}/context")
    def context(run_id: str):
        return attempt_artifacts(world, run_id, "context_artifact_id")

    @app.get("/api/v1/runs/{run_id}/agents-jobs")
    def agents_jobs(run_id: str):
        return world.attempts(run_id)

    @app.get("/api/v1/runs/{run_id}/events")
    def events(run_id: str, follow: bool = Query(False), last_event_id: str | None = Header(None)):
        after = int(last_event_id or 0)
        return StreamingResponse(event_stream(world, run_id, after, follow), media_type="text/event-stream")


def graph_routes(app: FastAPI, world: World) -> None:
    @app.get("/api/v1/artifacts/{artifact_id}")
    def artifact(artifact_id: str):
        return admitted_artifact(world, artifact_id)

    @app.get("/api/v1/nodes/{node_id}")
    def node(node_id: str):
        return public_node(world.admitted_node(node_id))

    @app.get("/api/v1/artifacts/{artifact_id}/content")
    def artifact_content(artifact_id: str):
        value = admitted_artifact(world, artifact_id)
        return Response(world.artifacts.read(artifact_id), media_type=value["media_type"])


def frontend_routes(app: FastAPI) -> None:
    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        return frontend_file(path)


async def event_stream(world: World, run_id: str, after: int, follow: bool):
    cursor = after
    while True:
        values = world.events(run_id, cursor)
        for event in values:
            cursor = event["event_id"]
            yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
        if not follow:
            return
        yield ": keepalive\n\n"
        await asyncio.sleep(1)


def bootstrap_data(world: World, projects: list[dict], selected: str | None) -> dict:
    if not selected:
        return {"projects": [], "active_project_id": None, "nodes": [], "edges": [], "events": [], "jobs": [], "agents": [], "runtimes": [], "artifacts": []}
    runs = [run for run in world.runs() if run["project_id"] == selected]
    nodes = [public_node(node) for node in world.admitted_nodes(selected)]
    return {"projects": [{**item, "title": item["name"]} for item in projects], "active_project_id": selected,
            "nodes": nodes, "review_nodes": nodes,
            "edges": world.project_edges(selected), "events": [event for run in runs for event in world.events(run["id"])],
            "jobs": [attempt for run in runs for attempt in world.attempts(run["id"])], "agents": [], "runtimes": [],
            "artifacts": public_artifacts(world.project_artifacts(selected), nodes), "runs": runs}


def public_node(node: dict) -> dict:
    payload = node.get("payload") or {}
    actor = node.get("generation_id")
    return {key: value for key, value in node.items() if key != "payload"} | {
        "title": node_text(payload, 96), "summary": node_text(payload, 280),
        "content": {"record": payload},
        "created_by": {"kind": "agent" if actor else "system", "id": actor or "system"},
        "audit": "approve" if node.get("status") == "admitted" else "pending",
    }


def node_text(payload: dict, limit: int) -> str:
    value = next((payload[key] for key in ("title", "text", "strategy", "role")
                  if isinstance(payload.get(key), str) and payload[key].strip()), "Untitled node")
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


def public_artifacts(artifacts: list[dict], nodes: list[dict]) -> list[dict]:
    owners = {node["content"]["record"].get("artifact_id"): node for node in nodes}
    return [public_artifact(artifact, owners.get(artifact["id"])) for artifact in artifacts]


def public_artifact(artifact: dict, owner: dict | None) -> dict:
    return {**artifact, "node_id": owner["id"] if owner else None,
            "title": owner["title"] if owner else artifact["id"],
            "kind": owner["kind"] if owner else "artifact", "content_type": artifact["media_type"]}


def attempt_artifacts(world: World, run_id: str, field: str) -> list[dict]:
    values = []
    for attempt in world.attempts(run_id):
        if attempt[field]:
            content = json.loads(world.artifacts.read(attempt[field]))
            values.append({"attempt_id": attempt["id"], "actor": attempt["actor"], "generation_id": attempt["generation_id"], "content": content})
    return values


def frontend_file(path: str):
    dist = ROOT / "web" / "dist"
    asset = dist / path
    if path and asset.is_file():
        return FileResponse(asset)
    if (dist / "index.html").is_file():
        return FileResponse(dist / "index.html")
    raise HTTPException(404, "frontend not built")


def admitted_artifact(world: World, artifact_id: str) -> dict:
    try:
        return world.public_artifact(artifact_id)
    except PermissionError as error:
        raise HTTPException(404, "artifact not found") from error


settings = load_settings()
app = create_app(World(settings.database, settings.artifacts))
