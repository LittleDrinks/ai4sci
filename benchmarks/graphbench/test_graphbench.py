import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from graph import ResearchGraph, digest
from scenarios import assert_invariants, run_all


def test_graphbench_scenarios_pass():
    results = run_all()
    assert all(result["passed"] for result in results)


def test_replay_is_canonical():
    graph = ResearchGraph()
    assert graph.submit("root", content="x").accepted
    assert graph.audit("root", "approve").accepted
    assert graph.claim("root", "a1").accepted
    assert graph.complete("root", "a1", "out").accepted
    rebuilt = ResearchGraph.replay(graph.event_dicts())
    assert rebuilt.snapshot() == graph.snapshot()
    assert rebuilt.state_digest() == graph.state_digest()


def test_hash_helper_is_stable():
    assert digest("same") == digest("same")
    assert digest("same") != digest("different")


def test_unreviewed_action_is_gated():
    graph = ResearchGraph()
    assert graph.submit("candidate").accepted
    assert not graph.can_execute("candidate")
    assert_invariants(graph)
