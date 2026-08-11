from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from . import db, repository as repo
from .commands import complete_task, dispatch
from .models import (Command, MaintenanceClaim, MaintenanceCompletion, RuntimeHeartbeat,
                     RuntimeRegistration, TaskClaim, TaskCompletion, TaskEvent,
                     TaskFailure, TaskHeartbeat)


ROOT = Path(__file__).resolve().parents[1]
ACTOR = {"kind": "system", "id": "bootstrap"}
STALE_ATTEMPT_CODE = "stale_task_attempt"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.initialize()
    seed_project()
    task = asyncio.create_task(reaper_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Research World", lifespan=lifespan)


@app.exception_handler(repo.StateConflict)
async def state_conflict(_: Request, error: repo.StateConflict) -> JSONResponse:
    detail = str(error)
    body = {"detail": detail}
    if detail == "stale task attempt":
        body["code"] = STALE_ATTEMPT_CODE
    return JSONResponse(body, status_code=409)


async def reaper_loop() -> None:
    while True:
        repo.sweep_stale()
        await asyncio.sleep(5)


def seed_project() -> None:
    if not repo.projects():
        repo.create_project("Computer processing limits", "Is there an upper limit to computer processing speed?", ACTOR)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/bootstrap")
def bootstrap(project_id: str | None = None) -> dict:
    selected = selected_project(project_id)
    return {"projects": repo.projects(), "active_project_id": selected,
            "nodes": repo.project_nodes(selected), "review_nodes": repo.review_nodes(selected),
            "edges": repo.project_edges(selected),
            "events": repo.events(selected), "jobs": repo.project_jobs(selected),
            "agents": repo.agents(), "runtimes": repo.runtimes(),
            "artifacts": repo.project_artifacts(selected)}


@app.get("/api/nodes/{node_id}")
def node_detail(node_id: str) -> dict:
    value = repo.node(node_id)
    if not value:
        raise HTTPException(404, "unknown node")
    return value


@app.get("/api/artifacts/{artifact_id}/metadata")
def artifact_metadata(artifact_id: str) -> dict:
    value = repo.artifact(artifact_id)
    if not value:
        raise HTTPException(404, "unknown artifact")
    return value


def selected_project(project_id: str | None) -> str:
    projects = repo.projects()
    if project_id:
        if any(value["id"] == project_id for value in projects):
            return project_id
        raise HTTPException(404, "unknown project")
    if not projects:
        raise HTTPException(404, "no projects")
    return projects[0]["id"]


@app.post("/api/commands")
def command(value: Command) -> dict:
    return {"result": dispatch(value)}


@app.post("/api/runtimes/register")
def register_runtime(value: RuntimeRegistration) -> dict:
    return repo.register_runtime(value.model_dump())


@app.post("/api/runtimes/{runtime_id}/heartbeat")
def runtime_heartbeat(runtime_id: str, value: RuntimeHeartbeat) -> dict:
    if value.status not in {"online", "offline"}:
        raise HTTPException(400, "runtime status must be online or offline")
    return repo.heartbeat(runtime_id, value.status)


@app.post("/api/tasks/claim")
def claim(value: TaskClaim):
    task = repo.claim_job(value.runtime_id)
    if not task:
        return Response(status_code=204)
    return {"task": task}


@app.post("/api/tasks/{job_id}/heartbeat")
def task_heartbeat(job_id: str, value: TaskHeartbeat) -> dict:
    return repo.renew_lease(job_id, value.runtime_id, value.attempt_id)


@app.post("/api/tasks/{job_id}/events")
def task_event(job_id: str, value: TaskEvent) -> dict:
    repo.record_task_event(job_id, value.model_dump())
    return {"accepted": True}


@app.post("/api/tasks/{job_id}/complete")
def task_complete(job_id: str, value: TaskCompletion) -> dict:
    return complete_task(job_id, value)


@app.post("/api/tasks/{job_id}/fail")
def task_fail(job_id: str, value: TaskFailure) -> dict:
    return repo.fail_job(job_id, value.runtime_id, value.attempt_id, value.error)


@app.post("/api/maintenance/claim")
def maintenance_claim(value: MaintenanceClaim):
    command = repo.claim_workspace_command(value.runtime_id)
    return {"command": command} if command else Response(status_code=204)


@app.post("/api/maintenance/{command_id}/complete")
def maintenance_complete(command_id: str, value: MaintenanceCompletion) -> dict:
    return repo.complete_workspace_command(command_id, value.runtime_id)


@app.get("/api/events/stream")
async def event_stream(project_id: str, after: int = Query(0, ge=0)) -> StreamingResponse:
    return StreamingResponse(stream_events(project_id, after), media_type="text/event-stream")


async def stream_events(project_id: str, after: int):
    cursor = after
    while True:
        values = repo.events(project_id, cursor)
        for value in values:
            cursor = value["seq"]
            yield f"data: {json.dumps(value, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.7)


@app.get("/api/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str) -> HTMLResponse:
    value = repo.artifact(artifact_id)
    if not value:
        raise HTTPException(404, "unknown artifact")
    content = Path(value["path"]).read_text(encoding="utf-8")
    return HTMLResponse(content, headers=artifact_headers())


def artifact_headers() -> dict[str, str]:
    policy = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:;"
    return {"Content-Security-Policy": policy, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    dist = ROOT / "web" / "dist"
    asset = dist / path
    if path and asset.is_file():
        return FileResponse(asset)
    if (dist / "index.html").is_file():
        return FileResponse(dist / "index.html")
    raise HTTPException(404, "frontend not built; run npm run dev")
