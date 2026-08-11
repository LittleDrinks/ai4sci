import json
import threading
from types import SimpleNamespace

import httpx
import pytest

import worker.__main__ as worker_main
from worker.api import ControlPlane
from worker.maintenance import execute_maintenance, maintenance_path


def command(action="delete_attempt_workspace", job_id="job:1", attempt_id="attempt:1"):
    return {"id": "maintenance:1", "runtime_id": "runtime:1", "job_id": job_id,
            "attempt_id": attempt_id, "action": action}


class MaintenanceApi:
    def __init__(self):
        self.completed = []

    def complete_maintenance(self, value):
        self.completed.append(value["id"])


def test_delete_attempt_keeps_job_and_siblings(tmp_path):
    selected = tmp_path / "job:1" / "attempt:1"
    sibling = tmp_path / "job:1" / "attempt:2"
    selected.mkdir(parents=True)
    sibling.mkdir()
    api = MaintenanceApi()
    execute_maintenance(api, settings(tmp_path), command())
    assert not selected.exists()
    assert sibling.exists()
    assert api.completed == ["maintenance:1"]


def test_delete_job_keeps_other_jobs(tmp_path):
    selected = tmp_path / "job:1" / "attempt:1"
    other = tmp_path / "job:2" / "attempt:1"
    selected.mkdir(parents=True)
    other.mkdir(parents=True)
    api = MaintenanceApi()
    execute_maintenance(api, settings(tmp_path), command("delete_job_workspace"))
    assert not selected.parent.exists()
    assert other.exists()


@pytest.mark.parametrize("value", [command("unknown"), command(job_id="../outside"),
                                   command(attempt_id=""), command(attempt_id="nested/path")])
def test_invalid_command_is_not_completed(tmp_path, value):
    api = MaintenanceApi()
    with pytest.raises(ValueError):
        execute_maintenance(api, settings(tmp_path), value)
    assert api.completed == []


def test_symlink_cannot_escape_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "job:1").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        maintenance_path(workspace, command("delete_job_workspace"))
    assert outside.exists()


def test_maintenance_api_claim_and_complete():
    requests = []
    api = control_plane(requests)
    value = api.claim_maintenance("runtime:1")
    api.complete_maintenance(value)
    assert requests == [("/api/maintenance/claim", {"runtime_id": "runtime:1"}),
                        ("/api/maintenance/maintenance:1/complete", {"runtime_id": "runtime:1"})]
    api.close()


def test_claim_loop_runs_maintenance_before_task(tmp_path):
    api = LoopApi()
    stop = threading.Event()
    api.stop = stop
    worker_main.claim_loop(api, settings(tmp_path), "runtime:1", 0, stop)
    assert api.calls[:4] == ["heartbeat", "maintenance_claim", "maintenance_complete", "task_claim"]


def settings(root):
    return SimpleNamespace(workspace_root=root)


def control_plane(requests):
    value = command()
    def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"command": value})
    api = ControlPlane("http://control.test")
    api.client.close()
    api.client = httpx.Client(base_url="http://control.test", transport=httpx.MockTransport(handler))
    return api


class LoopApi(MaintenanceApi):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.stop = None

    def heartbeat(self, _runtime_id):
        self.calls.append("heartbeat")

    def claim_maintenance(self, _runtime_id):
        self.calls.append("maintenance_claim")
        return command()

    def complete_maintenance(self, value):
        self.calls.append("maintenance_complete")

    def claim(self, _runtime_id):
        self.calls.append("task_claim")
        self.stop.set()
        return None
