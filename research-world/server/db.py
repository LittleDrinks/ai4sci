from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("RESEARCH_WORLD_DB", ROOT / "data" / "research-world.db"))


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, question TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
  summary TEXT NOT NULL, content_json TEXT NOT NULL, status TEXT NOT NULL, audit TEXT NOT NULL,
  actor_kind TEXT NOT NULL, actor_id TEXT NOT NULL, source_job_id TEXT, created_at TEXT NOT NULL,
  admitted_at TEXT
);
CREATE TABLE IF NOT EXISTS edges (
  project_id TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL, relation TEXT NOT NULL,
  PRIMARY KEY (project_id, source, target, relation)
);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, kind TEXT NOT NULL,
  actor_kind TEXT NOT NULL, actor_id TEXT NOT NULL, entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runtimes (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, sdk TEXT NOT NULL, version TEXT NOT NULL,
  capabilities_json TEXT NOT NULL, status TEXT NOT NULL, last_seen TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, runtime_id TEXT NOT NULL, model TEXT NOT NULL,
  instructions TEXT NOT NULL, capabilities_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, agent_id TEXT NOT NULL, kind TEXT NOT NULL,
  subject_id TEXT, prompt TEXT NOT NULL, status TEXT NOT NULL, attempt_id TEXT, runtime_id TEXT,
  revision INTEGER NOT NULL, review_mode TEXT, review_scope TEXT, review_feedback TEXT,
  result_text TEXT, output_node_id TEXT, output_artifact_id TEXT, error TEXT,
  created_at TEXT NOT NULL, started_at TEXT, heartbeat_at TEXT, lease_expires_at TEXT,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, job_id TEXT NOT NULL, node_id TEXT,
  title TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL, content_type TEXT NOT NULL,
  path TEXT NOT NULL, sha256 TEXT NOT NULL, agent_id TEXT NOT NULL, created_at TEXT NOT NULL,
  reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS workspace_commands (
  id TEXT PRIMARY KEY, runtime_id TEXT NOT NULL, job_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
  action TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS jobs_lease_idx ON jobs(status, lease_expires_at);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


def rows(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return [dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]


def row(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    values = rows(sql, params)
    return values[0] if values else None


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with connect() as connection:
        connection.execute(sql, tuple(params))


def decode(value: str | None, default: Any) -> Any:
    return json.loads(value) if value else default
