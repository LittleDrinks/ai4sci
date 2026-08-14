import json

import pytest

from server.research import ResearchState
from server.dossier import DossierExporter


DIRECTION = {"title": "Bounded simulation", "rationale": "Measure one mechanism.", "workflow": "simulation", "completion_test": "A replayed metric exists.", "remaining": "External validation."}


def test_direction_cycle_and_work_item_are_separate(world, project):
    state = ResearchState(world)
    direction = state.propose_directions(project["id"], [DIRECTION])[0]
    assert direction["status"] == "proposed"
    state.admit_direction(direction["id"])
    cycle = state.start_cycle(direction["id"])
    work = state.create_work_item(cycle["id"], "experiment", {"claim": "bounded"})
    assert [step["role"] for step in work["steps"]] == ["plan", "execute", "science_review", "code_review"]
    assert all(step["attempt_id"] is None for step in work["steps"])
    assert state.node(direction["id"])["status"] == "active"


def test_work_item_gate_fails_closed(world, project):
    state = ResearchState(world)
    direction = state.propose_directions(project["id"], [DIRECTION])[0]
    state.admit_direction(direction["id"])
    work = state.create_work_item(state.start_cycle(direction["id"])["id"], "claim", {})
    with pytest.raises(ValueError, match="coverage"):
        state.complete_work_item(work["id"], {})
    for step in work["steps"]:
        state.finish_step(step["id"], {})
    state.add_finding(work["steps"][-1]["id"], "reviewer", {"check_id": "SCOPE-INFLATE", "severity": "major", "evidence": [{"id": "claim:1", "locator": "text", "sha256": "abc"}], "recommendation": "Narrow scope", "status": "open"})
    with pytest.raises(ValueError, match="blocking"):
        state.complete_work_item(work["id"], {})


def test_completed_cycle_keeps_frontier_visible(world, project):
    state = ResearchState(world)
    first, second = state.propose_directions(project["id"], [DIRECTION, {**DIRECTION, "title": "Another route"}])
    state.admit_direction(first["id"])
    state.admit_direction(second["id"])
    cycle = state.start_cycle(first["id"])
    state.complete_cycle(cycle["id"], {"title": "Brief", "open_questions": ["Need a larger test."]})
    assert state.node(first["id"])["status"] == "completed"
    assert state.node(second["id"])["status"] == "frontier"
    assert state.cycle(cycle["id"])["brief"]["open_questions"] == ["Need a larger test."]


def test_completed_cycle_exports_readable_dossier(world, project):
    state = ResearchState(world)
    direction = state.propose_directions(project["id"], [DIRECTION])[0]
    state.admit_direction(direction["id"])
    cycle = state.start_cycle(direction["id"])
    state.complete_cycle(cycle["id"], {"title": "Bounded result", "learned": ["One result."], "open_questions": ["One gap."]})
    result = DossierExporter(world).export(project["id"], cycle["id"])
    markdown = world.path(result["markdown"]).read_text()
    assert "## Learned\n- One result." in markdown
    assert "## Open Questions\n- One gap." in markdown


def test_exported_attempt_log_includes_input_and_output(world, project):
    state = ResearchState(world)
    direction = state.propose_directions(project["id"], [DIRECTION])[0]
    state.admit_direction(direction["id"])
    cycle = state.start_cycle(direction["id"])
    work = state.create_work_item(cycle["id"], "claim", {})
    attempt = world.create_attempt(cycle["run_id"], work["generation_id"], world.run(cycle["run_id"])["project_snapshot_id"], "worker")
    state.bind_attempt(work["id"], attempt["id"])
    state.add_attempt_log(attempt["id"], b'{"type":"model_output"}\n')
    world.complete_attempt(attempt["id"], b'{"answer":1}', b'{"question":1}', b'{}')
    result = DossierExporter(world).export(project["id"], cycle["id"])
    exported = next((world.path(result["json"]).parent / "logs").glob("*.log")).read_text()
    assert '"type": "attempt_input"' in exported
    assert '"type": "attempt_output"' in exported
