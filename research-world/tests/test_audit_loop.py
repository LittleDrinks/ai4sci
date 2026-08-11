import json

from fastapi.testclient import TestClient

from server import db
from server.app import app


ACTOR = {"kind": "human", "id": "operator"}


def command(client, kind, payload):
    response = client.post("/api/commands", json={"type": kind, "actor": ACTOR, "payload": payload})
    assert response.status_code == 200, response.text
    return response.json()["result"]


def register(client, name, runtime_id, capabilities):
    return command(client, "create_agent", {
        "name": name, "runtime_id": runtime_id, "model": "test", "instructions": name,
        "capabilities": capabilities,
    })


def register_runtime(client, name, capabilities):
    return client.post("/api/runtimes/register", json={
        "name": name, "sdk": "ResearchHarness", "version": "test", "capabilities": capabilities,
    }).json()


def offline_agents(client):
    runtime = register_runtime(client, "offline-cluster", ["research", "audit"])
    researcher = register(client, "offline-researcher", runtime["id"], ["research"])
    auditor = register(client, "offline-auditor", runtime["id"], ["audit"])
    client.post(f"/api/runtimes/{runtime['id']}/heartbeat", json={"status": "offline"})
    return researcher, auditor


def setup_cluster(client, with_auditor=True):
    state = client.get("/api/bootstrap").json()
    capabilities = ["research", "audit", "plan"] if with_auditor else ["research", "plan"]
    runtime = register_runtime(client, "cluster", capabilities)
    producer = register(client, "producer", runtime["id"], ["research", "plan"])
    auditor = register(client, "auditor", runtime["id"], ["audit"]) if with_auditor else None
    return state, runtime, producer, auditor


def enqueue_producer(client, state, producer, kind="research"):
    return command(client, "enqueue_job", {
        "project_id": state["active_project_id"], "agent_id": producer["id"], "kind": kind,
        "subject_id": state["nodes"][0]["id"], "prompt": "Propose one testable action",
    })


def claim(client, runtime_id):
    response = client.post("/api/tasks/claim", json={"runtime_id": runtime_id})
    assert response.status_code == 200, response.text
    return response.json()["task"]


def finish_producer(client, task, root_id, kind="result"):
    submission = {"kind": kind, "title": "Candidate", "summary": "Evidence", "content": {},
                  "dependencies": [root_id]}
    if kind == "action":
        submission["content"] = {"prompt": "Execute the admitted action"}
    body = {"runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"],
            "result_text": "done", "submission": submission}
    return client.post(f"/api/tasks/{task['id']}/complete", json=body)


def finish_audit(client, task, decision, feedback=""):
    body = {"runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"],
            "audit": {"decision": decision, "feedback": feedback, "checks": ["dependencies checked"]}}
    return client.post(f"/api/tasks/{task['id']}/complete", json=body)


