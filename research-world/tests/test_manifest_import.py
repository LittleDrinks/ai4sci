from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from server import db
from server.app import app
from server.importer import import_manifest, load_manifest, topological_nodes


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "music-directions.json"


def file_sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_music_manifest_is_real_and_meaningful():
    manifest = load_manifest(FIXTURE)
    ordered = topological_nodes(manifest)
    positions = {ref: index for index, ref in enumerate([manifest.root_ref, *[node.ref for node in ordered]])}
    assert len(manifest.nodes) + 1 == 166
    assert sum(len(node.dependencies) for node in manifest.nodes) == 246
    assert len({node.kind for node in manifest.nodes}) == 8
    assert all(source.sha256 == file_sha(source.path) for source in manifest.sources)
    assert all(positions[ref] < positions[node.ref] for node in ordered for ref in node.dependencies)


def test_full_manifest_import_is_topologically_admitted(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "manifest.db")
    with TestClient(app) as client:
        result = import_manifest(load_manifest(FIXTURE), client, None, "fixture-import")
        state = client.get("/api/bootstrap", params={"project_id": result["project_id"]}).json()
    assert result["nodes"] == 165
    assert result["dependencies"] == 246
    assert len(state["nodes"]) == 166
    assert len(state["edges"]) == 246
    assert all(node["status"] == "admitted" and node["audit"] == "approve" for node in state["nodes"])
    admitted = {node["id"] for node in state["nodes"]}
    assert {edge["source"] for edge in state["edges"]} <= admitted
    assert {edge["target"] for edge in state["edges"]} <= admitted
