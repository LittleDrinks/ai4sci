from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import db
from .identity import content_sha, uid


LEASE_SECONDS = 45
RUNTIME_STALE_SECONDS = 30
VISIBLE_NODE_STATES = ("admitted", "pending_review")
SUBMISSION_KINDS = {"plan": "action", "research": "result", "html_report": "report"}


class StateConflict(Exception):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat()


def deadline(seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()


def _event(connection: sqlite3.Connection, project_id: str | None, kind: str,
           actor: dict, entity: tuple[str, str], payload: dict) -> None:
    sql = """INSERT INTO events(project_id,kind,actor_kind,actor_id,entity_type,entity_id,payload_json,created_at)
             VALUES(?,?,?,?,?,?,?,?)"""
    connection.execute(sql, (project_id, kind, actor["kind"], actor["id"], *entity,
                             json.dumps(payload), now()))


def event(project_id: str | None, kind: str, actor: dict,
          entity: tuple[str, str], payload: dict) -> None:
    with db.connect() as connection:
        _event(connection, project_id, kind, actor, entity, payload)


def project(project_id: str) -> dict[str, Any] | None:
    return db.row("SELECT * FROM projects WHERE id=?", (project_id,))


def projects() -> list[dict[str, Any]]:
    return db.rows("SELECT * FROM projects ORDER BY created_at")


def create_project(title: str, question: str, actor: dict) -> dict[str, Any]:
    project_id = uid("project", {"title": title, "question": question})
    root_id = uid("node", {"project": project_id, "kind": "question", "question": question})
    with db.connect() as connection:
        _insert_project(connection, project_id, title, question)
        _insert_root(connection, root_id, project_id, title, question, actor)
        _event(connection, project_id, "project_created", actor, ("project", project_id), {"root_id": root_id})
    return {"id": project_id, "root_id": root_id}


def _insert_project(connection: sqlite3.Connection, project_id: str,
                    title: str, question: str) -> None:
    sql = "INSERT OR IGNORE INTO projects(id,title,question,created_at) VALUES(?,?,?,?)"
    connection.execute(sql, (project_id, title, question, now()))


def _insert_root(connection: sqlite3.Connection, node_id: str, project_id: str,
                 title: str, question: str, actor: dict) -> None:
    sql = """INSERT OR IGNORE INTO nodes(id,project_id,kind,title,summary,content_json,status,audit,
             actor_kind,actor_id,source_job_id,created_at,admitted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    values = (node_id, project_id, "question", title, question, json.dumps({"question": question}),
              "admitted", "approve", actor["kind"], actor["id"], None, now(), now())
    connection.execute(sql, values)


def node(node_id: str) -> dict[str, Any] | None:
    value = db.row("SELECT * FROM nodes WHERE id=?", (node_id,))
    return decode_node(value) if value else None


def decode_node(value: dict[str, Any]) -> dict[str, Any]:
    value["content"] = db.decode(value.pop("content_json"), {})
    value["created_by"] = {"kind": value.pop("actor_kind"), "id": value.pop("actor_id")}
    return value


def project_nodes(project_id: str) -> list[dict[str, Any]]:
    marks = ",".join("?" for _ in VISIBLE_NODE_STATES)
    sql = f"SELECT * FROM nodes WHERE project_id=? AND status IN ({marks}) ORDER BY created_at"
    return [decode_node(value) for value in db.rows(sql, (project_id, *VISIBLE_NODE_STATES))]


def admitted_nodes(project_id: str) -> list[dict[str, Any]]:
    sql = "SELECT * FROM nodes WHERE project_id=? AND status='admitted' AND audit='approve' ORDER BY created_at"
    return [decode_node(value) for value in db.rows(sql, (project_id,))]


def review_nodes(project_id: str) -> list[dict[str, Any]]:
    values = db.rows("SELECT * FROM nodes WHERE project_id=? ORDER BY created_at", (project_id,))
    return [decode_node(value) for value in values]


def project_edges(project_id: str, admitted_only: bool = False) -> list[dict[str, Any]]:
    states = ("admitted",) if admitted_only else VISIBLE_NODE_STATES
    marks = ",".join("?" for _ in states)
    sql = f"""SELECT e.source,e.target,e.relation FROM edges e
              JOIN nodes s ON s.id=e.source JOIN nodes t ON t.id=e.target
              WHERE e.project_id=? AND s.status IN ({marks}) AND t.status IN ({marks})"""
    return db.rows(sql, (project_id, *states, *states))


def dependencies_ready(project_id: str, dependencies: list[str]) -> bool:
    with db.connect() as connection:
        return _dependencies_ready(connection, project_id, dependencies)


def _dependencies_ready(connection: sqlite3.Connection, project_id: str,
                        dependencies: list[str]) -> bool:
    if not dependencies:
        return True
    marks = ",".join("?" for _ in dependencies)
    sql = f"SELECT id,audit,status,project_id FROM nodes WHERE id IN ({marks})"
    values = connection.execute(sql, dependencies).fetchall()
    return len(values) == len(dependencies) and all(
        row["audit"] == "approve" and row["status"] == "admitted" and row["project_id"] == project_id
        for row in values
    )


def insert_node(value: dict[str, Any], actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        result = _insert_candidate(connection, value, actor)
        connection.commit()
    return result


def node_identity(value: dict[str, Any]) -> str:
    keys = ("project_id", "kind", "title", "summary", "content", "dependencies")
    return uid("node", {key: value.get(key) for key in keys})


def _insert_candidate(connection: sqlite3.Connection, value: dict,
                      actor: dict, revision: int = 0) -> dict[str, Any]:
    node_id = node_identity(value)
    current = connection.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
    if current and current["status"] not in {"rejected", "revision_requested"}:
        return decode_node(dict(current))
    _write_candidate(connection, node_id, value, actor, bool(current))
    _write_edges(connection, node_id, value)
    _event(connection, value["project_id"], "node_submitted", actor, ("node", node_id),
           {"kind": value["kind"], "revision": revision})
    return decode_node(dict(connection.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()))


def _write_candidate(connection: sqlite3.Connection, node_id: str, value: dict,
                     actor: dict, exists: bool) -> None:
    if exists:
        sql = """UPDATE nodes SET status='pending_review',audit='pending',actor_kind=?,actor_id=?,
                 source_job_id=?,created_at=?,admitted_at=NULL WHERE id=?"""
        connection.execute(sql, (actor["kind"], actor["id"], value.get("source_job_id"), now(), node_id))
        return
    sql = """INSERT INTO nodes(id,project_id,kind,title,summary,content_json,status,audit,actor_kind,
             actor_id,source_job_id,created_at,admitted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params = (node_id, value["project_id"], value["kind"], value["title"], value["summary"],
              json.dumps(value.get("content", {})), "pending_review", "pending", actor["kind"],
              actor["id"], value.get("source_job_id"), now(), None)
    connection.execute(sql, params)


def _write_edges(connection: sqlite3.Connection, node_id: str, value: dict) -> None:
    for source in value.get("dependencies", []):
        connection.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)",
                           (value["project_id"], source, node_id, "depends_on"))


