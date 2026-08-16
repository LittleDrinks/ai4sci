from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.orchestrator import OrchestratorAgent, WorkflowManager


class FakeAgent:
    def __init__(self, action=None, content="可以按当前思路推进", count=8, select=4):
        self.value = {"content": content, "action": action, "count": count, "select": select}
        self.call = None

    def decide(self, node, messages, message, actions):
        self.call = (node, messages, message, actions)
        return self.value


class FakeHarness:
    def __init__(self, value):
        self.value = value
        self.call = None

    def json(self, role, instruction, payload):
        self.call = (role, instruction, payload)
        return self.value


class FailingAgent:
    def decide(self, node, messages, message, actions):
        raise RuntimeError("model unavailable")


def test_question_instruction_starts_brainstorm(world, project):
    question = world.nodes(project["id"])[0]
    agent = FakeAgent("brainstorm", count=5, select=2)
    reply = WorkflowManager(world, agent).assist(project["id"], question["id"], "生成五个方向，只保留两个")
    assert reply["workflow"]["kind"] == "brainstorm"
    assert reply["workflow"]["payload"] == {"instruction": "生成五个方向，只保留两个", "mode": "brainstorm", "count": 5, "select": 2}
    assert agent.call[3] == ["brainstorm"]
    assert len(world.messages(project["id"], question["id"])) == 2


def test_discussion_does_not_start_workflow(world, project):
    direction = world.create_node(project["id"], "direction", {"text": "Candidate"})
    reply = WorkflowManager(world, FakeAgent()).assist(project["id"], direction["id"], "解释一下这个方向")
    assert reply["workflow"] is None
    assert reply["actions"] == ["research"]
    assert world.workflows(project["id"]) == []


def test_failed_assistant_turn_does_not_persist_partial_message(world, project):
    question = world.nodes(project["id"])[0]
    with pytest.raises(RuntimeError, match="model unavailable"):
        WorkflowManager(world, FailingAgent()).assist(project["id"], question["id"], "开始研究")
    assert world.messages(project["id"], question["id"]) == []


def test_orchestrator_agent_passes_conversation_and_validates_action():
    harness = FakeHarness({"content": "开始规划", "action": "research", "count": 8, "select": 4})
    node = {"id": "node:d", "kind": "direction", "life_state": "admitted",
            "direction_status": "proposed", "payload": {"text": "轨道稳定"}, "rebuttal": None}
    result = OrchestratorAgent(harness).decide(node, [{"role": "user", "content": "先讨论"}], "开始实验", ["research"])
    assert result["action"] == "research"
    assert harness.call[2]["conversation"] == [{"role": "user", "content": "先讨论"}]


def test_materializing_draft_clears_conversation(world, project):
    question = world.nodes(project["id"])[0]
    manager = WorkflowManager(world, FakeAgent())
    manager.assist(project["id"], question["id"], "记录这个方向")
    node = manager.materialize(project["id"], question["id"], "direction", {"text": "Resonance"})
    assert node["parent_id"] == question["id"]
    assert world.messages(project["id"], question["id"]) == []


def test_new_conversation_clears_current_node_messages(world, project):
    question = world.nodes(project["id"])[0]
    world.add_message(project["id"], question["id"], "user", "旧草稿")
    response = TestClient(create_app(world)).delete(
        f"/api/v1/projects/{project['id']}/messages", params={"node_id": question["id"]})
    assert response.status_code == 204
    assert world.messages(project["id"], question["id"]) == []
