from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from .artifacts import ArtifactStore, now
from .db import Database


NODE_KINDS = {"question", "source", "claim", "artifact", "result"}
EDGE_TYPES = {"addresses", "supports", "contradicts", "derived_from", "contains"}


class InvalidPackage(ValueError):
    pass


def stable_id(prefix: str, value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


def decode(row: sqlite3.Row) -> dict:
    value = dict(row)
    for key in ("payload", "locator", "arguments", "result", "command", "spec", "usage", "entity"):
        if key in value and isinstance(value[key], str):
            value[key] = json.loads(value[key])
    return value


class World:
    def __init__(self, database: Path, artifacts: Path, embedding: Callable | None = None):
        self.db = Database(database)
        self.artifacts = ArtifactStore(artifacts, self.db)
        self.embedding = embedding

    def create_project(self, name: str, root: Path, question: str) -> dict:
        project_id = stable_id("project", {"name": name})
        values = (project_id, name, str(root.resolve()), question, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO projects VALUES(?,?,?,?,?)", values)
            self._insert_question(connection, project_id, question)
        return self.project(project_id)

    def _insert_question(self, connection: sqlite3.Connection, project_id: str, question: str) -> None:
        node_id = stable_id("node", {"project": project_id, "question": question})
        payload = json.dumps({"text": question})
        values = (node_id, project_id, None, None, "question", payload, "admitted", now(), now())
        connection.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)", values)
        connection.execute("INSERT INTO node_fts VALUES(?,?,?)", (node_id, project_id, question))

    def project(self, project_id: str) -> dict:
        return self._one("SELECT * FROM projects WHERE id=?", (project_id,))

    def projects(self) -> list[dict]:
        return self._many("SELECT * FROM projects ORDER BY created_at")

    def project_by_name(self, name: str) -> dict:
        return self._one("SELECT * FROM projects WHERE name=?", (name,))

    def path(self, value: str) -> Path:
        return Path(value)

    def sync_project(self, project_id: str) -> dict:
        project = self.project(project_id)
        manifest = {"project_id": project_id, "files": self._snapshot_files(Path(project["root"]))}
        artifact = self.add_artifact(json.dumps(manifest, sort_keys=True).encode(), "application/json")
        snapshot_id = stable_id("project-snapshot", {"project": project_id, "artifact": artifact["id"]})
        with self.db.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO project_snapshots VALUES(?,?,?,?)", (snapshot_id, project_id, artifact["id"], now()))
        return self._one("SELECT * FROM project_snapshots WHERE id=?", (snapshot_id,))

    def _snapshot_files(self, root: Path) -> list[dict]:
        ignored = {".git", ".venv", "data", "node_modules", "dist", "__pycache__"}
        paths = (path for path in root.rglob("*") if path.is_file() and not ignored.intersection(path.parts))
        return [self._snapshot_file(root, path) for path in sorted(paths)]

    def _snapshot_file(self, root: Path, path: Path) -> dict:
        artifact = self.add_artifact(path.read_bytes(), "application/octet-stream")
        return {"path": path.relative_to(root).as_posix(), "sha256": artifact["sha256"], "artifact_id": artifact["id"]}

    def snapshot_manifest(self, snapshot_id: str) -> dict:
        snapshot = self._one("SELECT * FROM project_snapshots WHERE id=?", (snapshot_id,))
        return json.loads(self.artifacts.read(snapshot["artifact_id"]))

    def snapshot_file(self, snapshot_id: str, path: str) -> bytes:
        manifest = self.snapshot_manifest(snapshot_id)
        entry = next((item for item in manifest["files"] if item["path"] == path), None)
        if not entry:
            raise KeyError(path)
        return self.artifacts.read(entry["artifact_id"])

    def create_run(self, project_id: str, question_id: int, apply_selected: bool) -> dict:
        run_id = f"run:{secrets.token_hex(12)}"
        values = (run_id, project_id, question_id, "created", int(apply_selected), None, None, None, now(), None)
        with self.db.connect() as connection:
            connection.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?)", values)
        return self.run(run_id)

    def run(self, run_id: str) -> dict:
        return self._one("SELECT * FROM runs WHERE id=?", (run_id,))

    def runs(self) -> list[dict]:
        return self._many("SELECT * FROM runs ORDER BY created_at DESC")

    def claim_run(self, run_id: str | None = None) -> dict | None:
        with self.db.connect() as connection:
            if run_id:
                row = connection.execute("UPDATE runs SET status='claimed' WHERE id=? AND status='created' RETURNING *", (run_id,)).fetchone()
            else:
                row = connection.execute("UPDATE runs SET status='claimed' WHERE id=(SELECT id FROM runs WHERE status='created' ORDER BY created_at LIMIT 1) RETURNING *").fetchone()
        return decode(row) if row else None

    def create_attempt(self, run_id: str, generation_id: str, snapshot_id: str, actor: str) -> dict:
        attempt_id = f"attempt:{secrets.token_hex(12)}"
        values = (attempt_id, run_id, generation_id, snapshot_id, actor, "created", None, None, now(), None)
        with self.db.connect() as connection:
            connection.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?)", values)
        return self.attempt(attempt_id)

    def attempt(self, attempt_id: str) -> dict:
        return self._one("SELECT * FROM attempts WHERE id=?", (attempt_id,))

    def attempt_project(self, attempt_id: str) -> dict:
        attempt = self.attempt(attempt_id)
        return self.project(self.run(attempt["run_id"])["project_id"])

    def attempts(self, run_id: str, actor: str | None = None) -> list[dict]:
        if actor:
            return self._many("SELECT * FROM attempts WHERE run_id=? AND actor=? ORDER BY created_at", (run_id, actor))
        return self._many("SELECT * FROM attempts WHERE run_id=? ORDER BY created_at", (run_id,))

    def complete_attempt(self, attempt_id: str, wire: bytes, context: bytes) -> dict:
        wire_artifact = self.add_artifact(wire, "application/json")
        context_artifact = self.add_artifact(context, "application/json")
        with self.db.connect() as connection:
            connection.execute("UPDATE attempts SET status='completed',wire_artifact_id=?,context_artifact_id=?,completed_at=? WHERE id=?", (wire_artifact["id"], context_artifact["id"], now(), attempt_id))
        attempt = self.attempt(attempt_id)
        self.record_event(attempt["run_id"], attempt["generation_id"], attempt_id, attempt["actor"], "attempt_completed", {"type": "attempt", "id": attempt_id}, {"wire_artifact_id": wire_artifact["id"], "context_artifact_id": context_artifact["id"]})
        return attempt

    def issue_task_token(self, attempt_id: str, minutes: int = 30) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()
        with self.db.connect() as connection:
            connection.execute("INSERT INTO task_tokens VALUES(?,?,?)", (self._token_hash(token), attempt_id, expires))
        return token

    def authorize_task(self, token: str, attempt_id: str) -> dict | None:
        sql = "SELECT attempt_id,expires_at FROM task_tokens WHERE token_hash=?"
        rows = self._rows(sql, (self._token_hash(token),))
        if not rows or rows[0]["attempt_id"] != attempt_id or rows[0]["expires_at"] <= now():
            return None
        return self.attempt(attempt_id)

    def _token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def record_event(self, run_id: str, generation_id: str | None, attempt_id: str | None,
                     actor: str, event_type: str, entity: dict, payload: dict) -> dict:
        values = (run_id, generation_id, attempt_id, actor, event_type, now(), json.dumps(entity), json.dumps(payload))
        with self.db.connect() as connection:
            cursor = connection.execute("INSERT INTO events(run_id,generation_id,attempt_id,actor,type,time,entity,payload) VALUES(?,?,?,?,?,?,?,?)", values)
            event_id = cursor.lastrowid
        return self.event(event_id)

    def event(self, event_id: int) -> dict:
        return self._one("SELECT * FROM events WHERE event_id=?", (event_id,))

    def events(self, run_id: str, after: int = 0) -> list[dict]:
        return self._many("SELECT * FROM events WHERE run_id=? AND event_id>? ORDER BY event_id", (run_id, after))

    def create_generation(self, project_id: str, ordinal: int, parent_id: str | None = None,
                          strategy_change: str | None = None, run_id: str | None = None) -> dict:
        generation_id = stable_id("generation", {"project": project_id, "run": run_id, "ordinal": ordinal})
        values = (generation_id, project_id, run_id, ordinal, parent_id, strategy_change, None, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO generations VALUES(?,?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM generations WHERE id=?", (generation_id,))

    def generations(self, run_id: str) -> list[dict]:
        return self._many("SELECT * FROM generations WHERE run_id=? ORDER BY ordinal", (run_id,))

    def update_generation(self, generation_id: str, package_id: str, strategy_change: str | None) -> None:
        with self.db.connect() as connection:
            connection.execute("UPDATE generations SET package_id=?,strategy_change=? WHERE id=?", (package_id, strategy_change, generation_id))

    def update_run(self, run_id: str, status: str, **fields) -> dict:
        allowed = {"project_snapshot_id", "final_markdown_id", "final_html_id", "completed_at"}
        values = {key: value for key, value in fields.items() if key in allowed}
        assignments = ["status=?", *(f"{key}=?" for key in values)]
        with self.db.connect() as connection:
            connection.execute(f"UPDATE runs SET {','.join(assignments)} WHERE id=?", (status, *values.values(), run_id))
        return self.run(run_id)

    def admitted_nodes(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM nodes WHERE project_id=? AND status='admitted' ORDER BY created_at", (project_id,))

    def admitted_node(self, node_id: str, project_id: str | None = None) -> dict:
        sql = "SELECT * FROM nodes WHERE id=? AND status='admitted'"
        return self._one(sql + (" AND project_id=?" if project_id else ""), (node_id, project_id) if project_id else (node_id,))

    def require_artifact_access(self, attempt_id: str, artifact_id: str) -> dict:
        if not self._artifact_accessible(attempt_id, artifact_id):
            raise PermissionError("artifact is outside the task capability")
        return self.artifact_value(artifact_id)

    def _artifact_accessible(self, attempt_id: str, artifact_id: str) -> bool:
        attempt = self.attempt(attempt_id)
        project_id = self.attempt_project(attempt_id)["id"]
        snapshot_ids = {entry["artifact_id"] for entry in self.snapshot_manifest(attempt["snapshot_id"])["files"]}
        return artifact_id in snapshot_ids or self._admitted_artifact(project_id, artifact_id) or self._attempt_artifact(attempt, artifact_id)

    def _admitted_artifact(self, project_id: str, artifact_id: str) -> bool:
        sql = "SELECT 1 FROM nodes WHERE project_id=? AND status='admitted' AND json_extract(payload,'$.artifact_id')=?"
        return bool(self._rows(sql, (project_id, artifact_id)))

    def _attempt_artifact(self, attempt: dict, artifact_id: str) -> bool:
        direct = artifact_id in {attempt["wire_artifact_id"], attempt["context_artifact_id"]}
        sql = "SELECT 1 FROM executions WHERE attempt_id=? AND (input_artifact_id=? OR output_artifact_id=?)"
        execution = bool(self._rows(sql, (attempt["id"], artifact_id, artifact_id)))
        event = bool(self._rows("SELECT 1 FROM events WHERE attempt_id=? AND json_extract(entity,'$.id')=?", (attempt["id"], artifact_id)))
        return direct or execution or event

    def project_edges(self, project_id: str) -> list[dict]:
        sql = "SELECT e.source,e.target,e.type FROM edges e JOIN nodes s ON s.id=e.source JOIN nodes t ON t.id=e.target WHERE s.project_id=? AND s.status='admitted' AND t.status='admitted'"
        return self._many(sql, (project_id,))

    def project_artifacts(self, project_id: str) -> list[dict]:
        sql = "SELECT DISTINCT a.* FROM artifacts a JOIN nodes n ON json_extract(n.payload,'$.artifact_id')=a.id WHERE n.project_id=?"
        return self._many(sql, (project_id,))

    def reviews(self, package_id: str) -> list[dict]:
        return self._many("SELECT * FROM reviews WHERE package_id=? ORDER BY created_at", (package_id,))

    def add_tool_receipt(self, attempt_id: str, server: str, tool: str,
                         arguments: dict, result: object, error: str | None = None) -> dict:
        receipt_id = f"tool-receipt:{secrets.token_hex(12)}"
        values = (receipt_id, attempt_id, server, tool, json.dumps(arguments), json.dumps(result), error, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO tool_receipts VALUES(?,?,?,?,?,?,?,?)", values)
        receipt = self._one("SELECT * FROM tool_receipts WHERE id=?", (receipt_id,))
        self._tool_events(receipt)
        return receipt

    def _tool_events(self, receipt: dict) -> None:
        attempt = self.attempt(receipt["attempt_id"])
        entity = {"type": "tool_receipt", "id": receipt["id"]}
        self.record_event(attempt["run_id"], attempt["generation_id"], attempt["id"], attempt["actor"], "tool_call", entity, {"server": receipt["server"], "tool": receipt["tool"], "arguments": receipt["arguments"]})
        self.record_event(attempt["run_id"], attempt["generation_id"], attempt["id"], attempt["actor"], "tool_result", entity, {"result": receipt["result"], "error": receipt["error"]})

    def tool_receipts(self, attempt_id: str) -> list[dict]:
        return self._many("SELECT * FROM tool_receipts WHERE attempt_id=? ORDER BY created_at", (attempt_id,))

    def add_execution(self, values: dict) -> dict:
        columns = ("id", "project_id", "attempt_id", "environment_id", "image_digest", "command", "input_artifact_id", "input_hash", "seed", "spec", "exit_code", "output_artifact_id", "output_hash", "usage", "created_at")
        encoded = {**values, "command": json.dumps(values["command"]), "spec": json.dumps(values["spec"]), "usage": json.dumps(values["usage"])}
        with self.db.connect() as connection:
            connection.execute(f"INSERT INTO executions({','.join(columns)}) VALUES({','.join('?' for _ in columns)})", tuple(encoded[column] for column in columns))
        return self.execution(values["id"])

    def execution(self, execution_id: str) -> dict:
        return self._one("SELECT * FROM executions WHERE id=?", (execution_id,))

    def artifact_value(self, artifact_id: str) -> dict:
        return self.artifacts.get(artifact_id)

    def public_artifact(self, artifact_id: str) -> dict:
        sql = "SELECT 1 FROM nodes WHERE status='admitted' AND json_extract(payload,'$.artifact_id')=?"
        if not self._rows(sql, (artifact_id,)):
            raise PermissionError("artifact is not admitted")
        return self.artifact_value(artifact_id)

    def add_environment(self, project_id: str, attempt_id: str, image_digest: str,
                        lock_artifact_id: str, setup: list[str]) -> dict:
        environment_id = stable_id("environment", {"image": image_digest, "lock": lock_artifact_id})
        values = (environment_id, project_id, attempt_id, image_digest, lock_artifact_id, json.dumps(setup), now())
        with self.db.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO environments VALUES(?,?,?,?,?,?,?)", values)
        return self.environment(environment_id)

    def environment(self, environment_id: str) -> dict:
        return self._one("SELECT * FROM environments WHERE id=?", (environment_id,))

    def add_artifact(self, content: bytes, media_type: str) -> dict:
        return self.artifacts.add(content, media_type)

    def admit_artifact_node(self, project_id: str, generation_id: str,
                            artifact: dict, role: str) -> dict:
        payload = {"artifact_id": artifact["id"], "sha256": artifact["sha256"],
                   "media_type": artifact["media_type"], "role": role}
        node_id = stable_id("node", {"project": project_id, "generation": generation_id, "artifact": payload})
        values = (node_id, project_id, generation_id, None, "artifact", json.dumps(payload), "admitted", now(), now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)", values)
            connection.execute("INSERT INTO node_fts VALUES(?,?,?)", (node_id, project_id, role))
            self._store_embedding(connection, node_id, role)
        return self._one("SELECT * FROM nodes WHERE id=?", (node_id,))

    def add_source_snapshot(self, project_id: str, url: str, artifact: dict, locator: dict) -> dict:
        self._validate_locator(artifact["id"], locator)
        snapshot_id = stable_id("source-snapshot", {"url": url, "hash": artifact["sha256"], "locator": locator})
        values = (snapshot_id, project_id, url, artifact["id"], json.dumps(locator), now())
        with self.db.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO source_snapshots VALUES(?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM source_snapshots WHERE id=?", (snapshot_id,))

    def source_snapshot(self, snapshot_id: str) -> dict:
        return self._one("SELECT * FROM source_snapshots WHERE id=?", (snapshot_id,))

    def submit_package(self, project_id: str, payload: dict) -> dict:
        self._validate_package(project_id, payload)
        package_id = stable_id("package", payload)
        with self.db.connect() as connection:
            self._insert_package(connection, package_id, project_id, payload)
            self._insert_package_graph(connection, package_id, project_id, payload)
        return self._one("SELECT * FROM packages WHERE id=?", (package_id,))

    def _insert_package(self, connection, package_id, project_id, payload) -> None:
        values = (package_id, project_id, payload["generation_id"], json.dumps(payload), "pending", now(), None)
        connection.execute("INSERT INTO packages VALUES(?,?,?,?,?,?,?)", values)

    def _insert_package_graph(self, connection, package_id, project_id, payload) -> None:
        nodes = self._package_node_values(package_id, project_id, payload)
        connection.executemany("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)", nodes)
        result_id = nodes[-1][0]
        for node in nodes[:-1]:
            connection.execute("INSERT INTO edges VALUES(?,?,?,?)", (result_id, node[0], "contains", package_id))
        self._insert_semantic_edges(connection, package_id, nodes, payload)

    def _package_node_values(self, package_id, project_id, payload) -> list[tuple]:
        values = []
        generation_id = payload["generation_id"]
        for kind, entries in (("source", payload["sources"]), ("claim", payload["claims"]), ("artifact", payload["artifacts"])):
            values.extend(self._node_value(project_id, generation_id, package_id, kind, entry) for entry in entries)
        result = {"strategy": payload["strategy"], "code": payload["code"], "no_code_reason": payload.get("no_code_reason")}
        values.append(self._node_value(project_id, generation_id, package_id, "result", result))
        return values

    def _node_value(self, project_id, generation_id, package_id, kind, payload) -> tuple:
        node_id = stable_id("node", {"package": package_id, "kind": kind, "payload": payload})
        return (node_id, project_id, generation_id, package_id, kind, json.dumps(payload), "pending", now(), None)

    def _insert_semantic_edges(self, connection, package_id, nodes, payload) -> None:
        sources = [node[0] for node in nodes if node[4] == "source"]
        claims = [node[0] for node in nodes if node[4] == "claim"]
        question = connection.execute("SELECT id FROM nodes WHERE project_id=? AND kind='question'", (nodes[0][1],)).fetchone()[0]
        result = nodes[-1][0]
        connection.execute("INSERT INTO edges VALUES(?,?,?,?)", (result, question, "addresses", package_id))
        for source in sources:
            for claim in claims:
                connection.execute("INSERT INTO edges VALUES(?,?,?,?)", (source, claim, "supports", package_id))

    def _validate_package(self, project_id: str, payload: dict) -> None:
        self._validate_package_shape(payload)
        generation = self._one("SELECT * FROM generations WHERE id=?", (payload["generation_id"],))
        if generation["project_id"] != project_id:
            raise InvalidPackage("generation belongs to another project")
        if not payload["code"] and not payload.get("no_code_reason"):
            raise InvalidPackage("an empty code set requires no_code_reason")
        execution_ids = self._validate_code(project_id, payload["generation_id"], payload["code"])
        self._validate_computational_claims(payload["claims"], execution_ids)
        for source in payload["sources"]:
            self._validate_source(project_id, source)
        for artifact in payload["artifacts"]:
            self._validate_artifact(artifact)
        for claim in payload["claims"]:
            self._validate_claim(project_id, claim)

    def _validate_code(self, project_id: str, generation_id: str, code: list[dict]) -> set[str]:
        execution_ids = set()
        for entry in code:
            execution = self._validated_execution(project_id, generation_id, entry)
            execution_ids.add(execution["id"])
        return execution_ids

    def _validated_execution(self, project_id: str, generation_id: str, entry: dict) -> dict:
        if {"execution_id", "artifact_id"} - entry.keys():
            raise InvalidPackage("code entry requires execution_id and artifact_id")
        try:
            execution = self.execution(entry["execution_id"])
            attempt = self.attempt(execution["attempt_id"])
        except KeyError as error:
            raise InvalidPackage("code execution does not exist") from error
        self._check_execution(project_id, generation_id, entry, execution, attempt)
        return execution

    def _check_execution(self, project_id, generation_id, entry, execution, attempt) -> None:
        artifact = self.artifact_value(execution["output_artifact_id"])
        valid = execution["project_id"] == project_id and attempt["generation_id"] == generation_id
        valid = valid and execution["exit_code"] == 0 and execution["usage"].get("replay_verified") is True
        valid = valid and entry["artifact_id"] == execution["output_artifact_id"]
        if not valid or artifact["sha256"] != execution["output_hash"]:
            raise InvalidPackage("code execution receipt or offline replay is invalid")

    def _validate_computational_claims(self, claims: list[dict], execution_ids: set[str]) -> None:
        for claim in claims:
            if claim.get("kind") == "computational" and claim.get("execution_id") not in execution_ids:
                raise InvalidPackage("computational claim requires a verified execution")

    def _validate_package_shape(self, payload: dict) -> None:
        required = {"generation_id", "strategy", "sources", "claims", "artifacts", "code"}
        missing = sorted(required - payload.keys())
        if missing:
            raise InvalidPackage(f"research package missing keys: {', '.join(missing)}")
        if not all(isinstance(payload[key], list) for key in ("sources", "claims", "artifacts", "code")):
            raise InvalidPackage("sources, claims, artifacts, and code must be arrays")
        if not payload["claims"]:
            raise InvalidPackage("research package requires claims")

    def _validate_source(self, project_id: str, source: dict) -> None:
        if {"snapshot_id", "artifact_id"} - source.keys():
            raise InvalidPackage("package source is incomplete")
        snapshot = self.source_snapshot(source["snapshot_id"])
        if snapshot["project_id"] != project_id or snapshot["artifact_id"] != source["artifact_id"]:
            raise InvalidPackage("package source does not resolve")

    def _validate_artifact(self, artifact: dict) -> None:
        if {"artifact_id", "role"} - artifact.keys():
            raise InvalidPackage("package artifact is incomplete")
        try:
            self.artifact_value(artifact["artifact_id"])
        except KeyError as error:
            raise InvalidPackage("package artifact does not exist") from error

    def _validate_claim(self, project_id: str, claim: dict) -> None:
        if not claim.get("text") or not claim.get("citations"):
            raise InvalidPackage("every claim requires citations")
        for citation in claim["citations"]:
            self._validate_citation(project_id, citation)

    def _validate_citation(self, project_id: str, citation: dict) -> None:
        keys = {"source_snapshot_id", "artifact_id", "locator"}
        if keys - citation.keys():
            raise InvalidPackage("citation is incomplete")
        snapshot = self._one("SELECT * FROM source_snapshots WHERE id=?", (citation["source_snapshot_id"],))
        if snapshot["project_id"] != project_id or snapshot["artifact_id"] != citation["artifact_id"]:
            raise InvalidPackage("citation does not resolve to its source snapshot")
        self._validate_locator(citation["artifact_id"], citation["locator"])

    def _validate_locator(self, artifact_id: str, locator: dict) -> None:
        if "line_start" not in locator or "line_end" not in locator:
            raise InvalidPackage("locator requires a line range")
        line_count = len(self.artifacts.read(artifact_id).decode("utf-8").splitlines())
        if not 1 <= locator["line_start"] <= locator["line_end"] <= line_count:
            raise InvalidPackage("locator is outside the artifact")

    def review_package(self, package_id: str, reviewer: str, decision: str, feedback: str) -> dict:
        if decision not in {"approve", "revise", "uncertain"}:
            raise ValueError("invalid review decision")
        review_id = stable_id("review", {"package": package_id, "reviewer": reviewer})
        with self.db.connect() as connection:
            self._insert_review(connection, review_id, package_id, reviewer, decision, feedback)
            self._resolve_reviews(connection, package_id)
        return self._one("SELECT * FROM reviews WHERE id=?", (review_id,))

    def human_admit_package(self, package_id: str, feedback: str) -> dict:
        with self.db.connect() as connection:
            status = connection.execute("SELECT status FROM packages WHERE id=?", (package_id,)).fetchone()[0]
            if status != "conflict":
                raise InvalidPackage("only a conflicted package can be human-approved")
            self._admit(connection, package_id)
            self._insert_review(connection, stable_id("review", {"package": package_id, "reviewer": "human-resolver"}), package_id, "human-resolver", "approve", feedback)
        return self._one("SELECT * FROM packages WHERE id=?", (package_id,))

    def _insert_review(self, connection, review_id, package_id, reviewer, decision, feedback) -> None:
        sql = "INSERT INTO reviews VALUES(?,?,?,?,?,?)"
        connection.execute(sql, (review_id, package_id, reviewer, decision, feedback, now()))

    def _resolve_reviews(self, connection: sqlite3.Connection, package_id: str) -> None:
        decisions = [row[0] for row in connection.execute("SELECT decision FROM reviews WHERE package_id=?", (package_id,))]
        if len(decisions) == 2 and set(decisions) == {"approve"}:
            self._admit(connection, package_id)
        elif len(decisions) == 2 and set(decisions) == {"revise"}:
            connection.execute("UPDATE packages SET status='revise' WHERE id=?", (package_id,))
        elif len(decisions) == 2:
            connection.execute("UPDATE packages SET status='conflict' WHERE id=?", (package_id,))

    def _admit(self, connection: sqlite3.Connection, package_id: str) -> None:
        timestamp = now()
        connection.execute("UPDATE packages SET status='admitted',admitted_at=? WHERE id=?", (timestamp, package_id))
        connection.execute("UPDATE nodes SET status='admitted',admitted_at=? WHERE package_id=?", (timestamp, package_id))
        rows = connection.execute("SELECT id,project_id,payload FROM nodes WHERE package_id=?", (package_id,)).fetchall()
        for row in rows:
            text = self._node_text(json.loads(row["payload"]))
            connection.execute("INSERT INTO node_fts VALUES(?,?,?)", (row["id"], row["project_id"], text))
            self._store_embedding(connection, row["id"], text)

    def _store_embedding(self, connection, node_id, text) -> None:
        if self.embedding:
            vector = json.dumps(self.embedding(text))
            connection.execute("INSERT INTO node_embeddings VALUES(?,?)", (node_id, vector))

    def package_nodes(self, package_id: str) -> list[dict]:
        return self._many("SELECT * FROM nodes WHERE package_id=? ORDER BY created_at", (package_id,))

    def package(self, package_id: str) -> dict:
        return self._one("SELECT * FROM packages WHERE id=?", (package_id,))

    def search(self, project_id: str, query: str, embed: Callable | None = None) -> list[dict]:
        lexical = self._fts_seeds(project_id, query)
        semantic = self._vector_seeds(project_id, query, embed or self.embedding)
        seeds = self._rrf(lexical, semantic)
        ids = self._expand([node_id for node_id, _ in seeds], project_id)[:40]
        return [self._one("SELECT * FROM nodes WHERE id=? AND status='admitted'", (node_id,)) for node_id in ids]

    def _fts_seeds(self, project_id: str, query: str) -> list[str]:
        terms = re.findall(r"[A-Za-z0-9]+", query)
        if not terms:
            return []
        match = " OR ".join(terms)
        sql = "SELECT node_id FROM node_fts WHERE project_id=? AND node_fts MATCH ? ORDER BY bm25(node_fts) LIMIT 10"
        return [row["node_id"] for row in self._rows(sql, (project_id, match))]

    def _vector_seeds(self, project_id: str, query: str, embed: Callable | None) -> list[str]:
        if not embed:
            return []
        target = embed(query)
        rows = self._rows("SELECT n.id,n.payload,e.vector FROM nodes n LEFT JOIN node_embeddings e ON e.node_id=n.id WHERE n.project_id=? AND n.status='admitted'", (project_id,))
        ranked = sorted(rows, key=lambda row: self._distance(target, row, embed))
        return [row["id"] for row in ranked[:10]]

    def _distance(self, target: list[float], row: sqlite3.Row, embed: Callable) -> float:
        vector = json.loads(row["vector"]) if row["vector"] else embed(self._node_text(json.loads(row["payload"])))
        norm = math.sqrt(sum(value * value for value in target)) * math.sqrt(sum(value * value for value in vector))
        return 1 - sum(a * b for a, b in zip(target, vector)) / (norm or 1)

    def _rrf(self, *rankings: list[str]) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, node_id in enumerate(ranking, 1):
                scores[node_id] = scores.get(node_id, 0) + 1 / (60 + rank)
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    def _expand(self, seeds: list[str], project_id: str) -> list[str]:
        ordered = list(dict.fromkeys(seeds))
        if not seeds:
            return ordered
        marks = ",".join("?" for _ in seeds)
        sql = f"SELECT source,target FROM edges WHERE type IN ('addresses','supports','contradicts','derived_from','contains') AND (source IN ({marks}) OR target IN ({marks}))"
        for row in self._rows(sql, (*seeds, *seeds)):
            ordered.extend((row["source"], row["target"]))
        return list(dict.fromkeys(ordered))

    def _node_text(self, payload: dict) -> str:
        return " ".join(str(value) for value in payload.values() if isinstance(value, (str, int, float)))

    def _rows(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.db.connect() as connection:
            return connection.execute(sql, params).fetchall()

    def _one(self, sql: str, params: tuple = ()) -> dict:
        rows = self._rows(sql, params)
        if not rows:
            raise KeyError(params[0] if params else sql)
        return decode(rows[0])

    def _many(self, sql: str, params: tuple = ()) -> list[dict]:
        return [decode(row) for row in self._rows(sql, params)]
