from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from pathlib import Path

from .artifacts import ArtifactStore, now
from .db import Database


def stable_id(prefix: str, value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


def decode(row: sqlite3.Row) -> dict:
    value = dict(row)
    encoded = ("payload", "locator", "arguments", "result", "command", "spec", "usage", "entity", "brief", "input", "output", "evidence")
    for key in encoded:
        if key in value and isinstance(value[key], str):
            value[key] = json.loads(value[key])
    return value


class World:
    def __init__(self, database: Path, artifacts: Path):
        self.db = Database(database)
        self.artifacts = ArtifactStore(artifacts, self.db)

    def create_project(self, name: str, root: Path, question: str) -> dict:
        project_id = stable_id("project", {"name": name})
        values = (project_id, name, str(root.resolve()), question, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO projects VALUES(?,?,?,?,?)", values)
            self._insert_question(connection, project_id, question)
        return self.project(project_id)

    def _insert_question(self, connection, project_id: str, question: str) -> None:
        node_id = stable_id("node", {"project": project_id, "question": question})
        values = (node_id, project_id, None, None, "question", json.dumps({"text": question}), "admitted", now(), now())
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
        values = (snapshot_id, project_id, artifact["id"], now())
        with self.db.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO project_snapshots VALUES(?,?,?,?)", values)
        return self._one("SELECT * FROM project_snapshots WHERE id=?", (snapshot_id,))

    def _snapshot_files(self, root: Path) -> list[dict]:
        ignored = {".git", ".venv", "data", "node_modules", "dist", "__pycache__", "research-dossier"}
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
        columns = "id,project_id,question_id,status,apply_selected,created_at"
        values = (run_id, project_id, question_id, "created", int(apply_selected), now())
        self._execute(f"INSERT INTO runs({columns}) VALUES(?,?,?,?,?,?)", values)
        return self.run(run_id)

    def run(self, run_id: str) -> dict:
        return self._one("SELECT * FROM runs WHERE id=?", (run_id,))

    def create_generation(self, project_id: str, ordinal: int, parent_id: str | None = None,
                          strategy_change: str | None = None, run_id: str | None = None) -> dict:
        generation_id = stable_id("generation", {"project": project_id, "run": run_id, "ordinal": ordinal})
        columns = "id,project_id,run_id,ordinal,parent_id,strategy_change,created_at"
        values = (generation_id, project_id, run_id, ordinal, parent_id, strategy_change, now())
        self._execute(f"INSERT INTO generations({columns}) VALUES(?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM generations WHERE id=?", (generation_id,))

    def create_attempt(self, run_id: str, generation_id: str, snapshot_id: str, actor: str) -> dict:
        attempt_id = f"attempt:{secrets.token_hex(12)}"
        columns = "id,run_id,generation_id,snapshot_id,actor,status,created_at"
        values = (attempt_id, run_id, generation_id, snapshot_id, actor, "created", now())
        self._execute(f"INSERT INTO attempts({columns}) VALUES(?,?,?,?,?,?,?)", values)
        return self.attempt(attempt_id)

    def attempt(self, attempt_id: str) -> dict:
        return self._one("SELECT * FROM attempts WHERE id=?", (attempt_id,))

    def complete_attempt(self, attempt_id: str, wire: bytes, context: bytes, manifest: bytes) -> dict:
        artifacts = [self.add_artifact(value, "application/json") for value in (wire, context, manifest)]
        sql = "UPDATE attempts SET status='completed',wire_artifact_id=?,context_artifact_id=?,manifest_artifact_id=?,completed_at=? WHERE id=?"
        self._execute(sql, (*[item["id"] for item in artifacts], now(), attempt_id))
        return self.attempt(attempt_id)

    def fail_attempt(self, attempt_id: str, error: str) -> dict:
        artifact = self.add_artifact(error.encode(), "text/plain")
        self._execute("UPDATE attempts SET status='failed',wire_artifact_id=?,completed_at=? WHERE id=?", (artifact["id"], now(), attempt_id))
        return self.attempt(attempt_id)

    def grant_artifact(self, attempt_id: str, artifact_id: str, role: str) -> None:
        self._execute("INSERT OR IGNORE INTO attempt_artifacts VALUES(?,?,?)", (attempt_id, artifact_id, role))

    def update_run(self, run_id: str, status: str, **fields) -> dict:
        allowed = {"project_snapshot_id", "completed_at"}
        values = {key: value for key, value in fields.items() if key in allowed}
        assignments = ["status=?", *(f"{key}=?" for key in values)]
        self._execute(f"UPDATE runs SET {','.join(assignments)} WHERE id=?", (status, *values.values(), run_id))
        return self.run(run_id)

    def project_nodes(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM nodes WHERE project_id=? ORDER BY created_at", (project_id,))

    def all_project_edges(self, project_id: str) -> list[dict]:
        sql = "SELECT e.source,e.target,e.type FROM edges e JOIN nodes s ON s.id=e.source JOIN nodes t ON t.id=e.target WHERE s.project_id=? AND t.project_id=?"
        return self._many(sql, (project_id, project_id))

    def add_tool_receipt(self, attempt_id: str, server: str, tool: str,
                         arguments: dict, result: object, error: str | None = None) -> dict:
        receipt_id = f"tool-receipt:{secrets.token_hex(12)}"
        values = (receipt_id, attempt_id, server, tool, json.dumps(arguments), json.dumps(result), error, now())
        self._execute("INSERT INTO tool_receipts VALUES(?,?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM tool_receipts WHERE id=?", (receipt_id,))

    def tool_receipts(self, attempt_id: str) -> list[dict]:
        return self._many("SELECT * FROM tool_receipts WHERE attempt_id=? ORDER BY created_at", (attempt_id,))

    def add_execution(self, values: dict) -> dict:
        columns = ("id", "project_id", "attempt_id", "environment_id", "image_digest", "command", "input_artifact_id", "input_hash", "seed", "spec", "exit_code", "output_artifact_id", "output_hash", "usage", "created_at")
        encoded = {**values, "command": json.dumps(values["command"]), "spec": json.dumps(values["spec"]), "usage": json.dumps(values["usage"])}
        marks = ",".join("?" for _ in columns)
        self._execute(f"INSERT INTO executions({','.join(columns)}) VALUES({marks})", tuple(encoded[key] for key in columns))
        return self.execution(values["id"])

    def execution(self, execution_id: str) -> dict:
        return self._one("SELECT * FROM executions WHERE id=?", (execution_id,))

    def add_environment(self, project_id: str, attempt_id: str, image_digest: str,
                        lock_artifact_id: str, setup: list[str]) -> dict:
        environment_id = stable_id("environment", {"image": image_digest, "lock": lock_artifact_id})
        values = (environment_id, project_id, attempt_id, image_digest, lock_artifact_id, json.dumps(setup), now())
        self._execute("INSERT OR IGNORE INTO environments VALUES(?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM environments WHERE id=?", (environment_id,))

    def add_artifact(self, content: bytes, media_type: str) -> dict:
        return self.artifacts.add(content, media_type)

    def add_source_snapshot(self, project_id: str, url: str, artifact: dict, locator: dict) -> dict:
        self._validate_locator(artifact["id"], locator)
        snapshot_id = stable_id("source-snapshot", {"url": url, "hash": artifact["sha256"], "locator": locator})
        values = (snapshot_id, project_id, url, artifact["id"], json.dumps(locator), now())
        self._execute("INSERT OR IGNORE INTO source_snapshots VALUES(?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM source_snapshots WHERE id=?", (snapshot_id,))

    def _validate_locator(self, artifact_id: str, locator: dict) -> None:
        if "line_start" not in locator or "line_end" not in locator:
            raise ValueError("locator requires a line range")
        line_count = len(self.artifacts.read(artifact_id).decode("utf-8").splitlines())
        if not 1 <= locator["line_start"] <= locator["line_end"] <= line_count:
            raise ValueError("locator is outside the artifact")

    def _execute(self, sql: str, values: tuple) -> None:
        with self.db.connect() as connection:
            connection.execute(sql, values)

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
