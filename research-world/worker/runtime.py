from __future__ import annotations

import contextlib
import io
import sys
import threading
from typing import Any

import httpx

from .api import ControlPlane, LeaseLost
from .config import Settings
from .harness import collect_outputs, prepare_workspace, run_harness
from .trace import publish_trace


HEARTBEAT_SECONDS = 10


class TaskLease:
    def __init__(self, api: ControlPlane, task: dict[str, Any]):
        self.api = api
        self.task = task
        self.stop_signal = threading.Event()
        self.lost = threading.Event()
        self.thread = threading.Thread(target=self._run, name=f"lease-{task['id']}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_signal.set()
        if self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join()

    def mark_lost(self) -> None:
        self.lost.set()
        self.stop_signal.set()

    def assert_owned(self) -> None:
        if self.lost.is_set():
            raise LeaseLost("stale task attempt")

    def _run(self) -> None:
        while not self.stop_signal.wait(HEARTBEAT_SECONDS):
            self._pulse()

    def _pulse(self) -> None:
        self._runtime_heartbeat()
        try:
            self.api.task_heartbeat(self.task)
        except LeaseLost:
            self.mark_lost()
        except httpx.HTTPError:
            pass

    def _runtime_heartbeat(self) -> None:
        try:
            self.api.heartbeat(self.task["runtime_id"])
        except httpx.HTTPError:
            pass


class EventWriter(io.TextIOBase):
    def __init__(self, api: ControlPlane, task: dict[str, Any]):
        self.api = api
        self.task = task
        self.buffer = ""

    def write(self, text: str) -> int:
        sys.__stdout__.write(text)
        self.buffer += text
        self._emit_lines()
        return len(text)

    def flush(self) -> None:
        sys.__stdout__.flush()
        if self.buffer.strip():
            self.api.event(self.task, "log", self.buffer.strip())
        self.buffer = ""

    def _emit_lines(self) -> None:
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                self.api.event(self.task, "log", line)


def execute_task(api: ControlPlane, settings: Settings, task: dict[str, Any]) -> dict[str, Any]:
    workspace = prepare_workspace(settings.workspace_root, task)
    api.event(task, "lifecycle", "Workspace prepared", workspace=str(workspace))
    writer = EventWriter(api, task)
    api.event(task, "lifecycle", "Agent started", model=task["agent"]["model"])
    try:
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            result = run_harness(settings, task, workspace)
    finally:
        writer.flush()
    publish_trace(api, task, workspace)
    outputs = collect_outputs(task, workspace, result)
    api.event(task, "lifecycle", "Agent finished")
    return outputs


def process_task(api: ControlPlane, settings: Settings, task: dict[str, Any]) -> None:
    lease = TaskLease(api, task)
    lease.start()
    try:
        _run_owned(api, settings, task, lease)
    except LeaseLost:
        lease.mark_lost()
    except Exception as error:
        _fail_owned(api, task, lease, error)
    finally:
        lease.stop()


def _run_owned(api: ControlPlane, settings: Settings, task: dict[str, Any], lease: TaskLease) -> None:
    api.event(task, "lifecycle", "Task claimed", job_kind=task["job"]["kind"])
    outputs = execute_task(api, settings, task)
    lease.stop()
    lease.assert_owned()
    api.complete(task, outputs)


def _fail_owned(api: ControlPlane, task: dict[str, Any], lease: TaskLease, error: Exception) -> None:
    lease.stop()
    if lease.lost.is_set():
        return
    try:
        api.fail(task, str(error))
    except LeaseLost:
        lease.mark_lost()