def review_node(node_id: str, decision: str, feedback: str, actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM nodes WHERE id=? AND audit='pending'", (node_id,)).fetchone()
        if not row:
            raise StateConflict("node is not pending review")
        _cancel_candidate_audits(connection, node_id)
        job_row = _review_node_row(connection, row, decision, feedback, actor)
        connection.commit()
    return {"node": node(node_id), "job": job(job_row["id"]) if job_row else None}


def _cancel_candidate_audits(connection: sqlite3.Connection, node_id: str) -> None:
    sql = "SELECT * FROM jobs WHERE kind='audit' AND subject_id=? AND status IN ('queued','running')"
    for row in connection.execute(sql, (node_id,)).fetchall():
        connection.execute("UPDATE jobs SET status='cancelled',lease_expires_at=NULL WHERE id=?", (row["id"],))
        _schedule_cleanup(connection, row, "delete_job_workspace")


def _review_node_row(connection: sqlite3.Connection, row: sqlite3.Row, decision: str,
                     feedback: str, actor: dict) -> sqlite3.Row | None:
    job_row = _current_job(connection, row["source_job_id"], "output_node_id", row["id"])
    if decision in {"revise", "restart"} and not job_row:
        raise StateConflict("node has no active agent session")
    status = "admitted" if decision == "approve" else "rejected" if decision == "reject" else "revision_requested"
    admitted_at = now() if decision == "approve" else None
    connection.execute("UPDATE nodes SET audit=?,status=?,admitted_at=? WHERE id=?",
                       (decision, status, admitted_at, row["id"]))
    _event(connection, row["project_id"], "node_reviewed", actor, ("node", row["id"]),
           {"decision": decision, "feedback": feedback})
    _advance_after_node_review(connection, job_row, decision, feedback, actor)
    _schedule_action_execution(connection, row, decision, actor)
    return job_row


def _schedule_action_execution(connection: sqlite3.Connection, row: sqlite3.Row,
                               decision: str, actor: dict) -> None:
    if decision != "approve" or row["kind"] != "action":
        return
    executor = _capable_agent(connection, "research")
    if not executor:
        raise StateConflict("no research agent is registered")
    content = db.decode(row["content_json"], {})
    value = {"project_id": row["project_id"], "agent_id": executor["id"], "kind": "research",
             "subject_id": row["id"], "prompt": content.get("prompt", row["summary"])}
    if not _job_for_subject(connection, value):
        _insert_job(connection, value, actor)


def _advance_after_node_review(connection: sqlite3.Connection, job_row: sqlite3.Row | None,
                               decision: str, feedback: str, actor: dict) -> None:
    if not job_row:
        return
    if decision == "approve":
        _finalize_if_ready(connection, job_row["id"], actor)
    elif decision == "reject":
        _reject_job(connection, job_row, feedback, actor)
    else:
        _reject_current_artifact(connection, job_row, actor)
        _queue_revision(connection, job_row, decision, "node", feedback, actor)


def _current_job(connection: sqlite3.Connection, job_id: str | None,
                 field: str, entity_id: str) -> sqlite3.Row | None:
    if not job_id:
        return None
    sql = f"SELECT * FROM jobs WHERE id=? AND status='awaiting_review' AND {field}=?"
    return connection.execute(sql, (job_id, entity_id)).fetchone()


def runtime(runtime_id: str) -> dict[str, Any] | None:
    value = db.row("SELECT * FROM runtimes WHERE id=?", (runtime_id,))
    return decode_json_field(value, "capabilities_json", "capabilities") if value else None


def register_runtime(value: dict[str, Any]) -> dict[str, Any]:
    runtime_id = uid("runtime", {"name": value["name"], "sdk": value["sdk"]})
    timestamp = now()
    sql = """INSERT INTO runtimes(id,name,sdk,version,capabilities_json,status,last_seen,created_at)
             VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET sdk=excluded.sdk,
             version=excluded.version,capabilities_json=excluded.capabilities_json,
             status='online',last_seen=excluded.last_seen"""
    params = (runtime_id, value["name"], value["sdk"], value["version"],
              json.dumps(value["capabilities"]), "online", timestamp, timestamp)
    db.execute(sql, params)
    event(None, "runtime_registered", {"kind": "runtime", "id": runtime_id},
          ("runtime", runtime_id), {"sdk": value["sdk"]})
    return runtime(runtime_id) or {}


def heartbeat(runtime_id: str, status: str) -> dict[str, Any]:
    previous = runtime(runtime_id)
    if not previous:
        raise StateConflict("unknown runtime")
    db.execute("UPDATE runtimes SET status=?,last_seen=? WHERE id=?", (status, now(), runtime_id))
    if previous["status"] != status:
        actor = {"kind": "runtime", "id": runtime_id}
        event(None, "runtime_status_changed", actor, ("runtime", runtime_id), {"status": status})
    return runtime(runtime_id) or {}


def runtimes() -> list[dict[str, Any]]:
    values = db.rows("SELECT * FROM runtimes ORDER BY created_at")
    return [decode_json_field(value, "capabilities_json", "capabilities") for value in values]


def agent(agent_id: str) -> dict[str, Any] | None:
    values = [value for value in agents() if value["id"] == agent_id]
    return values[0] if values else None


def agents() -> list[dict[str, Any]]:
    sql = """SELECT a.*, CASE WHEN r.status!='online' THEN r.status
             WHEN EXISTS(SELECT 1 FROM jobs j WHERE j.agent_id=a.id AND j.status='running') THEN 'running'
             WHEN EXISTS(SELECT 1 FROM jobs j WHERE j.agent_id=a.id AND j.status='queued') THEN 'queued'
             ELSE 'idle' END AS status FROM agents a JOIN runtimes r ON r.id=a.runtime_id ORDER BY a.created_at"""
    return [decode_json_field(value, "capabilities_json", "capabilities") for value in db.rows(sql)]


def create_agent(value: dict[str, Any], actor: dict) -> dict[str, Any]:
    agent_id = uid("agent", {"name": value["name"], "runtime_id": value["runtime_id"]})
    sql = """INSERT OR REPLACE INTO agents(id,name,runtime_id,model,instructions,capabilities_json,created_at)
             VALUES(?,?,?,?,?,?,?)"""
    params = (agent_id, value["name"], value["runtime_id"], value["model"], value["instructions"],
              json.dumps(value["capabilities"]), now())
    db.execute(sql, params)
    event(None, "agent_registered", actor, ("agent", agent_id), {"runtime_id": value["runtime_id"]})
    return agent(agent_id) or {}


def create_job(value: dict[str, Any], actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        result = _insert_job(connection, value, actor)
        connection.commit()
    return result


def _job_for_subject(connection: sqlite3.Connection, value: dict) -> sqlite3.Row | None:
    sql = "SELECT * FROM jobs WHERE project_id=? AND kind=? AND subject_id=? ORDER BY created_at LIMIT 1"
    return connection.execute(sql, (value["project_id"], value["kind"], value.get("subject_id"))).fetchone()


def _insert_job(connection: sqlite3.Connection, value: dict, actor: dict) -> dict[str, Any]:
    timestamp = now()
    job_id = uid("job", {**value, "requested_at": timestamp})
    sql = """INSERT INTO jobs(id,project_id,agent_id,kind,subject_id,prompt,status,revision,
             created_at) VALUES(?,?,?,?,?,?,?,0,?)"""
    params = (job_id, value["project_id"], value["agent_id"], value["kind"],
              value.get("subject_id"), value["prompt"], "queued", timestamp)
    connection.execute(sql, params)
    _event(connection, value["project_id"], "job_queued", actor, ("job", job_id),
           {"agent_id": value["agent_id"], "kind": value["kind"]})
    return dict(connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())


def job(job_id: str) -> dict[str, Any] | None:
    return db.row("SELECT * FROM jobs WHERE id=?", (job_id,))


def project_jobs(project_id: str) -> list[dict[str, Any]]:
    return db.rows("SELECT * FROM jobs WHERE project_id=? ORDER BY created_at DESC", (project_id,))


def claim_job(runtime_id: str) -> dict[str, Any] | None:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _sweep_connection(connection)
        row = _claimable(connection, runtime_id)
        if row:
            _mark_claimed(connection, row, runtime_id)
        connection.commit()
    return task_context(row["id"]) if row else None


def _claimable(connection: sqlite3.Connection, runtime_id: str) -> sqlite3.Row | None:
    runtime_row = connection.execute("SELECT * FROM runtimes WHERE id=? AND status='online'", (runtime_id,)).fetchone()
    if not runtime_row:
        return None
    sql = """SELECT jobs.*,agents.capabilities_json FROM jobs JOIN agents ON agents.id=jobs.agent_id
             WHERE jobs.status='queued' AND agents.runtime_id=?
             AND (jobs.runtime_id IS NULL OR jobs.runtime_id=?) ORDER BY jobs.created_at"""
    runtime_capabilities = set(json.loads(runtime_row["capabilities_json"]))
    rows = connection.execute(sql, (runtime_id, runtime_id)).fetchall()
    return next((row for row in rows if row["kind"] in runtime_capabilities
                 and row["kind"] in json.loads(row["capabilities_json"])), None)


def _mark_claimed(connection: sqlite3.Connection, row: sqlite3.Row, runtime_id: str) -> None:
    attempt_id = row["attempt_id"] or uid("attempt", {"job": row["id"], "at": now()})
    timestamp, expires = now(), deadline(LEASE_SECONDS)
    sql = """UPDATE jobs SET status='running',attempt_id=?,runtime_id=?,started_at=?,heartbeat_at=?,
             lease_expires_at=? WHERE id=?"""
    connection.execute(sql, (attempt_id, runtime_id, timestamp, timestamp, expires, row["id"]))
    actor = {"kind": "runtime", "id": runtime_id}
    _event(connection, row["project_id"], "job_claimed", actor, ("job", row["id"]),
           {"attempt_id": attempt_id, "revision": row["revision"]})


def task_context(job_id: str) -> dict[str, Any]:
    value = job(job_id) or {}
    project_value = project(value["project_id"]) or {}
    subject = node(value["subject_id"]) if value.get("subject_id") else None
    context = relevant_context(value)
    return {"id": job_id, "attempt_id": value["attempt_id"], "runtime_id": value["runtime_id"],
            "job": value, "agent": agent(value["agent_id"]), "project": project_value,
            "subject": subject, "context": context}


def relevant_context(job_value: dict[str, Any]) -> dict[str, Any]:
    direction = "descendants" if job_value["kind"] == "html_report" else "ancestors"
    ids = related_admitted_ids(job_value["project_id"], job_value.get("subject_id"), direction)
    edges = edges_by_id(job_value["project_id"], ids)
    if job_value["kind"] == "audit":
        edges += subject_dependency_edges(job_value["project_id"], job_value.get("subject_id"), ids)
    return {"nodes": nodes_by_id(ids), "edges": edges}


def related_admitted_ids(project_id: str, subject_id: str | None, direction: str) -> list[str]:
    if not subject_id:
        return []
    source, target = ("source", "target") if direction == "descendants" else ("target", "source")
    sql = f"""WITH RECURSIVE related(id) AS (SELECT ? UNION SELECT e.{target} FROM edges e
              JOIN related r ON e.{source}=r.id WHERE e.project_id=?)
              SELECT n.id FROM related r JOIN nodes n ON n.id=r.id
              WHERE n.project_id=? AND n.status='admitted' AND n.audit='approve'"""
    return [row["id"] for row in db.rows(sql, (subject_id, project_id, project_id))]


def nodes_by_id(ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    return [decode_node(value) for value in db.rows(f"SELECT * FROM nodes WHERE id IN ({marks})", ids)]


def edges_by_id(project_id: str, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    marks = ",".join("?" for _ in ids)
    sql = f"SELECT source,target,relation FROM edges WHERE project_id=? AND source IN ({marks}) AND target IN ({marks})"
    return db.rows(sql, (project_id, *ids, *ids))


def subject_dependency_edges(project_id: str, subject_id: str | None,
                             admitted_ids: list[str]) -> list[dict[str, Any]]:
    if not subject_id or subject_id in admitted_ids or not admitted_ids:
        return []
    marks = ",".join("?" for _ in admitted_ids)
    sql = f"SELECT source,target,relation FROM edges WHERE project_id=? AND target=? AND source IN ({marks})"
    return db.rows(sql, (project_id, subject_id, *admitted_ids))


def renew_lease(job_id: str, runtime_id: str, attempt_id: str) -> dict[str, str]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_live_attempt(connection, job_id, runtime_id, attempt_id)
        timestamp, expires = now(), deadline(LEASE_SECONDS)
        connection.execute("UPDATE jobs SET heartbeat_at=?,lease_expires_at=? WHERE id=?",
                           (timestamp, expires, row["id"]))
        connection.execute("UPDATE runtimes SET status='online',last_seen=? WHERE id=?",
                           (timestamp, runtime_id))
        connection.commit()
    return {"heartbeat_at": timestamp, "lease_expires_at": expires}


def record_task_event(job_id: str, value: dict[str, Any]) -> None:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_live_attempt(connection, job_id, value["runtime_id"], value["attempt_id"])
        actor = {"kind": "agent", "id": row["agent_id"]}
        payload = {"message": value["message"], **value.get("payload", {}),
                   "attempt_id": value["attempt_id"], "revision": row["revision"]}
        _event(connection, row["project_id"], value["kind"], actor, ("job", job_id), payload)
        connection.commit()


def complete_task(job_id: str, runtime_id: str, attempt_id: str, result_text: str,
                  candidate: dict, html: str | None) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_live_attempt(connection, job_id, runtime_id, attempt_id)
        if row["kind"] == "audit":
            raise StateConflict("audit jobs require an audit result")
        output = _complete_candidate(connection, row, candidate)
        artifact_value = _complete_artifact(connection, row, output, html)
        _mark_awaiting_review(connection, row, result_text, output, artifact_value)
        audit_row = _queue_audit(connection, row, output)
        actor = {"kind": "agent", "id": row["agent_id"]}
        _event(connection, row["project_id"], "job_output_submitted", actor, ("job", job_id),
               {"attempt_id": attempt_id, "revision": row["revision"]})
        _finalize_if_ready(connection, job_id, actor)
        connection.commit()
    return {"job": job(job_id), "node": node(output["id"]),
            "artifact": artifact(artifact_value["id"]) if artifact_value else None,
            "audit_job": job(audit_row["id"]) if audit_row else None}


def _queue_audit(connection: sqlite3.Connection, producer: sqlite3.Row,
                 output: dict) -> dict[str, Any] | None:
    if output["audit"] != "pending" or output["source_job_id"] != producer["id"]:
        return None
    auditor = _audit_agent(connection, producer["agent_id"])
    if not auditor:
        return None
    value = {"project_id": producer["project_id"], "agent_id": auditor["id"], "kind": "audit",
             "subject_id": output["id"], "prompt": _audit_prompt(producer, output["id"])}
    actor = {"kind": "system", "id": "audit-dispatch"}
    return _insert_job(connection, value, actor)


def _audit_agent(connection: sqlite3.Connection, producer_id: str) -> dict[str, Any] | None:
    return _capable_agent(connection, "audit", producer_id)


def _capable_agent(connection: sqlite3.Connection, capability: str,
                   excluded_id: str = "") -> dict[str, Any] | None:
    sql = """SELECT a.*,r.capabilities_json runtime_capabilities FROM agents a
             JOIN runtimes r ON r.id=a.runtime_id WHERE a.id!=? AND r.status='online' ORDER BY a.created_at"""
    for row in connection.execute(sql, (excluded_id,)).fetchall():
        agent_caps = db.decode(row["capabilities_json"], [])
        runtime_caps = db.decode(row["runtime_capabilities"], [])
        if capability in agent_caps and capability in runtime_caps:
            return dict(row)
    return None


def _audit_prompt(producer: sqlite3.Row, node_id: str) -> str:
    return (f"Audit pending node {node_id}.\nProducer job: {producer['id']}\n"
            f"Producer revision: {producer['revision']}\n"
            "Assess only the submitted node against its admitted dependencies.")


def complete_audit_task(job_id: str, runtime_id: str, attempt_id: str,
                        audit: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_live_attempt(connection, job_id, runtime_id, attempt_id)
        candidate, producer = _audit_target(connection, row)
        _validate_audit(audit)
        actor = {"kind": "agent", "id": row["agent_id"]}
        _finish_audit_job(connection, row, producer, audit, actor)
        _review_node_row(connection, candidate, audit["decision"], audit["feedback"], actor)
        _schedule_cleanup(connection, row, "delete_job_workspace")
        connection.commit()
    return {"job": job(job_id), "node": node(candidate["id"]),
            "producer_job": job(producer["id"]), "decision": audit["decision"]}


def _audit_target(connection: sqlite3.Connection,
                  audit_job: sqlite3.Row) -> tuple[sqlite3.Row, sqlite3.Row]:
    if audit_job["kind"] != "audit":
        raise StateConflict("job is not an audit")
    candidate = connection.execute(
        "SELECT * FROM nodes WHERE id=? AND audit='pending'", (audit_job["subject_id"],)
    ).fetchone()
    producer = _candidate_producer(connection, candidate)
    if not candidate or not producer:
        raise StateConflict("audit subject is not a current pending output")
    if audit_job["agent_id"] == producer["agent_id"]:
        raise StateConflict("producer cannot audit its own output")
    return candidate, producer


def _candidate_producer(connection: sqlite3.Connection,
                        candidate: sqlite3.Row | None) -> sqlite3.Row | None:
    if not candidate or not candidate["source_job_id"]:
        return None
    sql = """SELECT * FROM jobs WHERE id=? AND output_node_id=?
             AND status='awaiting_review'"""
    return connection.execute(sql, (candidate["source_job_id"], candidate["id"])).fetchone()


def _validate_audit(audit: dict) -> None:
    if audit["decision"] != "approve" and not audit["feedback"].strip():
        raise StateConflict("audit feedback is required")


def _finish_audit_job(connection: sqlite3.Connection, row: sqlite3.Row,
                      producer: sqlite3.Row, audit: dict, actor: dict) -> None:
    result = json.dumps(audit, ensure_ascii=False, sort_keys=True)
    sql = """UPDATE jobs SET status='completed',result_text=?,completed_at=?,heartbeat_at=NULL,
             lease_expires_at=NULL,error=NULL WHERE id=?"""
    connection.execute(sql, (result, now(), row["id"]))
    payload = {**audit, "producer_job_id": producer["id"], "producer_revision": producer["revision"]}
    _event(connection, row["project_id"], "audit_completed", actor, ("job", row["id"]), payload)


def _complete_candidate(connection: sqlite3.Connection, row: sqlite3.Row,
                        candidate: dict) -> dict[str, Any]:
    expected = SUBMISSION_KINDS.get(row["kind"])
    if expected and candidate["kind"] != expected:
        raise StateConflict(f"{row['kind']} jobs require kind={expected} submissions")
    if not _dependencies_ready(connection, row["project_id"], candidate["dependencies"]):
        raise StateConflict("dependencies must be admitted nodes")
    actor = {"kind": "agent", "id": row["agent_id"]}
    existing_id = row["output_node_id"] if row["review_scope"] == "artifact" else None
    if existing_id and node_identity(candidate) != existing_id:
        raise StateConflict("artifact revision cannot change the admitted node")
    return decode_node(dict(connection.execute("SELECT * FROM nodes WHERE id=?", (existing_id,)).fetchone())) \
        if existing_id else _insert_candidate(connection, candidate, actor, row["revision"])


def _complete_artifact(connection: sqlite3.Connection, row: sqlite3.Row,
                       output: dict, html: str | None) -> dict[str, Any] | None:
    if not html:
        return None
    digest = content_sha(html)
    artifact_id = uid("artifact", {"job": row["id"], "attempt": row["attempt_id"],
                                    "revision": row["revision"], "sha256": digest})
    path = artifact_path(artifact_id)
    path.write_text(html, encoding="utf-8")
    sql = """INSERT INTO artifacts(id,project_id,job_id,node_id,title,kind,status,content_type,path,
             sha256,agent_id,created_at,reviewed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL)"""
    values = (artifact_id, row["project_id"], row["id"], output["id"], output["title"],
              "html_report", "pending_review", "text/html", str(path), digest, row["agent_id"], now())
    connection.execute(sql, values)
    actor = {"kind": "agent", "id": row["agent_id"]}
    _event(connection, row["project_id"], "artifact_submitted", actor, ("artifact", artifact_id),
           {"node_id": output["id"], "revision": row["revision"]})
    return dict(connection.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone())


def _mark_awaiting_review(connection: sqlite3.Connection, row: sqlite3.Row,
                          result_text: str, output: dict, artifact_value: dict | None) -> None:
    sql = """UPDATE jobs SET status='awaiting_review',result_text=?,output_node_id=?,
             output_artifact_id=?,heartbeat_at=NULL,lease_expires_at=NULL,error=NULL WHERE id=?"""
    connection.execute(sql, (result_text, output["id"],
                             artifact_value["id"] if artifact_value else None, row["id"]))


def fail_job(job_id: str, runtime_id: str, attempt_id: str, error: str) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _require_live_attempt(connection, job_id, runtime_id, attempt_id)
        sql = """UPDATE jobs SET status='failed',error=?,completed_at=?,heartbeat_at=NULL,
                 lease_expires_at=NULL WHERE id=?"""
        connection.execute(sql, (error, now(), job_id))
        actor = {"kind": "agent", "id": row["agent_id"]}
        _event(connection, row["project_id"], "job_failed", actor, ("job", job_id),
               {"message": error, "attempt_id": attempt_id, "revision": row["revision"]})
        connection.commit()
    return job(job_id) or {}


def retry_job(job_id: str, actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM jobs WHERE id=? AND status='failed'", (job_id,)).fetchone()
        if not row:
            raise StateConflict("only failed jobs can be retried")
        _schedule_cleanup(connection, row, "delete_attempt_workspace")
        sql = """UPDATE jobs SET status='queued',attempt_id=NULL,runtime_id=NULL,review_mode='restart',
                 error=NULL,started_at=NULL,heartbeat_at=NULL,lease_expires_at=NULL,completed_at=NULL WHERE id=?"""
        connection.execute(sql, (job_id,))
        _event(connection, row["project_id"], "job_retried", actor, ("job", job_id), {})
        connection.commit()
    return job(job_id) or {}


def _require_live_attempt(connection: sqlite3.Connection, job_id: str,
                          runtime_id: str, attempt_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    valid = row and row["status"] == "running" and row["runtime_id"] == runtime_id
    valid = valid and row["attempt_id"] == attempt_id and row["lease_expires_at"] > now()
    if not valid:
        raise StateConflict("stale task attempt")
    return row


def artifact_path(artifact_id: str) -> Path:
    path = db.DB_PATH.parent / "artifacts" / artifact_id.replace(":", "-") / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def artifact(artifact_id: str) -> dict[str, Any] | None:
    return db.row("SELECT * FROM artifacts WHERE id=?", (artifact_id,))


def project_artifacts(project_id: str) -> list[dict[str, Any]]:
    return db.rows("SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at DESC", (project_id,))


def review_artifact(artifact_id: str, decision: str, feedback: str,
                    actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM artifacts WHERE id=? AND status='pending_review'", (artifact_id,)).fetchone()
        if not row:
            raise StateConflict("artifact is not pending review")
        job_row = _current_job(connection, row["job_id"], "output_artifact_id", artifact_id)
        if not job_row:
            raise StateConflict("artifact is not the current job output")
        _review_artifact_row(connection, row, job_row, decision, feedback, actor)
        connection.commit()
    return {"artifact": artifact(artifact_id), "job": job(job_row["id"])}


def _review_artifact_row(connection: sqlite3.Connection, row: sqlite3.Row, job_row: sqlite3.Row,
                         decision: str, feedback: str, actor: dict) -> None:
    if decision == "approve" and not _node_approved(connection, row["node_id"]):
        raise StateConflict("approve the linked node before publishing its artifact")
    status = "published" if decision == "approve" else "rejected"
    connection.execute("UPDATE artifacts SET status=?,reviewed_at=? WHERE id=?", (status, now(), row["id"]))
    _event(connection, row["project_id"], "artifact_reviewed", actor, ("artifact", row["id"]),
           {"decision": decision, "feedback": feedback})
    if decision == "approve":
        _finalize_if_ready(connection, job_row["id"], actor)
    elif decision == "reject":
        _reject_job(connection, job_row, feedback, actor)
    else:
        _queue_revision(connection, job_row, decision, "artifact", feedback, actor)


def _node_approved(connection: sqlite3.Connection, node_id: str) -> bool:
    row = connection.execute("SELECT 1 FROM nodes WHERE id=? AND status='admitted' AND audit='approve'", (node_id,)).fetchone()
    return bool(row)


def _queue_revision(connection: sqlite3.Connection, row: sqlite3.Row, decision: str,
                    scope: str, feedback: str, actor: dict) -> None:
    mode = "continue" if decision == "revise" else "restart"
    if mode == "restart":
        _schedule_cleanup(connection, row, "delete_attempt_workspace")
    attempt_id = row["attempt_id"] if mode == "continue" else None
    runtime_id = row["runtime_id"] if mode == "continue" else None
    output_node_id = row["output_node_id"] if scope == "artifact" else None
    sql = """UPDATE jobs SET status='queued',attempt_id=?,runtime_id=?,revision=revision+1,
             review_mode=?,review_scope=?,review_feedback=?,result_text=NULL,output_node_id=?,
             output_artifact_id=NULL,error=NULL,completed_at=NULL,heartbeat_at=NULL,lease_expires_at=NULL
             WHERE id=?"""
    connection.execute(sql, (attempt_id, runtime_id, mode, scope, feedback, output_node_id, row["id"]))
    _event(connection, row["project_id"], "job_revision_queued", actor, ("job", row["id"]),
           {"mode": mode, "scope": scope, "feedback": feedback, "revision": row["revision"] + 1})


def _reject_current_artifact(connection: sqlite3.Connection, row: sqlite3.Row, actor: dict) -> None:
    if not row["output_artifact_id"]:
        return
    connection.execute("UPDATE artifacts SET status='rejected',reviewed_at=? WHERE id=? AND status='pending_review'",
                       (now(), row["output_artifact_id"]))
    _event(connection, row["project_id"], "artifact_reviewed", actor,
           ("artifact", row["output_artifact_id"]), {"decision": "reject", "reason": "node_revision"})


def _reject_job(connection: sqlite3.Connection, row: sqlite3.Row,
                feedback: str, actor: dict) -> None:
    _reject_current_artifact(connection, row, actor)
    connection.execute("UPDATE jobs SET status='rejected',completed_at=?,heartbeat_at=NULL,lease_expires_at=NULL WHERE id=?",
                       (now(), row["id"]))
    _schedule_cleanup(connection, row, "delete_job_workspace")
    _event(connection, row["project_id"], "job_rejected", actor, ("job", row["id"]), {"feedback": feedback})


def _finalize_if_ready(connection: sqlite3.Connection, job_id: str, actor: dict) -> bool:
    row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or not row["output_node_id"] or not _node_approved(connection, row["output_node_id"]):
        return False
    if row["output_artifact_id"] and not _artifact_published(connection, row["output_artifact_id"]):
        return False
    connection.execute("UPDATE jobs SET status='completed',completed_at=? WHERE id=?", (now(), job_id))
    _schedule_cleanup(connection, row, "delete_job_workspace")
    _event(connection, row["project_id"], "job_completed", actor, ("job", job_id),
           {"output_node_id": row["output_node_id"], "revision": row["revision"]})
    return True


def _artifact_published(connection: sqlite3.Connection, artifact_id: str) -> bool:
    return bool(connection.execute("SELECT 1 FROM artifacts WHERE id=? AND status='published'", (artifact_id,)).fetchone())


def _schedule_cleanup(connection: sqlite3.Connection, row: sqlite3.Row, action: str) -> None:
    if not row["runtime_id"] or not row["attempt_id"]:
        return
    command_id = uid("maintenance", {"job": row["id"], "attempt": row["attempt_id"], "action": action})
    sql = """INSERT OR IGNORE INTO workspace_commands(id,runtime_id,job_id,attempt_id,action,status,created_at)
             VALUES(?,?,?,?,?,'queued',?)"""
    connection.execute(sql, (command_id, row["runtime_id"], row["id"], row["attempt_id"], action, now()))


def claim_workspace_command(runtime_id: str) -> dict[str, Any] | None:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("""SELECT * FROM workspace_commands WHERE runtime_id=? AND status IN ('queued','running')
                                  ORDER BY created_at LIMIT 1""", (runtime_id,)).fetchone()
        if row:
            connection.execute("UPDATE workspace_commands SET status='running' WHERE id=?", (row["id"],))
        connection.commit()
    return dict(row) if row else None


def complete_workspace_command(command_id: str, runtime_id: str) -> dict[str, Any]:
    sql = """UPDATE workspace_commands SET status='completed',completed_at=?
             WHERE id=? AND runtime_id=? AND status='running'"""
    db.execute(sql, (now(), command_id, runtime_id))
    return db.row("SELECT * FROM workspace_commands WHERE id=?", (command_id,)) or {}


def sweep_stale() -> None:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _sweep_connection(connection)
        connection.commit()


def _sweep_connection(connection: sqlite3.Connection) -> None:
    cutoff = (datetime.now(UTC) - timedelta(seconds=RUNTIME_STALE_SECONDS)).isoformat()
    rows = connection.execute("SELECT * FROM runtimes WHERE status='online' AND last_seen<?", (cutoff,)).fetchall()
    for row in rows:
        connection.execute("UPDATE runtimes SET status='stale' WHERE id=?", (row["id"],))
        _event(connection, None, "runtime_status_changed", {"kind": "system", "id": "liveness"},
               ("runtime", row["id"]), {"status": "stale"})
    _requeue_expired_jobs(connection)


def _requeue_expired_jobs(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT * FROM jobs WHERE status='running' AND lease_expires_at<=?", (now(),)).fetchall()
    for row in rows:
        _schedule_cleanup(connection, row, "delete_attempt_workspace")
        sql = """UPDATE jobs SET status='queued',attempt_id=NULL,runtime_id=NULL,review_mode='restart',
                 started_at=NULL,heartbeat_at=NULL,lease_expires_at=NULL WHERE id=?"""
        connection.execute(sql, (row["id"],))
        _event(connection, row["project_id"], "job_requeued", {"kind": "system", "id": "liveness"},
               ("job", row["id"]), {"reason": "lease_expired", "attempt_id": row["attempt_id"],
                                    "runtime_id": row["runtime_id"]})


def invalidate_node(node_id: str, reason: str, actor: dict) -> dict[str, Any]:
    with db.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        root = connection.execute("SELECT * FROM nodes WHERE id=? AND status='admitted'", (node_id,)).fetchone()
        if not root:
            raise StateConflict("only admitted nodes can be invalidated")
        affected = _descendants(connection, root["project_id"], node_id)
        _invalidate_records(connection, root["project_id"], affected)
        _event(connection, root["project_id"], "subgraph_invalidated", actor, ("node", node_id),
               {"reason": reason, "affected_node_ids": affected})
        connection.commit()
    return {"root_id": node_id, "affected_node_ids": affected}


def _descendants(connection: sqlite3.Connection, project_id: str, node_id: str) -> list[str]:
    sql = """WITH RECURSIVE affected(id) AS (SELECT ? UNION SELECT e.target FROM edges e
             JOIN affected a ON e.source=a.id WHERE e.project_id=?) SELECT DISTINCT id FROM affected"""
    return [row["id"] for row in connection.execute(sql, (node_id, project_id)).fetchall()]


def _invalidate_records(connection: sqlite3.Connection, project_id: str, affected: list[str]) -> None:
    rows = _affected_jobs(connection, project_id, affected)
    marks = ",".join("?" for _ in affected)
    connection.execute(f"UPDATE nodes SET status='invalidated',audit='invalidated' WHERE id IN ({marks})", affected)
    connection.execute(f"UPDATE artifacts SET status='retracted' WHERE node_id IN ({marks})", affected)
    for row in rows:
        connection.execute("UPDATE jobs SET status='cancelled',lease_expires_at=NULL WHERE id=?", (row["id"],))
        _schedule_cleanup(connection, row, "delete_job_workspace")


def _affected_jobs(connection: sqlite3.Connection, project_id: str,
                   affected: list[str]) -> list[sqlite3.Row]:
    report_subjects = _report_context_subjects(connection, project_id, affected)
    affected_marks = ",".join("?" for _ in affected)
    report_marks = ",".join("?" for _ in report_subjects)
    sql = f"""SELECT * FROM jobs WHERE project_id=? AND status IN ('queued','running','awaiting_review')
              AND (subject_id IN ({affected_marks}) OR output_node_id IN ({affected_marks})
              OR (kind='html_report' AND subject_id IN ({report_marks})))"""
    return connection.execute(sql, (project_id, *affected, *affected, *report_subjects)).fetchall()


def _report_context_subjects(connection: sqlite3.Connection, project_id: str,
                             affected: list[str]) -> list[str]:
    marks = ",".join("?" for _ in affected)
    sql = f"""WITH RECURSIVE subjects(id) AS (SELECT id FROM nodes WHERE id IN ({marks})
              AND status='admitted' AND audit='approve' UNION
              SELECT e.source FROM edges e JOIN subjects s ON e.target=s.id WHERE e.project_id=?)
              SELECT DISTINCT id FROM subjects"""
    return [row["id"] for row in connection.execute(sql, (*affected, project_id)).fetchall()]


def events(project_id: str | None, after: int = 0) -> list[dict[str, Any]]:
    sql = "SELECT * FROM events WHERE seq>? AND (? IS NULL OR project_id=? OR project_id IS NULL) ORDER BY seq"
    return [decode_event(value) for value in db.rows(sql, (after, project_id, project_id))]


def decode_event(value: dict[str, Any]) -> dict[str, Any]:
    value["type"] = value.pop("kind")
    value["actor"] = {"kind": value.pop("actor_kind"), "id": value.pop("actor_id")}
    value["payload"] = db.decode(value.pop("payload_json"), {})
    return value


def decode_json_field(value: dict[str, Any], source: str, target: str) -> dict[str, Any]:
    value[target] = db.decode(value.pop(source), [])
    return value
