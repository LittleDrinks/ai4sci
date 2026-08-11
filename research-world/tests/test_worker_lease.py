import json
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from server import db
from server.app import app
from worker import runtime
from worker.api import ControlPlane, LeaseLost


TASK = {
    "id": "job:1",
    "attempt_id": "attempt:1",
    "runtime_id": "runtime:1",
    "job": {"kind": "research"},
}


class FakeControlPlane:
    def __init__(self, mode="normal"):
        self.mode = mode
        self.runtime_pulses = 0
        self.task_pulses = 0
        self.ready = threading.Event()
        self.completed = []
        self.failed = []

    def heartbeat(self, _runtime_id):
        self.runtime_pulses += 1

    def task_heartbeat(self, _task):
        self.task_pulses += 1
        if self.mode == "lost":
            self.ready.set()
            raise LeaseLost("stale")
        if self.mode == "network" and self.task_pulses == 1:
            raise httpx.ConnectError("offline")
        if self.task_pulses >= 2:
            self.ready.set()

    def event(self, *_args, **_kwargs):
        pass

    def complete(self, _task, outputs):
        if self.mode == "conflict":
            raise domain_conflict()
        self.completed.append(outputs)

    def fail(self, _task, error):
        self.failed.append(error)


def wait_for_pulses(api, _settings, _task):
    assert api.ready.wait(1)
    return {"result_text": "done"}


def run_task(monkeypatch, mode):
    api = FakeControlPlane(mode)
    monkeypatch.setattr(runtime, "HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(runtime, "execute_task", wait_for_pulses)
    runtime.process_task(api, None, TASK)
    return api


def test_long_task_renews_runtime_and_task_lease(monkeypatch):
    api = run_task(monkeypatch, "normal")
    assert api.runtime_pulses >= 2
    assert api.task_pulses >= 2
    assert api.completed == [{"result_text": "done"}]


def test_lease_loss_suppresses_complete_and_fail(monkeypatch):
    api = run_task(monkeypatch, "lost")
    assert api.completed == []
    assert api.failed == []


def test_network_error_retries_on_next_heartbeat(monkeypatch):
    api = run_task(monkeypatch, "network")
    assert api.task_pulses >= 2
    assert api.completed == [{"result_text": "done"}]


def test_domain_conflict_fails_current_job(monkeypatch):
    api = run_task(monkeypatch, "conflict")
    assert api.completed == []
    assert len(api.failed) == 1


def test_domain_conflict_marks_real_job_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(runtime, "execute_task", invalid_outputs)
    with TestClient(app) as client:
        task = claimed_research_task(client)
        api = attached_control_plane(client)
        runtime.process_task(api, None, task)
        job = next(value for value in client.get("/api/bootstrap").json()["jobs"] if value["id"] == task["id"])
        assert job["status"] == "failed"
        assert "409 Conflict" in job["error"]


def test_task_requests_include_runtime_and_attempt():
    requests = []
    api = control_plane(requests)
    api.task_heartbeat(TASK)
    api.event(TASK, "log", "hello")
    api.complete(TASK, {"result_text": "done"})
    api.fail(TASK, "failed")
    assert all(body["runtime_id"] == "runtime:1" for _, body in requests)
    assert all(body["attempt_id"] == "attempt:1" for _, body in requests)
    api.close()


def test_stale_task_code_becomes_lease_lost():
    api = control_plane([], 409, {"code": "stale_task_attempt"})
    with pytest.raises(LeaseLost):
        api.task_heartbeat(TASK)
    api.close()


def test_domain_conflict_remains_http_error():
    api = control_plane([], 409, {"detail": "submission conflict"})
    with pytest.raises(httpx.HTTPStatusError):
        api.task_heartbeat(TASK)
    api.close()


def domain_conflict():
    request = httpx.Request("POST", "http://control.test/api/tasks/job:1/complete")
    response = httpx.Response(409, request=request, json={"detail": "submission conflict"})
    return httpx.HTTPStatusError("domain conflict", request=request, response=response)


def invalid_outputs(_api, _settings, task):
    submission = {"kind": "report", "title": "Wrong kind",
                  "dependencies": [task["subject"]["id"]]}
    return {"result_text": "done", "submission": submission}


def claimed_research_task(client):
    state = client.get("/api/bootstrap").json()
    runtime_value = client.post("/api/runtimes/register", json={
        "name": "runtime", "sdk": "test", "version": "1", "capabilities": ["research"],
    }).json()
    agent = post_command(client, "create_agent", {
        "name": "agent", "runtime_id": runtime_value["id"], "model": "test",
        "capabilities": ["research"],
    })
    post_command(client, "enqueue_job", {
        "project_id": state["active_project_id"], "agent_id": agent["id"], "kind": "research",
        "subject_id": state["nodes"][0]["id"], "prompt": "Research",
    })
    return client.post("/api/tasks/claim", json={"runtime_id": runtime_value["id"]}).json()["task"]


def post_command(client, kind, payload):
    body = {"type": kind, "actor": {"kind": "human", "id": "test"}, "payload": payload}
    response = client.post("/api/commands", json=body)
    assert response.status_code == 200, response.text
    return response.json()["result"]


def attached_control_plane(client):
    api = ControlPlane(str(client.base_url))
    api.client.close()
    api.client = client
    return api


def control_plane(requests, status=200, payload=None):
    def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        return httpx.Response(status, json=payload or {})

    api = ControlPlane("http://control.test")
    api.client.close()
    api.client = httpx.Client(base_url="http://control.test", transport=httpx.MockTransport(handler))
    return api
