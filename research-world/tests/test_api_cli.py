import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.cli import SCHEMAS, main


def test_project_snapshot_is_immutable(world, project):
    root = world.project(project["id"])["root"]
    first = world.sync_project(project["id"])
    (world.path(root) / "README.md").write_text("changed", encoding="utf-8")
    second = world.sync_project(project["id"])
    assert first["id"] != second["id"]
    assert world.snapshot_manifest(first["id"])["files"][0]["sha256"] != world.snapshot_manifest(second["id"])["files"][0]["sha256"]


def test_task_token_is_scoped_to_its_attempt(world, project):
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0)
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "producer")
    other = world.create_attempt(run["id"], generation["id"], snapshot["id"], "reviewer")
    token = world.issue_task_token(attempt["id"])
    assert world.authorize_task(token, attempt["id"])["id"] == attempt["id"]
    assert world.authorize_task(token, other["id"]) is None


def test_sse_resumes_after_last_event_id(world, project):
    run = world.create_run(project["id"], 49, False)
    first = world.record_event(run["id"], None, None, "system", "run_started", {"type": "run", "id": run["id"]}, {})
    second = world.record_event(run["id"], None, None, "system", "generation_started", {"type": "generation", "id": "g0"}, {})
    with TestClient(create_app(world)) as client:
        response = client.get(f"/api/v1/runs/{run['id']}/events", headers={"Last-Event-ID": str(first["event_id"])})
    assert f"id: {second['event_id']}" in response.text
    assert "run_started" not in response.text


def test_run_detail_contains_event_history(world, project):
    run = world.create_run(project["id"], 49, False)
    world.record_event(run["id"], None, None, "system", "run_started", {"type": "run", "id": run["id"]}, {})
    with TestClient(create_app(world)) as client:
        response = client.get(f"/api/v1/runs/{run['id']}")
    assert response.json()["events"][0]["type"] == "run_started"


def test_api_does_not_publish_unadmitted_artifacts(world):
    artifact = world.add_artifact(b"pending", "text/plain")
    with TestClient(create_app(world), raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/artifacts/{artifact['id']}")
    assert response.status_code == 404


def test_cli_uses_versioned_envelope_and_reads_structured_stdin(world, tmp_path, monkeypatch):
    root = tmp_path / "cli-project"
    root.mkdir()
    payload = json.dumps({"name": "cli", "root": str(root), "question": "Question?"})
    output = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    assert main(["project", "create"], world=world, output=output) == 0
    body = json.loads(output.getvalue())
    assert body["schema_version"] == "1" and body["ok"] is True
    schema = io.StringIO()
    assert main(["schema", "project.create"], world=world, output=schema) == 0
    assert json.loads(schema.getvalue())["data"]["type"] == "object"


def test_task_cannot_read_an_unrelated_artifact(world, project, monkeypatch):
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0, run_id=run["id"])
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "producer")
    monkeypatch.setenv("RW_TASK_TOKEN", world.issue_task_token(attempt["id"]))
    monkeypatch.setenv("RW_TASK_WORKSPACE", str(world.path(project["root"])))
    artifact = world.add_artifact(b"private", "text/plain")
    error = io.StringIO()
    code = main(["artifact", "read", artifact["id"], "--attempt", attempt["id"]], world, error=error)
    assert code == 2
    assert "outside the task capability" in error.getvalue()


def test_task_event_does_not_grant_artifact_access(world, project, monkeypatch):
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0, run_id=run["id"])
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "producer")
    artifact = world.add_artifact(b"foreign pending", "text/plain")
    world.record_event(run["id"], generation["id"], attempt["id"], "agent", "artifact_added", {"type": "artifact", "id": artifact["id"]}, {})
    with pytest.raises(PermissionError, match="outside the task capability"):
        world.require_artifact_access(attempt["id"], artifact["id"])


def test_task_paths_are_anchored_to_workspace(tmp_path, monkeypatch):
    from server.cli import task_path
    workspace = tmp_path / "workspace"
    (workspace / "overlay").mkdir(parents=True)
    attempt = {"workspace": str(workspace)}
    assert task_path(attempt, Path("overlay/result.txt"), writable=True).is_relative_to(workspace)
    with pytest.raises(PermissionError, match="outside"):
        task_path(attempt, Path("../private"))


def test_watch_emits_one_json_envelope_per_event(world, project):
    run = world.create_run(project["id"], 49, False)
    world.record_event(run["id"], None, None, "system", "run_started", {"type": "run", "id": run["id"]}, {})
    world.update_run(run["id"], "completed")
    output = io.StringIO()
    assert main(["run", "watch", run["id"]], world, output=output) == 0
    lines = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(lines) == 1 and lines[0]["data"]["type"] == "run_started"


def test_every_public_command_has_a_schema():
    commands = {
        "project.create", "project.sync", "project.show", "project.apply",
        "run.start", "run.show", "run.watch", "review.resolve", "doctor",
        "task.show", "task.event", "graph.search", "graph.get",
        "artifact.inspect", "artifact.read", "artifact.materialize", "artifact.add",
        "tools.list", "tools.call", "source.acquire", "environment.build",
        "experiment.run", "submit.research-package",
    }
    assert set(SCHEMAS) == commands
