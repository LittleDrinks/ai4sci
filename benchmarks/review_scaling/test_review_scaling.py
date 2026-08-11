import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from questions import gold_answers, score_response
from representations import build_representations


def _window():
    rows = [
        {"run_id": "b-s0-c0", "strategy": "B", "seed": 0, "candidate_index": 0, "method_family_status": "provisional_slug_only", "pairwise_adjudication": "not_run", "sessions": [], "final": {"candidate": {"title": "blind"}}, "audit": {"status": "rejected"}, "execution": {"status": "skipped"}},
        {"run_id": "r-s2-c2", "strategy": "R", "seed": 2, "candidate_index": 2, "method_family_status": "provisional_slug_only", "pairwise_adjudication": "not_run", "sessions": [], "final": {"candidate": {"title": "reflect"}}, "audit": {"status": "accepted"}, "execution": {"status": "completed"}},
    ]
    events = [{"run_id": "b-s0-c0", "session_index": 0, "event": "audit_completed", "status": "rejected"}, {"run_id": "b-s0-c0", "event": "candidate_isolated"}, {"run_id": "b-s0-c0", "event": "execution_completed", "execution": {"status": "skipped"}}, {"run_id": "r-s2-c2", "session_index": 0, "event": "audit_completed", "status": "accepted"}, {"run_id": "r-s2-c2", "event": "execution_completed", "execution": {"status": "completed"}}]
    return {"run_count": 2, "results": rows, "events": events, "traces": {"b-s0-c0": [], "r-s2-c2": []}}


def test_gold_comes_from_event_states():
    gold = gold_answers(_window())
    assert gold["fact_counts"]["answer"] == {"accepted_final_count": 1, "execution_completed_count": 1}
    assert gold["impact_scope"]["answer"]["run_ids"] == ["b-s0-c0"]
    assert gold["todo_status"]["answer"]["isolated_count"] == 1


def test_scoring_marks_missing_tail_unsupported():
    window = _window()
    window["results"] = window["results"][:1]
    window["events"] = window["events"][:3]
    gold = gold_answers(window)
    scored = score_response('{"tail_fact":{"answer":"no evidence","unsupported":true}}', gold)
    assert scored[-1]["correct"] is True


def test_scoring_compares_values_not_model_keys():
    gold = gold_answers(_window())
    response = '{"fact_counts":{"answer":{"accepted_runs":1,"completed_runs":1}},"todo_status":{"answer":{"family":"provisional_slug_only","pairwise":"not_run","isolated":1,"skipped":1}}}'
    scored = score_response(response, gold)
    assert scored[0]["correct"] is True
    assert scored[2]["correct"] is True


def test_scoring_rejects_wrong_todo_count():
    gold = gold_answers(_window())
    response = '{"todo_status":{"answer":{"family":"provisional_slug_only","pairwise":"not_run","isolated":2,"skipped":1}}}'
    assert score_response(response, gold)[2]["correct"] is False


def test_four_representations_are_built():
    reps = build_representations(_window())
    assert [rep["id"] for rep in reps] == ["graph_dump", "review_view", "flat_report", "raw_log"]
    assert all(rep["text"] for rep in reps)
