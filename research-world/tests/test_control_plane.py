from fastapi.testclient import TestClient

from server import db, repository as repo
from server.app import app


ACTOR = {"kind": "human", "id": "reviewer"}


def command(client, kind, payload):
    response = client.post("/api/commands", json={"type": kind, "actor": ACTOR, "payload": payload})
    assert response.status_code == 200, response.text
    return response.json()["result"]


def client_state(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    return TestClient(app)


def setup_agent(client, capabilities=None):
    capabilities = capabilities or ["research", "html_report"]
    runtime = client.post("/api/runtimes/register", json={
        "name": "runtime", "sdk": "ResearchHarness", "version": "test", "capabilities": capabilities,
    }).json()
    agent = command(client, "create_agent", {
        "name": "worker", "runtime_id": runtime["id"], "model": "test",
        "instructions": "work carefully", "capabilities": capabilities,
    })
    return runtime, agent


def enqueue(client, state, agent, kind="research"):
    return command(client, "enqueue_job", {
        "project_id": state["active_project_id"], "agent_id": agent["id"], "kind": kind,
        "subject_id": state["nodes"][0]["id"], "prompt": "Investigate",
    })


def complete(client, task, root_id, title="Candidate", html=None):
    body = {"runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"], "result_text": "done",
            "submission": {"kind": "result", "title": title, "summary": "Evidence", "content": {},
                           "dependencies": [root_id]}, "html": html}
    return client.post(f"/api/tasks/{task['id']}/complete", json=body)


def test_pending_nodes_never_enter_worker_context(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        pending = command(client, "submit_node", {"project_id": state["active_project_id"],
            "kind": "claim", "title": "Unreviewed", "dependencies": [state["nodes"][0]["id"]]})
        runtime, agent = setup_agent(client)
        job = enqueue(client, state, agent)
        task = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        assert pending["id"] not in {node["id"] for node in task["context"]["nodes"]}
        assert len(task["context"]["nodes"]) == 1
        assert job["id"] == task["id"]


def test_review_revision_reuses_attempt_and_feedback(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        runtime, agent = setup_agent(client)
        task = claim(client, runtime["id"], enqueue(client, state, agent)["id"])
        output = complete(client, task, state["nodes"][0]["id"]).json()["node"]
        result = command(client, "review_node", {"node_id": output["id"], "decision": "revise",
                                                 "feedback": "Add a source"})
        assert result["job"]["revision"] == 1
        assert result["job"]["attempt_id"] == task["attempt_id"]
        revised = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        assert revised["attempt_id"] == task["attempt_id"]
        assert revised["job"]["review_feedback"] == "Add a source"
        assert revised["job"]["review_mode"] == "continue"


def test_restart_opens_new_attempt(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        runtime, agent = setup_agent(client)
        task = claim(client, runtime["id"], enqueue(client, state, agent)["id"])
        output = complete(client, task, state["nodes"][0]["id"]).json()["node"]
        command(client, "review_node", {"node_id": output["id"], "decision": "restart",
                                        "feedback": "Reframe from first principles"})
        restarted = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        assert restarted["attempt_id"] != task["attempt_id"]
        assert restarted["job"]["review_mode"] == "restart"


def test_expired_attempt_is_fenced_and_requeued(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        runtime, agent = setup_agent(client)
        first = claim(client, runtime["id"], enqueue(client, state, agent)["id"])
        db.execute("UPDATE jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (first["id"],))
        repo.sweep_stale()
        cleanup = db.row("SELECT * FROM workspace_commands WHERE job_id=?", (first["id"],))
        second = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
        stale = {"runtime_id": first["runtime_id"], "attempt_id": first["attempt_id"],
                 "kind": "log", "message": "late", "payload": {}}
        response = client.post(f"/api/tasks/{first['id']}/events", json=stale)
        assert response.status_code == 409
        assert response.json() == {"detail": "stale task attempt", "code": "stale_task_attempt"}
        assert second["attempt_id"] != first["attempt_id"]
        assert cleanup["action"] == "delete_attempt_workspace" and cleanup["attempt_id"] == first["attempt_id"]


def test_non_report_completion_rejects_html(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        runtime, agent = setup_agent(client)
        task = claim(client, runtime["id"], enqueue(client, state, agent)["id"])
        response = complete(client, task, state["nodes"][0]["id"], html="")
        assert response.status_code == 400
        job = next(value for value in client.get("/api/bootstrap").json()["jobs"] if value["id"] == task["id"])
        assert job["status"] == "running" and job["output_node_id"] is None


def test_invalidation_propagates_and_cancels_work(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        root = state["nodes"][0]["id"]
        first = admitted_node(client, state["active_project_id"], root, "Mechanism")
        second = admitted_node(client, state["active_project_id"], first["id"], "Consequence")
        runtime, agent = setup_agent(client)
        job = command(client, "enqueue_job", {"project_id": state["active_project_id"],
            "agent_id": agent["id"], "kind": "research", "subject_id": second["id"], "prompt": "Test"})
        client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]})
        result = command(client, "invalidate_node", {"node_id": first["id"], "reason": "Contradicted by replay"})
        snapshot = client.get("/api/bootstrap").json()
        assert set(result["affected_node_ids"]) == {first["id"], second["id"]}
        assert {node["id"] for node in snapshot["nodes"]} == {root}
        assert snapshot["edges"] == []
        assert next(value for value in snapshot["jobs"] if value["id"] == job["id"])["status"] == "cancelled"


def test_invalidation_cancels_job_using_affected_context(tmp_path, monkeypatch):
    with client_state(tmp_path, monkeypatch) as client:
        state = client.get("/api/bootstrap").json()
        root = state["nodes"][0]["id"]
        child = admitted_node(client, state["active_project_id"], root, "Report input")
        runtime, agent = setup_agent(client)
        job = enqueue(client, state, agent, "html_report")
        task = claim(client, runtime["id"], job["id"])
        assert child["id"] in {node["id"] for node in task["context"]["nodes"]}
        command(client, "invalidate_node", {"node_id": child["id"], "reason": "Retracted input"})
        cleanup = db.row("SELECT * FROM workspace_commands WHERE job_id=?", (job["id"],))
        assert repo.job(job["id"])["status"] == "cancelled"
        assert cleanup["action"] == "delete_job_workspace"


def claim(client, runtime_id, job_id):
    task = client.post("/api/tasks/claim", json={"runtime_id": runtime_id}).json()["task"]
    assert task["id"] == job_id
    return task


def admitted_node(client, project_id, dependency, title):
    node = command(client, "submit_node", {"project_id": project_id, "kind": "claim",
                                           "title": title, "dependencies": [dependency]})
    command(client, "review_node", {"node_id": node["id"], "decision": "approve"})
    return node
