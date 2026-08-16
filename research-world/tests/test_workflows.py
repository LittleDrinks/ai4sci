from __future__ import annotations

import pytest

from server.workflows import AgentFacade, WorkflowEngine, mmr


class FakeEmbedding:
    def __init__(self, vectors):
        self.vectors = vectors

    def __call__(self, text):
        return self.vectors[text]


class FakeRunner:
    def __init__(self, exit_code=0):
        self.exit_code = exit_code
        self.calls = []

    def run(self, step):
        self.calls.append(step)
        return {"exit_code": self.exit_code, "stdout": "measured", "usage": {"wall_ms": 10}}


class FakeAgents:
    def __init__(self, candidates=None, decisions=None):
        self.candidates = candidates or []
        self.decisions = list(decisions or [])
        self.pairs = []

    def brainstorm(self, context, count):
        return {"candidates": self.candidates[:count]}

    def pairwise(self, left, right):
        self.pairs.append((left, right))
        return True

    def plan(self, direction):
        return {"steps": [{"image": "busybox:1.36", "command": ["true"]}]}

    def review(self, context, reviewer):
        decision = self.decisions.pop(0) if self.decisions else "approve"
        return {"decision": decision, "quality": 0.8, "diversity": 0.7, "rebuttal": reviewer}

    def reflect(self, context):
        return {"text": "Reflected direction"}


class FakeHarness:
    def __init__(self, value):
        self.value = value
        self.call = None

    def json(self, role, instruction, payload):
        self.call = (role, instruction, payload)
        return self.value


def engine(world, agents, embedding=None, runner=None):
    return WorkflowEngine(world, agents, embedding or FakeEmbedding({}), runner or FakeRunner())


def admitted_direction(world, project, text="Existing direction"):
    node = world.create_node(project["id"], "direction", {"text": text})
    return world.admit_node(node["id"])


def test_brainstorm_agent_enforces_named_response_contract():
    harness = FakeHarness({"research_directions": []})
    with pytest.raises(ValueError, match="required field 'candidates'"):
        AgentFacade(harness).brainstorm({"text": "Why?"}, 2)
    assert '"candidates"' in harness.call[1]
    assert harness.call[2] == {"text": "Why?", "count": 2}


def test_mmr_balances_quality_and_similarity():
    candidates = [{"text": "a", "quality": 0.9, "vector": [1, 0]},
                  {"text": "b", "quality": 0.88, "vector": [0.99, 0.01]},
                  {"text": "c", "quality": 0.8, "vector": [0, 1]}]
    assert [item["text"] for item in mmr(candidates, 2)] == ["a", "c"]


def test_brainstorm_blocks_duplicates_and_admits_selected(world, project):
    existing = admitted_direction(world, project)
    world.embedding = FakeEmbedding({"Existing direction": [1, 0], "Duplicate": [1, 0], "Novel": [0, 1]})
    world.update_node(existing["id"], payload={"text": "Existing direction"})
    agents = FakeAgents([{"text": "Duplicate", "quality": 0.9}, {"text": "Novel", "quality": 0.8}])
    workflow = world.create_workflow(project["id"], world.nodes(project["id"])[0]["id"], "brainstorm", {"select": 2})
    result = engine(world, agents, world.embedding).run(workflow["id"])
    directions = [node for node in world.nodes(project["id"]) if node["kind"] == "direction"]
    assert result["status"] == "completed"
    assert world.workflow_events(workflow["id"])[1]["actor"] == "brainstormer"
    assert any(node["life_state"] == "ghost" and "cos=1.00" in node["rejection_reason"] for node in directions)
    assert any(node["payload"]["text"] == "Novel" and node["life_state"] == "admitted" for node in directions)


def test_gray_similarity_uses_pairwise_judge(world, project):
    admitted_direction(world, project)
    vectors = {"Existing direction": [1, 0], "Gray": [0.7, 0.714]}
    world.embedding = FakeEmbedding(vectors)
    agents = FakeAgents([{"text": "Gray", "quality": 0.7}])
    workflow = world.create_workflow(project["id"], world.nodes(project["id"])[0]["id"], "brainstorm")
    engine(world, agents, world.embedding).run(workflow["id"])
    assert agents.pairs == [("Gray", "Existing direction")]


def test_manual_research_confirms_start_and_each_step(world, project):
    direction = admitted_direction(world, project)
    workflow = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect")
    runner = FakeRunner()
    service = engine(world, FakeAgents(), runner=runner)
    planned = service.confirm(workflow["id"])
    assert planned["status"] == "waiting_human"
    assert planned["payload"]["experiment_id"].startswith("node:")
    assert runner.calls == []
    completed = service.confirm(workflow["id"])
    assert completed["status"] == "completed"
    assert len(runner.calls) == 1
    assert world.node(direction["id"])["direction_status"] == "supported"


def test_auto_review_starts_next_iteration(world, project):
    world.set_auto(project["id"], True)
    direction = admitted_direction(world, project)
    workflow = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect")
    result = engine(world, FakeAgents(), runner=FakeRunner()).run(workflow["id"])
    queued = [item for item in world.workflows(project["id"]) if item["status"] == "queued"]
    assert result["status"] == "completed"
    assert len(queued) == 1


def test_two_rejections_pause_lineage(world, project):
    world.set_auto(project["id"], True)
    direction = admitted_direction(world, project)
    workflow = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect")
    service = engine(world, FakeAgents(decisions=["reject", "reject"]), runner=FakeRunner(exit_code=1))
    result = service.run(workflow["id"])
    assert result["status"] == "paused"
    assert "连续 2 次" in result["payload"]["reason"]


def test_double_review_conflict_escalates_to_human(world, project):
    direction = admitted_direction(world, project)
    workflow = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect")
    service = engine(world, FakeAgents(decisions=["approve", "reject"]), runner=FakeRunner())
    service.confirm(workflow["id"])
    result = service.confirm(workflow["id"])
    assert result["status"] == "waiting_human"
    assert result["payload"]["conflict_node"].startswith("node:")
