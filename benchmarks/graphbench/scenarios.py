"""Deterministic and concurrent GraphBench cases."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from random import Random
from threading import Barrier
from typing import Callable

from graph import ResearchGraph


def _parallel(count: int, fn: Callable[[int], object]) -> list[object]:
    barrier = Barrier(count)

    def worker(index: int) -> object:
        barrier.wait()
        return fn(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(worker, range(count)))


def _approved(graph: ResearchGraph, node_id: str, deps: tuple[str, ...] = ()) -> None:
    assert graph.submit(node_id, deps=deps).accepted
    assert graph.audit(node_id, "approve").accepted


def _check(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": passed, "detail": detail}


def _result(name: str, graph: ResearchGraph, checks: list[dict[str, object]]) -> dict[str, object]:
    return {
        "scenario": name,
        "passed": all(bool(item["passed"]) for item in checks),
        "checks": checks,
        "event_count": len(graph.events()),
        "state_digest": graph.state_digest(),
        "events": graph.event_dicts(),
    }


def concurrent_submissions() -> dict[str, object]:
    graph = ResearchGraph()
    results = _parallel(8, lambda _: graph.submit("same-action"))
    accepted = sum(result.accepted for result in results)
    checks = [_check("single_winner", accepted == 1, f"accepted={accepted}")]
    checks.append(_check("one_submission_event", len(graph.events()) == 1, "duplicate ids are rejected atomically"))
    return _result("concurrent_submissions", graph, checks)


def duplicate_consumption() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "action")
    claims = _parallel(2, lambda _: graph.claim("action", "attempt-1"))
    completed = graph.complete("action", "attempt-1", "result")
    duplicate = graph.claim("action", "attempt-1")
    claim_events = [event for event in graph.events() if event.kind == "execution_claimed"]
    checks = [
        _check("one_claim", sum(item.accepted for item in claims) == 1, "same attempt has one consumer"),
        _check("one_claim_event", len(claim_events) == 1, "claim is append-once"),
        _check("completion_accepted", completed.accepted, completed.reason),
        _check("reconsume_rejected", not duplicate.accepted, duplicate.reason),
    ]
    return _result("duplicate_consumption", graph, checks)


def audit_race() -> dict[str, object]:
    graph = ResearchGraph()
    assert graph.submit("candidate").accepted
    decisions = ["approve", "reject"]
    results = _parallel(2, lambda index: graph.audit("candidate", decisions[index]))
    audits = [event for event in graph.events() if event.kind == "audit_recorded"]
    status = graph.node("candidate").status
    checks = [
        _check("one_audit_winner", sum(item.accepted for item in results) == 1, "stale audit loses the race"),
        _check("one_audit_event", len(audits) == 1, "audit state changes once"),
        _check("terminal_review_state", status in {"approved", "isolated"}, f"status={status}"),
    ]
    return _result("audit_race", graph, checks)


def upstream_invalidation() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "upstream")
    assert graph.claim("upstream", "u-1").accepted
    assert graph.complete("upstream", "u-1", "observation").accepted
    _approved(graph, "downstream", ("upstream",))
    assert graph.claim("downstream", "d-1").accepted
    invalidated = graph.invalidate("upstream", "calibration drift")
    late_completion = graph.complete("downstream", "d-1", "stale result")
    upstream = graph.node("upstream")
    downstream = graph.node("downstream")
    checks = [
        _check("invalidation_accepted", invalidated.accepted, invalidated.reason),
        _check("source_invalidated", upstream.status == "invalidated", upstream.status),
        _check("all_descendants_invalidated", downstream.status == "invalidated", downstream.status),
        _check("late_completion_rejected", not late_completion.accepted, late_completion.reason),
    ]
    return _result("upstream_invalidation", graph, checks)


def retry_idempotence() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "retryable")
    assert graph.claim("retryable", "try-1").accepted
    assert graph.fail("retryable", "try-1", "tool_timeout").accepted
    retries = _parallel(2, lambda _: graph.retry("retryable", "retry-key-1"))
    assert graph.claim("retryable", "try-2").accepted
    assert graph.complete("retryable", "try-2", "result").accepted
    retry_events = [event for event in graph.events() if event.kind == "node_requeued"]
    node = graph.node("retryable")
    checks = [
        _check("one_retry_winner", sum(item.accepted for item in retries) == 1, "retry key is consumed once"),
        _check("one_retry_event", len(retry_events) == 1, "retry is idempotent"),
        _check("new_attempt_allowed", len(node.attempt_ids) == 2, f"attempts={node.attempt_ids}"),
        _check("retry_completed", node.status == "completed", node.status),
    ]
    return _result("retry_idempotence", graph, checks)


def hash_mismatch() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "hashed")
    assert graph.claim("hashed", "h-1").accepted
    result = graph.complete("hashed", "h-1", "actual", expected="not-the-output-hash")
    node = graph.node("hashed")
    checks = [
        _check("completion_recorded", result.accepted, result.reason),
        _check("mismatch_failed", node.status == "failed", node.status),
        _check("mismatch_reason", node.failure == "hash_mismatch", str(node.failure)),
        _check("output_preserved", node.output_hash is not None, "observed output hash is retained"),
    ]
    return _result("hash_mismatch", graph, checks)


def cancellation_requeue() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "cancelable")
    assert graph.claim("cancelable", "c-1").accepted
    assert graph.cancel("cancelable").accepted
    first = graph.retry("cancelable", "requeue-key-1")
    second = graph.retry("cancelable", "requeue-key-1")
    assert graph.claim("cancelable", "c-2").accepted
    assert graph.complete("cancelable", "c-2", "result").accepted
    node = graph.node("cancelable")
    checks = [
        _check("requeue_once", first.accepted and not second.accepted, f"{first.reason}/{second.reason}"),
        _check("duplicate_key_rejected", second.reason == "duplicate_retry", second.reason),
        _check("requeued_attempt_completed", node.status == "completed", node.status),
    ]
    return _result("cancellation_requeue", graph, checks)


def isolation_visibility() -> dict[str, object]:
    graph = ResearchGraph()
    assert graph.submit("rejected").accepted
    assert graph.audit("rejected", "reject").accepted
    _approved(graph, "blocked-child", ("rejected",))
    visible = graph.visible_nodes()
    checks = [
        _check("isolated_hidden", "rejected" not in visible, str(visible)),
        _check("unrelated_projection_kept", "blocked-child" in visible, str(visible)),
        _check("isolated_dependency_blocks", not graph.can_execute("blocked-child"), "execution gate closed"),
    ]
    return _result("isolation_visibility", graph, checks)


def unreviewed_dependency() -> dict[str, object]:
    graph = ResearchGraph()
    assert graph.submit("unreviewed").accepted
    claim = graph.claim("unreviewed", "u-1")
    checks = [
        _check("unreviewed_cannot_execute", not claim.accepted, claim.reason),
        _check("correct_gate_reason", claim.reason == "unreviewed_dependency", claim.reason),
    ]
    return _result("unreviewed_dependency", graph, checks)


def replay_equivalence() -> dict[str, object]:
    graph = ResearchGraph()
    _approved(graph, "root")
    assert graph.claim("root", "r-1").accepted
    assert graph.complete("root", "r-1", "root-result").accepted
    _approved(graph, "child", ("root",))
    assert graph.claim("child", "c-1").accepted
    assert graph.complete("child", "c-1", "child-result").accepted
    replayed = ResearchGraph.replay(graph.events())
    checks = [
        _check("state_same", replayed.snapshot() == graph.snapshot(), "projection rebuilt from events"),
        _check("digest_same", replayed.state_digest() == graph.state_digest(), "canonical state digest"),
        _check("event_count_same", len(replayed.events()) == len(graph.events()), "event sequence retained"),
    ]
    return _result("event_replay", graph, checks)


def assert_invariants(graph: ResearchGraph) -> None:
    nodes = {node.id: node for node in graph.nodes()}
    for node in nodes.values():
        if node.status == "running":
            assert node.active_attempt is not None
        if node.status == "completed":
            assert node.active_attempt is None and node.audit == "approve"
        if node.visibility == "isolated":
            assert node.id not in graph.visible_nodes()
        if node.status == "invalidated":
            assert node.active_attempt is None
        assert all(dep in nodes for dep in node.deps)
    claims = [(event.payload["id"], event.payload["attempt_id"]) for event in graph.events() if event.kind == "execution_claimed"]
    assert len(claims) == len(set(claims))


def _property_trial(seed: int) -> None:
    rng = Random(seed)
    graph = ResearchGraph()
    ids = [f"p-{seed}-{index}" for index in range(5)]
    for node_id in ids:
        assert graph.submit(node_id).accepted
        assert_invariants(graph)
    order = ids[:]
    rng.shuffle(order)
    for node_id in order:
        decision = "approve" if rng.random() > 0.2 else "reject"
        assert graph.audit(node_id, decision).accepted
        assert_invariants(graph)
        if decision == "approve":
            assert graph.claim(node_id, f"a-{node_id}").accepted
            assert_invariants(graph)
            _complete_trial(graph, node_id, rng)
            assert_invariants(graph)


def _complete_trial(graph: ResearchGraph, node_id: str, rng: Random) -> None:
    if rng.random() > 0.25:
        assert graph.complete(node_id, f"a-{node_id}", f"out-{node_id}").accepted
    else:
        assert graph.fail(node_id, f"a-{node_id}", "random_failure").accepted


def property_trials(trials: int = 20) -> dict[str, object]:
    for seed in range(trials):
        _property_trial(seed)
    checked = max(0, trials)
    return {"scenario": "property_trials", "passed": True, "trials": checked, "checks": [{"name": "invariants", "passed": True, "detail": "all generated traces"}]}


def run_all() -> list[dict[str, object]]:
    cases = [
        concurrent_submissions,
        duplicate_consumption,
        audit_race,
        upstream_invalidation,
        retry_idempotence,
        hash_mismatch,
        cancellation_requeue,
        isolation_visibility,
        unreviewed_dependency,
        replay_equivalence,
    ]
    results = [case() for case in cases]
    results.append(property_trials())
    return results
