import json

import pytest
from fastapi.testclient import TestClient

from server import db
from server.app import app
from worker import harness
from worker.prompts import PLAN_PROMPT, task_prompt


ACTOR = {"kind": "human", "id": "planner-test"}


def command(client, kind, payload):
    response = client.post("/api/commands", json={"type": kind, "actor": ACTOR, "payload": payload})
    assert response.status_code == 200, response.text
    return response.json()["result"]


def register(client):
    return client.post("/api/runtimes/register", json={
        "name": "plan-runtime", "sdk": "ResearchHarness", "version": "test",
        "capabilities": ["plan", "research"],
    }).json()


def agent(client, name, runtime_id, capabilities):
    return command(client, "create_agent", {
        "name": name, "runtime_id": runtime_id, "model": "test",
        "instructions": name, "capabilities": capabilities,
    })


def complete(client, task, submission):
    return client.post(f"/api/tasks/{task['id']}/complete", json={
        "runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"],
        "result_text": "done", "submission": submission,
    })


def plan_job(client, state, planner):
    return command(client, "enqueue_job", {
        "project_id": state["active_project_id"], "agent_id": planner["id"], "kind": "plan",
        "subject_id": state["nodes"][0]["id"], "prompt": "Plan one experiment",
    })


def action_submission(root_id):
    return {"kind": "action", "title": "One action", "summary": "Test it",
            "content": {"prompt": "Run it"}, "dependencies": [root_id]}


def task_value(job):
    return {"id": "job:1", "attempt_id": "attempt:1", "job": job,
            "agent": {}, "project": {}, "subject": {}, "context": {}}


def run_plan_flow(client):
    state = client.get("/api/bootstrap").json()
    runtime = register(client)
    planner = agent(client, "planner", runtime["id"], ["plan"])
    researcher = agent(client, "researcher", runtime["id"], ["research"])
    plan = plan_job(client, state, planner)
    task = client.post("/api/tasks/claim", json={"runtime_id": runtime["id"]}).json()["task"]
    root_id = state["nodes"][0]["id"]
    wrong = complete(client, task, {**action_submission(root_id), "kind": "result"})
    assert wrong.status_code == 409
    output = complete(client, task, action_submission(root_id)).json()
    reviewed = command(client, "review_node", {"node_id": output["node"]["id"], "decision": "approve"})
    jobs = client.get("/api/bootstrap").json()["jobs"]
    executions = [job for job in jobs if job["kind"] == "research" and job["subject_id"] == output["node"]["id"]]
    return plan, researcher, output, reviewed, executions


def test_plan_approving_action_queues_one_research_job(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    with TestClient(app) as client:
        plan, researcher, output, reviewed, executions = run_plan_flow(client)
        assert plan["id"] == output["job"]["id"]
        assert researcher["id"] == executions[0]["agent_id"]
        assert reviewed["node"]["status"] == "admitted"
        assert len(executions) == 1 and executions[0]["status"] == "queued"


def test_plan_revision_prompt_and_worker_output(tmp_path):
    job = {"kind": "plan", "revision": 0, "review_mode": None,
           "review_scope": None, "review_feedback": None}
    assert task_prompt(job) == PLAN_PROMPT
    assert "one concrete" in PLAN_PROMPT and "Do not execute" in PLAN_PROMPT
    workspace = harness.prepare_workspace(tmp_path, task_value(job))
    (workspace / "submission.json").write_text(json.dumps({"kind": "action"}))
    assert harness.collect_outputs({"job": job}, workspace, "planned")["submission"]["kind"] == "action"
    revised = {**job, "revision": 1, "review_mode": "continue", "review_scope": "node", "review_feedback": "Clarify"}
    prompt = task_prompt(revised)
    assert "one revised action" in prompt


def test_worker_rejects_wrong_plan_output(tmp_path):
    job = {"kind": "plan", "revision": 0, "review_mode": None,
           "review_scope": None, "review_feedback": None}
    workspace = harness.prepare_workspace(tmp_path, task_value(job))
    (workspace / "submission.json").write_text(json.dumps({"kind": "result"}))
    with pytest.raises(ValueError, match="kind=action"):
        harness.collect_outputs({"job": job}, workspace, "planned")
