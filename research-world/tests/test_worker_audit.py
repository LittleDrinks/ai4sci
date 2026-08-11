import json

import httpx

from worker import harness
from worker.api import ControlPlane
from worker.prompts import task_prompt


def audit_task():
    return {
        "id": "job:audit", "attempt_id": "attempt:audit",
        "job": {"kind": "audit", "revision": 0, "review_mode": None,
                "review_scope": None, "review_feedback": None},
        "agent": {"model": "test", "instructions": ""},
        "project": {}, "subject": {"status": "pending_review"}, "context": {"nodes": [], "edges": []},
    }


def test_audit_collects_only_structured_audit_result(tmp_path):
    task = audit_task()
    workspace = harness.prepare_workspace(tmp_path, task)
    value = {"decision": "approve", "feedback": "", "checks": ["source linked"]}
    (workspace / "audit.json").write_text(json.dumps(value))
    assert harness.collect_outputs(task, workspace, "reviewed") == {
        "result_text": "reviewed", "audit": value,
    }
    assert not (workspace / "submission.json").exists()


def test_audit_prompt_forbids_producer_conversation_and_taxonomy():
    prompt = task_prompt(audit_task()["job"])
    assert "Do not seek or reconstruct the producer conversation" in prompt
    assert "Do not use a fixed defect taxonomy" in prompt
    assert "audit.json" in prompt


def test_local_runtime_registers_audit_capability():
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "runtime:1"})
    api = ControlPlane("http://control.test")
    api.client.close()
    api.client = httpx.Client(base_url="http://control.test", transport=httpx.MockTransport(handler))
    assert api.register("local", "test") == "runtime:1"
    assert requests[0]["capabilities"] == ["research", "html_report", "audit", "plan"]
    api.close()
