from __future__ import annotations

from server.orchestrator import WorkflowManager


def test_question_context_offers_brainstorm(world, project):
    question = world.nodes(project["id"])[0]
    reply = WorkflowManager(world).assist(project["id"], question["id"], "下一步做什么？")
    assert reply["actions"] == ["brainstorm"]
    assert len(world.messages(project["id"], question["id"])) == 2


def test_direction_outcome_offers_reflect_or_replan(world, project):
    direction = world.create_node(project["id"], "direction", {"text": "Candidate"})
    world.update_node(direction["id"], direction_status="refuted")
    reply = WorkflowManager(world).assist(project["id"], direction["id"], "如何继续？")
    assert reply["actions"] == ["reflect", "replan"]


def test_materializing_draft_clears_conversation(world, project):
    question = world.nodes(project["id"])[0]
    manager = WorkflowManager(world)
    manager.assist(project["id"], question["id"], "记录这个方向")
    node = manager.materialize(project["id"], question["id"], "direction", {"text": "Resonance"})
    assert node["parent_id"] == question["id"]
    assert world.messages(project["id"], question["id"]) == []
