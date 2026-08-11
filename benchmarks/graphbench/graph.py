"""Small event-sourced research graph used by GraphBench.

The benchmark intentionally keeps the write model in memory. Events are plain
JSON-compatible records, so the same log can be replayed by another process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from threading import RLock
from typing import Any, Iterable

import networkx as nx


@dataclass(frozen=True)
class Event:
    seq: int
    kind: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload}


@dataclass
class OperationResult:
    accepted: bool
    reason: str
    seq: int | None = None


@dataclass
class NodeState:
    id: str
    kind: str
    deps: tuple[str, ...]
    content_hash: str
    audit: str = "pending"
    status: str = "pending_review"
    visibility: str = "default"
    active_attempt: str | None = None
    attempt_ids: list[str] = field(default_factory=list)
    retry_keys: list[str] = field(default_factory=list)
    output_hash: str | None = None
    failure: str | None = None
    invalidated_by: str | None = None
    isolation_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "deps": list(self.deps),
            "content_hash": self.content_hash,
            "audit": self.audit,
            "status": self.status,
            "visibility": self.visibility,
            "active_attempt": self.active_attempt,
            "attempt_ids": list(self.attempt_ids),
            "retry_keys": list(self.retry_keys),
            "output_hash": self.output_hash,
            "failure": self.failure,
            "invalidated_by": self.invalidated_by,
            "isolation_reason": self.isolation_reason,
        }


class ResearchGraph:
    """Thread-safe write model with deterministic event replay."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeState] = {}
        self._topology = nx.DiGraph()
        self._events: list[Event] = []
        self._lock = RLock()

    @classmethod
    def replay(cls, events: Iterable[Event | dict[str, Any]]) -> "ResearchGraph":
        graph = cls()
        for raw in events:
            event = raw if isinstance(raw, Event) else Event(**raw)
            graph._events.append(event)
            graph._apply(event)
        return graph

    def events(self) -> tuple[Event, ...]:
        with self._lock:
            return tuple(self._events)

    def event_dicts(self) -> list[dict[str, Any]]:
        return [event.as_dict() for event in self.events()]

    def node(self, node_id: str) -> NodeState | None:
        with self._lock:
            node = self._nodes.get(node_id)
            return None if node is None else NodeState(**node.as_dict())

    def nodes(self) -> list[NodeState]:
        with self._lock:
            return [NodeState(**node.as_dict()) for node in self._nodes.values()]

    def visible_nodes(self) -> list[str]:
        with self._lock:
            return sorted(node.id for node in self._nodes.values() if node.visibility == "default")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            nodes = {key: value.as_dict() for key, value in sorted(self._nodes.items())}
            edges = sorted([list(edge) for edge in self._topology.edges()])
            return {"nodes": nodes, "edges": edges}

    def state_digest(self) -> str:
        encoded = json.dumps(self.snapshot(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def submit(
        self,
        node_id: str,
        kind: str = "action",
        deps: Iterable[str] = (),
        content: str = "",
    ) -> OperationResult:
        dependencies = tuple(dict.fromkeys(deps))
        with self._lock:
            if node_id in self._nodes:
                return OperationResult(False, "duplicate_node")
            if any(dep not in self._nodes for dep in dependencies):
                return OperationResult(False, "missing_dependency")
            if not self._acyclic_with(node_id, dependencies):
                return OperationResult(False, "dependency_cycle")
            payload = {"id": node_id, "kind": kind, "deps": list(dependencies), "content_hash": digest(content)}
            return self._commit("node_submitted", payload)

    def audit(self, node_id: str, decision: str, isolate: bool = True) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return OperationResult(False, "unknown_node")
            if node.audit != "pending":
                return OperationResult(False, "audit_already_recorded")
            if decision not in {"approve", "reject"}:
                return OperationResult(False, "invalid_audit_decision")
            payload = {"id": node_id, "decision": decision, "isolate": isolate}
            return self._commit("audit_recorded", payload)

    def claim(self, node_id: str, attempt_id: str) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            reason = self._claim_failure(node, attempt_id)
            if reason:
                return OperationResult(False, reason)
            payload = {"id": node_id, "attempt_id": attempt_id}
            return self._commit("execution_claimed", payload)

    def complete(self, node_id: str, attempt_id: str, output: str, expected: str | None = None) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return OperationResult(False, "unknown_node")
            if node.status != "running" or node.active_attempt != attempt_id:
                return OperationResult(False, "stale_attempt")
            payload = {"id": node_id, "attempt_id": attempt_id, "output_hash": digest(output), "expected_hash": expected}
            return self._commit("execution_completed", payload)

    def fail(self, node_id: str, attempt_id: str, reason: str) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return OperationResult(False, "unknown_node")
            if node.status != "running" or node.active_attempt != attempt_id:
                return OperationResult(False, "stale_attempt")
            return self._commit("execution_failed", {"id": node_id, "attempt_id": attempt_id, "reason": reason})

    def retry(self, node_id: str, retry_key: str) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return OperationResult(False, "unknown_node")
            if retry_key in node.retry_keys:
                return OperationResult(False, "duplicate_retry")
            if node.status not in {"failed", "cancelled"}:
                return OperationResult(False, "not_retryable")
            return self._commit("node_requeued", {"id": node_id, "retry_key": retry_key})

    def cancel(self, node_id: str) -> OperationResult:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return OperationResult(False, "unknown_node")
            if node.status not in {"approved", "running"}:
                return OperationResult(False, "not_cancellable")
            return self._commit("node_cancelled", {"id": node_id})

    def invalidate(self, node_id: str, reason: str) -> OperationResult:
        with self._lock:
            if node_id not in self._nodes:
                return OperationResult(False, "unknown_node")
            affected = sorted({node_id, *self._descendants(node_id)})
            payload = {"id": node_id, "affected": affected, "reason": reason}
            return self._commit("node_invalidated", payload)

    def isolate(self, node_id: str, reason: str) -> OperationResult:
        with self._lock:
            if node_id not in self._nodes:
                return OperationResult(False, "unknown_node")
            node = self._nodes[node_id]
            if node.visibility == "isolated":
                return OperationResult(False, "already_isolated")
            return self._commit("record_isolated", {"id": node_id, "reason": reason})

    def can_execute(self, node_id: str) -> bool:
        with self._lock:
            node = self._nodes.get(node_id)
            return node is not None and not self._claim_failure(node, "probe")

    def _claim_failure(self, node: NodeState | None, attempt_id: str) -> str | None:
        if node is None:
            return "unknown_node"
        if node.visibility == "isolated" or node.status == "isolated":
            return "isolated_record"
        if node.audit != "approve":
            return "unreviewed_dependency"
        if node.status == "running":
            return "already_running"
        if node.status == "completed":
            return "already_completed"
        if node.status != "approved":
            return "not_ready"
        if attempt_id in node.attempt_ids:
            return "duplicate_attempt"
        if any(self._nodes[dep].status != "completed" for dep in node.deps):
            return "dependency_not_completed"
        return None

    def _descendants(self, node_id: str) -> set[str]:
        return set(nx.descendants(self._topology, node_id))

    def _acyclic_with(self, node_id: str, deps: tuple[str, ...]) -> bool:
        topology = self._topology.copy()
        topology.add_node(node_id)
        topology.add_edges_from((dep, node_id) for dep in deps)
        return nx.is_directed_acyclic_graph(topology)

    def _commit(self, kind: str, payload: dict[str, Any]) -> OperationResult:
        event = Event(len(self._events) + 1, kind, json.loads(json.dumps(payload, ensure_ascii=False)))
        self._events.append(event)
        self._apply(event)
        return OperationResult(True, "accepted", event.seq)

    def _apply(self, event: Event) -> None:
        handlers = {
            "node_submitted": self._apply_submission,
            "audit_recorded": self._apply_audit,
            "execution_claimed": self._apply_claim,
            "execution_completed": self._apply_complete,
            "execution_failed": self._apply_failure,
            "node_requeued": self._apply_requeue,
            "node_cancelled": self._apply_cancel,
            "node_invalidated": self._apply_invalidation,
            "record_isolated": self._apply_isolation,
        }
        handlers[event.kind](event.payload)

    def _apply_submission(self, payload: dict[str, Any]) -> None:
        self._topology.add_node(payload["id"])
        self._topology.add_edges_from((dep, payload["id"]) for dep in payload["deps"])
        self._nodes[payload["id"]] = NodeState(
            payload["id"], payload["kind"], tuple(payload["deps"]), payload["content_hash"]
        )

    def _apply_audit(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.audit = payload["decision"]
        node.status = "approved" if node.audit == "approve" else "rejected"
        if node.audit == "reject" and payload["isolate"]:
            node.status = "isolated"
            node.visibility = "isolated"
            node.isolation_reason = "audit_rejected"

    def _apply_claim(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.status = "running"
        node.active_attempt = payload["attempt_id"]
        node.attempt_ids.append(payload["attempt_id"])

    def _apply_complete(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.active_attempt = None
        node.output_hash = payload["output_hash"]
        expected = payload["expected_hash"]
        if expected is not None and expected != payload["output_hash"]:
            node.status = "failed"
            node.failure = "hash_mismatch"
            return
        node.status = "completed"
        node.failure = None

    def _apply_failure(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.status = "failed"
        node.failure = payload["reason"]
        node.active_attempt = None

    def _apply_requeue(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.retry_keys.append(payload["retry_key"])
        node.status = "approved"
        node.failure = None

    def _apply_cancel(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.status = "cancelled"
        node.active_attempt = None

    def _apply_invalidation(self, payload: dict[str, Any]) -> None:
        for node_id in payload["affected"]:
            node = self._nodes[node_id]
            node.status = "invalidated"
            node.invalidated_by = payload["id"]
            node.active_attempt = None

    def _apply_isolation(self, payload: dict[str, Any]) -> None:
        node = self._nodes[payload["id"]]
        node.visibility = "isolated"
        node.status = "isolated"
        node.isolation_reason = payload["reason"]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
