from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from pathlib import Path
from typing import Callable

from .artifacts import now
from .db import Database


NODE_KINDS = {"question", "source", "direction", "experiment"}
LIFE_STATES = {"pending", "admitted", "ghost"}
EDGE_POLARITIES = {"supports", "refutes"}
DIRECTION_STATES = {"proposed", "supported", "refuted"}


def stable_id(prefix: str, value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


def decode(row: sqlite3.Row) -> dict:
    value = dict(row)
    for key in ("payload", "rebuttal"):
        if value.get(key):
            value[key] = json.loads(value[key])
    return value


class World:
    def __init__(self, database: Path, artifacts: Path, embedding: Callable | None = None):
        self.db = Database(database)
        self.artifacts_root = artifacts
        self.embedding = embedding

    def create_project(self, name: str, root: Path, question: str) -> dict:
        project_id = stable_id("project", {"name": name})
        values = (project_id, name, str(root.resolve()), question, 0, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", values)
            self._insert_question(connection, project_id, question)
        return self.project(project_id)

    def _insert_question(self, connection, project_id: str, text: str) -> None:
        node_id = stable_id("node", {"project": project_id, "question": text})
        values = (node_id, project_id, None, node_id, "question", json.dumps({"text": text}),
                  "admitted", None, 0, None, None, now(), now())
        connection.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        connection.execute("INSERT INTO node_fts VALUES(?,?,?)", (node_id, project_id, text))

    def project(self, project_id: str) -> dict:
        return self._one("SELECT * FROM projects WHERE id=?", (project_id,))

    def project_by_name(self, name: str) -> dict:
        return self._one("SELECT * FROM projects WHERE name=?", (name,))

    def projects(self) -> list[dict]:
        return self._many("SELECT * FROM projects ORDER BY created_at")

    def set_auto(self, project_id: str, enabled: bool) -> dict:
        with self.db.connect() as connection:
            connection.execute("UPDATE projects SET auto=? WHERE id=?", (int(enabled), project_id))
        return self.project(project_id)

    def create_node(self, project_id: str, kind: str, payload: dict, **state) -> dict:
        self._validate_node(kind, state.get("life_state", "pending"), state.get("direction_status"))
        node_id = f"node:{secrets.token_hex(12)}"
        parent_id = state.get("parent_id")
        lineage_id = state.get("lineage_id") or self._lineage(parent_id, node_id)
        values = self._node_values(node_id, project_id, kind, payload, lineage_id, state)
        with self.db.connect() as connection:
            connection.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
            connection.execute("INSERT INTO node_fts VALUES(?,?,?)", (node_id, project_id, self._node_text(payload)))
            self._store_embedding(connection, node_id, payload)
        return self.node(node_id)

    def _node_values(self, node_id, project_id, kind, payload, lineage_id, state) -> tuple:
        direction_status = state.get("direction_status") or ("proposed" if kind == "direction" else None)
        return (node_id, project_id, state.get("parent_id"), lineage_id, kind, json.dumps(payload),
                state.get("life_state", "pending"), direction_status, int(state.get("working", False)),
                state.get("rejection_reason"), json.dumps(state["rebuttal"]) if state.get("rebuttal") else None,
                now(), now())

    def _validate_node(self, kind: str, life_state: str, direction_status: str | None) -> None:
        if kind not in NODE_KINDS or life_state not in LIFE_STATES:
            raise ValueError("invalid node kind or life state")
        if kind != "direction" and direction_status is not None:
            raise ValueError("only direction nodes have direction status")
        if direction_status is not None and direction_status not in DIRECTION_STATES:
            raise ValueError("invalid direction status")

    def _lineage(self, parent_id: str | None, fallback: str) -> str:
        return self.node(parent_id)["lineage_id"] if parent_id else fallback

    def node(self, node_id: str) -> dict:
        return self._one("SELECT * FROM nodes WHERE id=?", (node_id,))

    def nodes(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM nodes WHERE project_id=? ORDER BY created_at", (project_id,))

    def update_node(self, node_id: str, payload: dict | None = None, **state) -> dict:
        node = self.node(node_id)
        self._validate_transition(node, state)
        fields = self._node_updates(node, payload, state)
        assignments = ",".join(f"{key}=?" for key in fields)
        with self.db.connect() as connection:
            connection.execute(f"UPDATE nodes SET {assignments} WHERE id=?", (*fields.values(), node_id))
        return self.node(node_id)

    def _validate_transition(self, node: dict, state: dict) -> None:
        target = state.get("direction_status")
        if target and node["kind"] != "direction":
            raise ValueError("only direction nodes have direction status")
        if target and node["direction_status"] != "proposed":
            raise ValueError("direction status is terminal")
        if target and target not in {"supported", "refuted"}:
            raise ValueError("direction must resolve to supported or refuted")

    def _node_updates(self, node: dict, payload: dict | None, state: dict) -> dict:
        fields = {key: state[key] for key in ("life_state", "direction_status", "rejection_reason") if key in state}
        if payload is not None:
            fields["payload"] = json.dumps(payload)
        if "working" in state:
            fields["working"] = int(state["working"])
        if "rebuttal" in state:
            fields["rebuttal"] = json.dumps(state["rebuttal"])
        fields["updated_at"] = now()
        return fields

    def admit_node(self, node_id: str, payload: dict | None = None) -> dict:
        return self.update_node(node_id, payload, life_state="admitted", working=False, rejection_reason=None)

    def ghost_node(self, node_id: str, reason: str, rebuttal: dict | None = None) -> dict:
        if not reason.strip():
            raise ValueError("ghost node requires a rejection reason")
        return self.update_node(node_id, life_state="ghost", working=False,
                                rejection_reason=reason.strip(), rebuttal=rebuttal)

    def set_working(self, node_id: str, working: bool) -> dict:
        return self.update_node(node_id, working=working)

    def add_edge(self, source: str, target: str, polarity: str) -> dict:
        if polarity not in EDGE_POLARITIES:
            raise ValueError("edge polarity must be supports or refutes")
        self._validate_edge_nodes(source, target)
        values = (source, target, polarity, now())
        with self.db.connect() as connection:
            connection.execute("INSERT INTO edges VALUES(?,?,?,?)", values)
        return {"source": source, "target": target, "polarity": polarity}

    def _validate_edge_nodes(self, source: str, target: str) -> None:
        left, right = self.node(source), self.node(target)
        if left["project_id"] != right["project_id"]:
            raise ValueError("edge nodes must belong to one project")

    def edges(self, project_id: str) -> list[dict]:
        sql = "SELECT e.* FROM edges e JOIN nodes n ON n.id=e.source WHERE n.project_id=? ORDER BY e.created_at"
        return self._many(sql, (project_id,))

    def search(self, project_id: str, query: str) -> list[dict]:
        terms = " OR ".join(part for part in query.split() if part)
        if not terms:
            return []
        sql = "SELECT n.* FROM node_fts f JOIN nodes n ON n.id=f.node_id WHERE f.project_id=? AND node_fts MATCH ?"
        return self._many(sql, (project_id, terms))

    def _store_embedding(self, connection, node_id: str, payload: dict) -> None:
        if self.embedding is None:
            return
        vector = self.embedding(self._node_text(payload))
        connection.execute("INSERT INTO node_embeddings VALUES(?,?)", (node_id, json.dumps(vector)))

    def embedding_for(self, node_id: str) -> list[float] | None:
        rows = self._rows("SELECT vector FROM node_embeddings WHERE node_id=?", (node_id,))
        return json.loads(rows[0]["vector"]) if rows else None

    def add_message(self, project_id: str, node_id: str, role: str, content: str) -> dict:
        if role not in {"user", "assistant"} or not content.strip():
            raise ValueError("message requires a valid role and content")
        with self.db.connect() as connection:
            cursor = connection.execute("INSERT INTO messages(project_id,node_id,role,content,created_at) VALUES(?,?,?,?,?)",
                                        (project_id, node_id, role, content.strip(), now()))
        return self._one("SELECT * FROM messages WHERE id=?", (cursor.lastrowid,))

    def messages(self, project_id: str, node_id: str) -> list[dict]:
        return self._many("SELECT * FROM messages WHERE project_id=? AND node_id=? ORDER BY id",
                          (project_id, node_id))

    def clear_messages(self, project_id: str, node_id: str) -> None:
        with self.db.connect() as connection:
            connection.execute("DELETE FROM messages WHERE project_id=? AND node_id=?", (project_id, node_id))

    def _node_text(self, payload: dict) -> str:
        return " ".join(str(payload.get(key, "")) for key in ("title", "text", "summary") if payload.get(key))

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
