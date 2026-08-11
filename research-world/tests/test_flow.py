import pytest
from fastapi.testclient import TestClient

from server import db
from server.app import app


ACTOR = {"kind": "human", "id": "tester"}


def command(client, kind, payload, actor=ACTOR):
    response = client.post("/api/commands", json={"type": kind, "actor": actor, "payload": payload})
    assert response.status_code == 200, response.text
    return response.json()["result"]


def test_agent_queue_result_and_report(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        project_id, root_id = state["active_project_id"], state["nodes"][0]["id"]
        runtime = client.post("/api/runtimes/register", json=runtime_payload()).json()
        agent = command(client, "create_agent", agent_payload(runtime["id"]))
        job = command(client, "enqueue_job", job_payload(project_id, root_id, agent["id"]))
        task = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        complete = client.post(f"/api/tasks/{job['id']}/complete", json=completion(task, root_id))
        assert complete.status_code == 200, complete.text
        assert complete.json()["node"]["audit"] == "pending"
        assert complete.json()["artifact"]["status"] == "pending_review"
        assert complete.json()["artifact"]["title"] == "Initial report"
        assert complete.json()["job"]["status"] == "awaiting_review"


def test_same_submission_has_same_uid(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        payload = node_payload(state["active_project_id"], state["nodes"][0]["id"])
        first = command(client, "submit_node", payload)
        second = command(client, "submit_node", payload, {"kind": "agent", "id": "agent-2"})
        assert first["id"] == second["id"]
        assert len(client.get("/api/bootstrap").json()["nodes"]) == 2


def test_pending_subject_cannot_be_queued(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state, runtime, agent = setup_agent(client)
        pending = command(client, "submit_node", node_payload(state["active_project_id"], state["nodes"][0]["id"]))
        payload = job_payload(state["active_project_id"], pending["id"], agent["id"])
        response = client.post("/api/commands", json={"type": "enqueue_job", "actor": ACTOR, "payload": payload})
        assert response.status_code == 409


def test_submit_node_rejects_question_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        payload = node_payload(state["active_project_id"], state["nodes"][0]["id"])
        response = client.post("/api/commands", json={
            "type": "submit_node", "actor": ACTOR, "payload": {**payload, "kind": "question"},
        })
        assert response.status_code == 400
        assert response.json()["detail"] == "question nodes are created with projects"
        assert len(client.get("/api/bootstrap").json()["nodes"]) == 1


def test_public_enqueue_rejects_audit_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        runtime = client.post("/api/runtimes/register", json={
            **runtime_payload(), "capabilities": ["audit"],
        }).json()
        agent = command(client, "create_agent", {
            **agent_payload(runtime["id"]), "capabilities": ["audit"],
        })
        payload = {**job_payload(state["active_project_id"], state["nodes"][0]["id"], agent["id"]),
                   "kind": "audit"}
        response = client.post("/api/commands", json={"type": "enqueue_job", "actor": ACTOR, "payload": payload})
        assert response.status_code == 400
        assert client.get("/api/bootstrap").json()["jobs"] == []


@pytest.mark.parametrize("html", [None, "", " \n"])
def test_html_report_requires_non_empty_html(tmp_path, monkeypatch, html):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state, runtime, agent = setup_agent(client)
        job = command(client, "enqueue_job", job_payload(
            state["active_project_id"], state["nodes"][0]["id"], agent["id"]))
        task = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        body = {**completion(task, state["nodes"][0]["id"]), "html": html}
        assert client.post(f"/api/tasks/{job['id']}/complete", json=body).status_code == 400
        snapshot = client.get("/api/bootstrap").json()
        assert snapshot["jobs"][0]["status"] == "running"
        assert len(snapshot["nodes"]) == 1 and snapshot["artifacts"] == []


def test_dependency_cannot_cross_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        project = command(client, "create_project", {"title": "Second", "question": "Another question?"})
        payload = node_payload(project["id"], state["nodes"][0]["id"])
        response = client.post("/api/commands", json={"type": "submit_node", "actor": ACTOR, "payload": payload})
        assert response.status_code == 409


def test_unknown_project_does_not_select_default(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        response = client.get("/api/bootstrap", params={"project_id": "project:missing"})
        assert response.status_code == 404


def test_runtime_offline_is_visible(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        runtime = client.post("/api/runtimes/register", json=runtime_payload()).json()
        response = client.post(f"/api/runtimes/{runtime['id']}/heartbeat", json={"status": "offline"})
        assert response.json()["status"] == "offline"
        state = client.get("/api/bootstrap").json()
        assert state["runtimes"][0]["status"] == "offline"
        assert state["events"][-1]["type"] == "runtime_status_changed"


def test_artifact_review_happens_once(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state, runtime, agent = setup_agent(client)
        artifact = complete_report(client, state["active_project_id"], state["nodes"][0]["id"], runtime["id"], agent["id"])
        command(client, "review_node", {"node_id": artifact["node_id"], "decision": "approve"})
        command(client, "review_artifact", {"artifact_id": artifact["id"], "decision": "approve"})
        payload = {"type": "review_artifact", "actor": ACTOR, "payload": {"artifact_id": artifact["id"], "decision": "reject", "feedback": "stale review"}}
        response = client.post("/api/commands", json=payload)
        assert response.status_code == 409
        assert "code" not in response.json()


def test_identical_reports_keep_project_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "research.db")
    with TestClient(app) as client:
        state, runtime, agent = setup_agent(client)
        first = complete_report(client, state["active_project_id"], state["nodes"][0]["id"], runtime["id"], agent["id"])
        project = command(client, "create_project", {"title": "Second", "question": "Another question?"})
        second = complete_report(client, project["id"], project["root_id"], runtime["id"], agent["id"])
        assert first["id"] != second["id"]
        assert second["project_id"] == project["id"]
        assert client.get(f"/api/nodes/{project['root_id']}").json()["project_id"] == project["id"]
        assert client.get(f"/api/artifacts/{second['id']}/metadata").json()["project_id"] == project["id"]


def setup_agent(client):
    state = client.get("/api/bootstrap").json()
    runtime = client.post("/api/runtimes/register", json=runtime_payload()).json()
    agent = command(client, "create_agent", agent_payload(runtime["id"]))
    return state, runtime, agent


def complete_report(client, project_id, root_id, runtime_id, agent_id):
    job = command(client, "enqueue_job", job_payload(project_id, root_id, agent_id))
    task = client.post("/api/tasks/claim", json={"runtime_id": runtime_id}).json()["task"]
    response = client.post(f"/api/tasks/{job['id']}/complete", json=completion(task, root_id))
    assert response.status_code == 200, response.text
    return response.json()["artifact"]


def runtime_payload():
    return {"name": "test-runtime", "sdk": "ResearchHarness", "version": "test", "capabilities": ["research", "html_report"]}


def agent_payload(runtime_id):
    return {"name": "Researcher", "runtime_id": runtime_id, "model": "test-model", "instructions": "Research carefully", "capabilities": ["research", "html_report"]}


def job_payload(project_id, root_id, agent_id):
    return {"project_id": project_id, "agent_id": agent_id, "kind": "html_report", "subject_id": root_id, "prompt": "Summarize the question"}


def completion(task, root_id):
    submission = {"kind": "report", "title": "Initial report", "summary": "Pending review", "content": {"sources": []}, "dependencies": [root_id]}
    return {"runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"], "result_text": "done", "submission": submission, "html": "<main><h1>Initial report</h1></main>"}


def node_payload(project_id, root_id):
    return {"project_id": project_id, "kind": "claim", "title": "A candidate", "summary": "Testable", "content": {}, "dependencies": [root_id]}
