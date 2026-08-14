from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,root TEXT NOT NULL,question TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_snapshots(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,artifact_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,sha256 TEXT UNIQUE NOT NULL,media_type TEXT NOT NULL,size INTEGER NOT NULL,path TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_snapshots(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,url TEXT NOT NULL,artifact_id TEXT NOT NULL,locator TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS generations(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,run_id TEXT,ordinal INTEGER NOT NULL,parent_id TEXT,strategy_change TEXT,package_id TEXT,created_at TEXT NOT NULL,UNIQUE(run_id,ordinal));
CREATE TABLE IF NOT EXISTS packages(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,generation_id TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,admitted_at TEXT);
CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,generation_id TEXT,package_id TEXT,kind TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,admitted_at TEXT);
CREATE TABLE IF NOT EXISTS edges(source TEXT NOT NULL,target TEXT NOT NULL,type TEXT NOT NULL,package_id TEXT NOT NULL,PRIMARY KEY(source,target,type));
CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,package_id TEXT NOT NULL,reviewer TEXT NOT NULL,decision TEXT NOT NULL,feedback TEXT NOT NULL,category TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(package_id,reviewer));
CREATE TABLE IF NOT EXISTS node_embeddings(node_id TEXT PRIMARY KEY,vector TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,question_id INTEGER NOT NULL,status TEXT NOT NULL,apply_selected INTEGER NOT NULL,project_snapshot_id TEXT,final_markdown_id TEXT,final_html_id TEXT,created_at TEXT NOT NULL,completed_at TEXT);
CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,generation_id TEXT NOT NULL,snapshot_id TEXT NOT NULL,actor TEXT NOT NULL,status TEXT NOT NULL,workspace TEXT,wire_artifact_id TEXT,context_artifact_id TEXT,manifest_artifact_id TEXT,created_at TEXT NOT NULL,completed_at TEXT);
CREATE TABLE IF NOT EXISTS attempt_artifacts(attempt_id TEXT NOT NULL,artifact_id TEXT NOT NULL,role TEXT NOT NULL,PRIMARY KEY(attempt_id,artifact_id));
CREATE TABLE IF NOT EXISTS task_tokens(token_hash TEXT PRIMARY KEY,attempt_id TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,generation_id TEXT,attempt_id TEXT,actor TEXT NOT NULL,type TEXT NOT NULL,time TEXT NOT NULL,entity TEXT NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tool_receipts(id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL,server TEXT NOT NULL,tool TEXT NOT NULL,arguments TEXT NOT NULL,result TEXT NOT NULL,error TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS executions(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,attempt_id TEXT NOT NULL,environment_id TEXT NOT NULL,image_digest TEXT NOT NULL,command TEXT NOT NULL,input_artifact_id TEXT NOT NULL,input_hash TEXT NOT NULL,seed INTEGER NOT NULL,spec TEXT NOT NULL,exit_code INTEGER NOT NULL,output_artifact_id TEXT NOT NULL,output_hash TEXT NOT NULL,usage TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS environments(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,attempt_id TEXT NOT NULL,image_digest TEXT NOT NULL,lock_artifact_id TEXT NOT NULL,setup TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_cycles(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,direction_id TEXT NOT NULL,run_id TEXT NOT NULL,status TEXT NOT NULL,brief TEXT NOT NULL,created_at TEXT NOT NULL,completed_at TEXT);
CREATE TABLE IF NOT EXISTS work_items(id TEXT PRIMARY KEY,cycle_id TEXT NOT NULL,project_id TEXT NOT NULL,direction_id TEXT NOT NULL,generation_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,input TEXT NOT NULL,output TEXT NOT NULL,created_at TEXT NOT NULL,completed_at TEXT);
CREATE TABLE IF NOT EXISTS workflow_steps(id TEXT PRIMARY KEY,work_item_id TEXT NOT NULL,ordinal INTEGER NOT NULL,role TEXT NOT NULL,status TEXT NOT NULL,attempt_id TEXT,output TEXT NOT NULL,started_at TEXT,completed_at TEXT,UNIQUE(work_item_id,ordinal));
CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY,work_item_id TEXT NOT NULL,step_id TEXT NOT NULL,reviewer TEXT NOT NULL,check_id TEXT NOT NULL,severity TEXT NOT NULL,evidence TEXT NOT NULL,recommendation TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_messages(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,node_id TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_item_attempts(work_item_id TEXT NOT NULL,attempt_id TEXT NOT NULL,PRIMARY KEY(work_item_id,attempt_id));
CREATE TABLE IF NOT EXISTS attempt_logs(attempt_id TEXT PRIMARY KEY,artifact_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_calls(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,attempt_id TEXT NOT NULL,role TEXT NOT NULL,log_artifact_id TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS node_fts USING fts5(node_id UNINDEXED,project_id UNINDEXED,text);
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
