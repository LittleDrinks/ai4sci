import io
import json

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
