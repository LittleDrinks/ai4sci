import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "review_scaling"))
sys.path.insert(0, str(Path(__file__).parent))
from benchmarks.review_query.graph import aggregate_json, get_json, impact_json, subgraph_json


def _graph():
    return {12: {"scale": 12, "rows": {"r-1": {"run_id": "r-1", "audit": "accepted", "execution": "completed", "isolated": False, "method_family_status": "pending", "pairwise_adjudication": "not_run"}}, "events": [{"run_id": "r-1", "event": "audit_completed", "status": "accepted"}]}}


def test_queries_are_deterministic_and_typed():
    graphs = _graph()
    assert json.loads(aggregate_json(graphs, 12))["found"] is True
    assert json.loads(get_json(graphs, 12, "missing")) == {"found": False, "run_id": "missing", "scale": 12}
    assert json.loads(impact_json(graphs, 12))["count"] == 0
    assert len(json.loads(subgraph_json(graphs, 12, "r-1", 1))["nodes"]) == 2


def test_unknown_scale_is_explicit():
    assert json.loads(aggregate_json(_graph(), 36)) == {"found": False, "scale": 36}
