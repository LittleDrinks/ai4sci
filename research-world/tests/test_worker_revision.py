import json

import pytest

from worker import harness
from worker.config import Settings


class FakeAgent:
    def __init__(self):
        self.calls = []

    def _run_session(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"result_text": "current revision"}


def test_initial_run_uses_session_api(tmp_path, monkeypatch):
    task = task_value(0)
    workspace = harness.prepare_workspace(tmp_path, task)
    agent = FakeAgent()
    monkeypatch.setattr(harness, "build_agent", lambda *_: agent)
    result = harness.run_harness(settings(tmp_path), task, workspace)
    assert result == "current revision"
    assert agent.calls[0][1]["prior_messages"] is None


def test_revision_reuses_workspace_and_messages(tmp_path, monkeypatch):
    initial = task_value(0)
    workspace = harness.prepare_workspace(tmp_path, initial)
    write_prior_state(workspace)
    write_old_outputs(workspace)
    revised = task_value(1)
    assert harness.prepare_workspace(tmp_path, revised) == workspace
    assert not (workspace / "submission.json").exists()
    assert not (workspace / "report.html").exists()
    agent = FakeAgent()
    monkeypatch.setattr(harness, "build_agent", lambda *_: agent)
    harness.run_harness(settings(tmp_path), revised, workspace)
    prompt, values = agent.calls[0]
    assert values["prior_messages"] == [{"role": "assistant", "content": "old answer"}]
    assert "missing source" in prompt


def test_revision_without_session_fails(tmp_path):
    task = task_value(1)
    workspace = harness.prepare_workspace(tmp_path, task)
    with pytest.raises(FileNotFoundError, match="prior ResearchHarness session"):
        harness.prior_messages(task, workspace)


def task_value(revision):
    return {
        "id": "job:1", "attempt_id": "attempt:1",
        "job": {"kind": "html_report", "revision": revision,
                "review_mode": "continue", "review_scope": "artifact",
                "review_feedback": "missing source"},
        "agent": {"model": "test", "instructions": ""},
        "project": {}, "subject": {}, "context": {},
    }


def settings(root):
    return Settings(api_base="http://example.test", api_key="test", workspace_root=root)


def write_prior_state(workspace):
    path = workspace / "traces" / "session_state_1.json"
    path.write_text(json.dumps({"messages": [{"role": "assistant", "content": "old answer"}]}))


def write_old_outputs(workspace):
    (workspace / "submission.json").write_text("{}")
    (workspace / "report.html").write_text("old")
