from __future__ import annotations

import pytest

from server.app import bootstrap_data
from server.world import EDGE_POLARITIES, NODE_KINDS


def test_graph_has_four_node_kinds_and_two_edge_polarities():
    assert NODE_KINDS == {"question", "source", "direction", "experiment"}
    assert EDGE_POLARITIES == {"supports", "refutes"}


def test_pending_node_is_admitted_or_ghosted(world, project):
    pending = world.create_node(project["id"], "direction", {"text": "Test orbit resonance"})
    assert pending["life_state"] == "pending"
    assert world.admit_node(pending["id"])["life_state"] == "admitted"
    rejected = world.create_node(project["id"], "experiment", {"title": "Unstable solver"})
    ghost = world.ghost_node(rejected["id"], "numerical audit failed")
    assert (ghost["life_state"], ghost["rejection_reason"]) == ("ghost", "numerical audit failed")


def test_direction_state_is_terminal(world, project):
    direction = world.create_node(project["id"], "direction", {"text": "Resonance protects the orbit"})
    supported = world.update_node(direction["id"], direction_status="supported")
    assert supported["direction_status"] == "supported"
    with pytest.raises(ValueError, match="terminal"):
        world.update_node(direction["id"], direction_status="refuted")


def test_edge_requires_polarity_and_one_project(world, project, tmp_path):
    direction = world.create_node(project["id"], "direction", {"text": "Candidate"})
    evidence = world.create_node(project["id"], "source", {"title": "Paper"}, life_state="admitted")
    assert world.add_edge(evidence["id"], direction["id"], "supports")["polarity"] == "supports"
    other = world.create_project("other", tmp_path / "other", "Other question")
    with pytest.raises(ValueError, match="one project"):
        world.add_edge(evidence["id"], world.nodes(other["id"])[0]["id"], "refutes")


def test_bootstrap_includes_all_life_states(world, project):
    world.create_node(project["id"], "direction", {"text": "Pending"})
    ghost = world.create_node(project["id"], "experiment", {"title": "Failed"})
    world.ghost_node(ghost["id"], "audit rejected")
    data = bootstrap_data(world, project["id"])
    assert {node["life_state"] for node in data["nodes"]} == {"admitted", "pending", "ghost"}


def test_active_workflow_is_idempotent_for_node_and_experiment(world, project):
    direction = world.create_node(project["id"], "direction", {"text": "Candidate"})
    experiment = world.create_node(project["id"], "experiment", {"title": "Pending"}, parent_id=direction["id"])
    workflow = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect",
                                     {"experiment_id": experiment["id"]})
    duplicate = world.create_workflow(project["id"], direction["id"], "plan-execute-review-reflect")
    associated = world.create_workflow(project["id"], experiment["id"], "brainstorm")
    assert duplicate["id"] == workflow["id"] == associated["id"]
    assert len(world.workflows(project["id"])) == 1
