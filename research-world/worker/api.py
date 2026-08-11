from __future__ import annotations

from typing import Any

import httpx


class LeaseLost(RuntimeError):
    pass


STALE_ATTEMPT_CODE = "stale_task_attempt"


def task_identity(task: dict[str, Any]) -> dict[str, str]:
    return {"runtime_id": task["runtime_id"], "attempt_id": task["attempt_id"]}


class ControlPlane:
    def __init__(self, server: str):
        self.client = httpx.Client(base_url=server.rstrip("/"), timeout=30, trust_env=False)

    def close(self) -> None:
        self.client.close()

    def register(self, name: str, version: str) -> str:
        body = {
            "name": name,
            "sdk": "ResearchHarness",
            "version": version,
            "capabilities": ["research", "html_report", "audit", "plan"],
        }
        return self._post("/api/runtimes/register", body)["id"]

    def claim(self, runtime_id: str) -> dict[str, Any] | None:
        response = self.client.post("/api/tasks/claim", json={"runtime_id": runtime_id})
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()["task"]

    def claim_maintenance(self, runtime_id: str) -> dict[str, Any] | None:
        response = self.client.post("/api/maintenance/claim", json={"runtime_id": runtime_id})
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()["command"]

    def complete_maintenance(self, command: dict[str, Any]) -> None:
        body = {"runtime_id": command["runtime_id"]}
        self._post(f"/api/maintenance/{command['id']}/complete", body)

    def heartbeat(self, runtime_id: str, status: str = "online") -> None:
        self._post(f"/api/runtimes/{runtime_id}/heartbeat", {"status": status})

    def task_heartbeat(self, task: dict[str, Any]) -> None:
        self._task_post(f"/api/tasks/{task['id']}/heartbeat", task_identity(task))

    def event(self, task: dict[str, Any], kind: str, message: str, **payload: Any) -> None:
        body = {
            **task_identity(task),
            "kind": kind,
            "message": message,
            "payload": payload,
        }
        self._task_post(f"/api/tasks/{task['id']}/events", body)

    def complete(self, task: dict[str, Any], outputs: dict[str, Any]) -> None:
        body = {**outputs, **task_identity(task)}
        self._task_post(f"/api/tasks/{task['id']}/complete", body)

    def fail(self, task: dict[str, Any], error: str) -> None:
        body = {**task_identity(task), "error": error}
        self._task_post(f"/api/tasks/{task['id']}/fail", body)

    def _task_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(path, json=body)
        if response.status_code == 409 and response_code(response) == STALE_ATTEMPT_CODE:
            raise LeaseLost("stale task attempt")
        response.raise_for_status()
        return response.json() if response.content else {}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(path, json=body)
        response.raise_for_status()
        return response.json() if response.content else {}


def response_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("code") if isinstance(body, dict) else None
