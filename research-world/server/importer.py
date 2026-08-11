from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field


class ManifestSource(BaseModel):
    path: str
    sha256: str


class ManifestNode(BaseModel):
    ref: str
    kind: str
    title: str
    summary: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class ResearchManifest(BaseModel):
    schema_version: Literal[1]
    title: str
    question: str
    root_ref: str
    sources: list[ManifestSource]
    nodes: list[ManifestNode]


def load_manifest(path: Path) -> ResearchManifest:
    return ResearchManifest.model_validate_json(path.read_text(encoding="utf-8"))


def topological_nodes(manifest: ResearchManifest) -> list[ManifestNode]:
    pending = {node.ref: node for node in manifest.nodes}
    validate_refs(manifest, pending)
    admitted, ordered = {manifest.root_ref}, []
    while pending:
        ready = sorted(ref for ref, node in pending.items() if set(node.dependencies) <= admitted)
        if not ready:
            raise ValueError("manifest dependencies contain a cycle")
        for ref in ready:
            ordered.append(pending.pop(ref))
            admitted.add(ref)
    return ordered


def validate_refs(manifest: ResearchManifest, nodes: dict[str, ManifestNode]) -> None:
    if len(nodes) != len(manifest.nodes):
        raise ValueError("manifest node refs must be unique")
    known = set(nodes) | {manifest.root_ref}
    unknown = sorted({ref for node in nodes.values() for ref in node.dependencies} - known)
    if unknown:
        raise ValueError(f"unknown dependency refs: {', '.join(unknown)}")


def import_manifest(manifest: ResearchManifest, client: Any, project_id: str | None,
                    actor_id: str) -> dict[str, Any]:
    project_id, root_id = resolve_project(manifest, client, project_id, actor_id)
    identities, admitted = {manifest.root_ref: root_id}, []
    for node in topological_nodes(manifest):
        payload = node_payload(node, project_id, identities)
        result = command(client, actor_id, "submit_node", payload)
        approve_pending(client, actor_id, result)
        identities[node.ref] = result["id"]
        admitted.append(result["id"])
    return {"project_id": project_id, "root_id": root_id, "nodes": len(admitted),
            "dependencies": sum(len(node.dependencies) for node in manifest.nodes)}


def resolve_project(manifest: ResearchManifest, client: Any, project_id: str | None,
                    actor_id: str) -> tuple[str, str]:
    if not project_id:
        result = command(client, actor_id, "create_project",
                         {"title": manifest.title, "question": manifest.question})
        return result["id"], result["root_id"]
    response = client.get("/api/bootstrap", params={"project_id": project_id})
    response.raise_for_status()
    roots = [node for node in response.json()["nodes"] if node["kind"] == "question"]
    if len(roots) != 1:
        raise ValueError("target project must have exactly one question node")
    return project_id, roots[0]["id"]


def node_payload(node: ManifestNode, project_id: str,
                 identities: dict[str, str]) -> dict[str, Any]:
    return {"project_id": project_id, "kind": node.kind, "title": node.title,
            "summary": node.summary, "content": node.content,
            "dependencies": [identities[ref] for ref in node.dependencies]}


def approve_pending(client: Any, actor_id: str, node: dict[str, Any]) -> None:
    if node["audit"] == "pending":
        command(client, actor_id, "review_node", {"node_id": node["id"], "decision": "approve"})


def command(client: Any, actor_id: str, kind: str, payload: dict) -> dict[str, Any]:
    body = {"type": kind, "actor": {"kind": "human", "id": actor_id}, "payload": payload}
    response = client.post("/api/commands", json=body)
    response.raise_for_status()
    return response.json()["result"]


def import_to_server(path: Path, server: str, project_id: str | None,
                     actor_id: str) -> dict[str, Any]:
    with httpx.Client(base_url=server, timeout=60) as client:
        return import_manifest(load_manifest(path), client, project_id, actor_id)