def test_completion_queues_independent_audit_with_isolated_context(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, auditor = setup_cluster(client)
        producer_job = enqueue_producer(client, state, producer)
        producer_task = claim(client, runtime["id"])
        assert producer_task["id"] == producer_job["id"]
        completed = finish_producer(client, producer_task, state["nodes"][0]["id"]).json()
        audit_task = claim(client, runtime["id"])
        assert completed["audit_job"]["agent_id"] == auditor["id"] != producer["id"]
        assert audit_task["subject"]["id"] == completed["node"]["id"]
        assert {node["id"] for node in audit_task["context"]["nodes"]} == {state["nodes"][0]["id"]}
        assert audit_task["context"]["edges"] == [{"source": state["nodes"][0]["id"],
                                                     "target": completed["node"]["id"],
                                                     "relation": "depends_on"}]
        assert producer_task["id"] in audit_task["job"]["prompt"]
        assert "Producer revision: 0" in audit_task["job"]["prompt"]


def test_audit_revise_requeues_producer_without_recursive_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        producer_job = enqueue_producer(client, state, producer)
        output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"]).json()
        audit_task = claim(client, runtime["id"])
        reviewed = finish_audit(client, audit_task, "revise", "Add a source").json()
        jobs = client.get("/api/bootstrap").json()["jobs"]
        producer_after = next(job for job in jobs if job["id"] == producer_job["id"])
        assert reviewed["node"]["status"] == "revision_requested"
        assert producer_after["status"] == "queued" and producer_after["revision"] == 1
        assert producer_after["review_feedback"] == "Add a source"
        assert json.loads(reviewed["job"]["result_text"])["decision"] == "revise"
        assert len([job for job in jobs if job["kind"] == "audit"]) == 1


def test_audit_approve_action_triggers_exactly_one_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        enqueue_producer(client, state, producer, "plan")
        output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"], "action").json()
        audit_task = claim(client, runtime["id"])
        reviewed = finish_audit(client, audit_task, "approve").json()
        replay = finish_audit(client, audit_task, "approve")
        jobs = client.get("/api/bootstrap").json()["jobs"]
        executions = [job for job in jobs if job["kind"] == "research" and job["subject_id"] == output["node"]["id"]]
        assert reviewed["node"]["status"] == "admitted"
        assert replay.status_code == 409
        assert len(executions) == 1 and executions[0]["status"] == "queued"


def test_duplicate_admitted_output_does_not_queue_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        first = enqueue_producer(client, state, producer)
        first_output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"]).json()
        reviewed = finish_audit(client, claim(client, runtime["id"]), "approve").json()
        second = enqueue_producer(client, state, producer)
        duplicate = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"]).json()
        jobs = client.get("/api/bootstrap").json()["jobs"]
        assert reviewed["node"]["status"] == "admitted"
        assert duplicate["audit_job"] is None
        assert duplicate["job"]["status"] == "completed"
        assert {job["id"] for job in jobs if job["kind"] == "audit"} == {
            first_output["audit_job"]["id"]
        }
        assert first["id"] != second["id"]


def test_without_auditor_output_waits_for_human_review(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client, with_auditor=False)
        enqueue_producer(client, state, producer)
        completed = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"]).json()
        assert completed["audit_job"] is None
        assert completed["job"]["status"] == "awaiting_review"
        reviewed = command(client, "review_node", {"node_id": completed["node"]["id"], "decision": "approve"})
        assert reviewed["node"]["status"] == "admitted"


def test_producer_cannot_complete_its_own_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        enqueue_producer(client, state, producer)
        finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"])
        audit_task = claim(client, runtime["id"])
        db.execute("UPDATE jobs SET agent_id=? WHERE id=?", (producer["id"], audit_task["id"]))
        response = finish_audit(client, audit_task, "approve")
        assert response.status_code == 409
        assert client.get(f"/api/nodes/{audit_task['job']['subject_id']}").json()["audit"] == "pending"


def test_audit_completion_rejects_html_field(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        enqueue_producer(client, state, producer)
        finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"])
        audit_task = claim(client, runtime["id"])
        body = {"runtime_id": audit_task["runtime_id"], "attempt_id": audit_task["attempt_id"],
                "audit": {"decision": "approve", "feedback": "", "checks": []}, "html": ""}
        assert client.post(f"/api/tasks/{audit_task['id']}/complete", json=body).status_code == 400
        job = next(value for value in client.get("/api/bootstrap").json()["jobs"] if value["id"] == audit_task["id"])
        assert job["status"] == "running"


def test_dispatch_ignores_agents_on_offline_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state = client.get("/api/bootstrap").json()
        offline_researcher, offline_auditor = offline_agents(client)
        runtime = register_runtime(client, "online-cluster", ["plan", "research", "audit"])
        planner = register(client, "online-planner", runtime["id"], ["plan"])
        researcher = register(client, "online-researcher", runtime["id"], ["research"])
        auditor = register(client, "online-auditor", runtime["id"], ["audit"])
        enqueue_producer(client, state, planner, "plan")
        output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"], "action").json()
        assert output["audit_job"]["agent_id"] == auditor["id"] != offline_auditor["id"]
        finish_audit(client, claim(client, runtime["id"]), "approve")
        execution = next(job for job in client.get("/api/bootstrap").json()["jobs"] if job["kind"] == "research")
        assert execution["agent_id"] == researcher["id"] != offline_researcher["id"]


def test_human_review_cancels_queued_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        enqueue_producer(client, state, producer, "plan")
        output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"], "action").json()
        command(client, "review_node", {"node_id": output["node"]["id"], "decision": "approve"})
        audit = db.row("SELECT * FROM jobs WHERE id=?", (output["audit_job"]["id"],))
        assert audit["status"] == "cancelled"
        assert claim(client, runtime["id"])["job"]["kind"] == "research"


def test_human_review_cleans_running_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        state, runtime, producer, _ = setup_cluster(client)
        enqueue_producer(client, state, producer)
        output = finish_producer(client, claim(client, runtime["id"]), state["nodes"][0]["id"]).json()
        audit_task = claim(client, runtime["id"])
        command(client, "review_node", {"node_id": output["node"]["id"], "decision": "approve"})
        cleanup = db.row("SELECT * FROM workspace_commands WHERE job_id=?", (audit_task["id"],))
        assert db.row("SELECT status FROM jobs WHERE id=?", (audit_task["id"],))["status"] == "cancelled"
        assert cleanup["action"] == "delete_job_workspace" and cleanup["attempt_id"] == audit_task["attempt_id"]
