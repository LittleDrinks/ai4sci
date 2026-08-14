import io
import json

from fastapi.testclient import TestClient

from server.app import create_app
from server.cli import main
from server.research import ResearchState


def test_project_snapshot_is_immutable(world, project):
    root = world.project(project["id"])["root"]
    first = world.sync_project(project["id"])
    (world.path(root) / "README.md").write_text("changed", encoding="utf-8")
    second = world.sync_project(project["id"])
    assert first["id"] != second["id"]


def test_project_api_creates_a_tool_profile(world, tmp_path, monkeypatch):
    monkeypatch.setenv("RW_PROJECTS_ROOT", str(tmp_path))
    with TestClient(create_app(world)) as client:
        response = client.post("/api/v1/projects", json={"name": "Orbit Lab", "question": "Why are orbits stable?"})
    assert response.status_code == 200
    root = tmp_path / "orbit-lab"
    assert json.loads((root / ".mcp.json").read_text())["researchTools"]["search"] == "search"


def test_cli_create_uses_versioned_envelope(world, tmp_path, monkeypatch):
    monkeypatch.setenv("RW_PROJECTS_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"name": "CLI Lab", "question": "Question?"})))
    output = io.StringIO()
    assert main(["project", "create"], world=world, output=output) == 0
    body = json.loads(output.getvalue())
    assert body["schema_version"] == "1" and body["ok"] is True
    assert (tmp_path / "cli-lab" / ".mcp.json").is_file()


def test_attempt_log_is_readable(world, project):
    state = ResearchState(world)
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0, run_id=run["id"])
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "reviewer")
    state.add_attempt_log(attempt["id"], b'{"type":"assistant","content":"checked"}\n')
    with TestClient(create_app(world)) as client:
        response = client.get(f"/api/v1/attempts/{attempt['id']}/log")
    assert response.status_code == 200 and "checked" in response.text


def test_restart_marks_active_research_interrupted(world, project):
    state = ResearchState(world)
    direction = state.propose_directions(project["id"], [{"title": "A", "workflow": "simulation"}])[0]
    state.admit_direction(direction["id"])
    cycle = state.start_cycle(direction["id"])
    work = state.create_work_item(cycle["id"], "experiment", {})
    state.start_step(work["steps"][0]["id"])
    create_app(world)
    assert state.cycle(cycle["id"])["status"] == "blocked"
    assert state.work_item(work["id"])["status"] == "interrupted"
    assert state.step(work["steps"][0]["id"])["status"] == "interrupted"


def test_bootstrap_only_exposes_research_control_plane(world, project):
    with TestClient(create_app(world)) as client:
        body = client.get(f"/api/v1/bootstrap?project_id={project['id']}").json()
    assert body["active_project_id"] == project["id"]
    assert {"cycles", "work_items", "attempts", "messages"} <= set(body)
    assert not ({"runs", "jobs", "runtimes"} & set(body))
