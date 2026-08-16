from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects(
  id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, root TEXT NOT NULL,
  question TEXT NOT NULL, auto INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parent_id TEXT REFERENCES nodes(id), lineage_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('question','source','direction','experiment')),
  payload TEXT NOT NULL, life_state TEXT NOT NULL CHECK(life_state IN ('pending','admitted','ghost')),
  direction_status TEXT CHECK(direction_status IN ('proposed','supported','refuted')),
  working INTEGER NOT NULL DEFAULT 0, rejection_reason TEXT, rebuttal TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edges(
  source TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  target TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  polarity TEXT NOT NULL CHECK(polarity IN ('supports','refutes')),
  created_at TEXT NOT NULL, PRIMARY KEY(source,target,polarity)
);
CREATE VIRTUAL TABLE IF NOT EXISTS node_fts USING fts5(
  node_id UNINDEXED, project_id UNINDEXED, text
);
CREATE TABLE IF NOT EXISTS node_embeddings(
  node_id TEXT PRIMARY KEY REFERENCES nodes(id) ON DELETE CASCADE, vector TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('user','assistant')),
  content TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
