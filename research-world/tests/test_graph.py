import pytest

from server.world import InvalidPackage


def package(world, project, generation_id):
    source = world.add_artifact(b"Line one.\nLine two supports the claim.\n", "text/plain")
    snapshot = world.add_source_snapshot(
        project["id"], "https://example.test/orbits", source, {"line_start": 1, "line_end": 2}
    )
    return {
        "generation_id": generation_id,
        "strategy": "Check whether the premise has a dissipative mechanism.",
        "sources": [{"snapshot_id": snapshot["id"], "artifact_id": source["id"], "title": "Orbital mechanics"}],
        "claims": [claim(snapshot, source)],
        "artifacts": [{"artifact_id": source["id"], "role": "source_text"}],
        "code": [],
        "no_code_reason": "The claim is resolved analytically from cited mechanics.",
    }


def claim(snapshot, source):
    citation = {
        "source_snapshot_id": snapshot["id"],
        "artifact_id": source["id"],
        "locator": {"line_start": 2, "line_end": 2},
    }
    return {"kind": "evidence", "text": "An ideal two-body orbit does not dissipate energy.", "citations": [citation]}


def test_package_is_isolated_then_atomically_admitted(world, project):
    generation = world.create_generation(project["id"], 0)
    candidate = world.submit_package(project["id"], package(world, project, generation["id"]))
    assert world.search(project["id"], "dissipate") == []
    world.review_package(candidate["id"], "reviewer-a", "approve", "Citations resolve.")
    assert world.search(project["id"], "dissipate") == []
    world.review_package(candidate["id"], "reviewer-b", "approve", "Mechanism is sound.")
    nodes = world.search(project["id"], "dissipate")
    assert {node["kind"] for node in nodes} >= {"claim", "result"}
    assert {node["status"] for node in world.package_nodes(candidate["id"])} == {"admitted"}


def test_submission_rejects_unresolvable_citation(world, project):
    generation = world.create_generation(project["id"], 0)
    value = package(world, project, generation["id"])
    value["claims"][0]["citations"][0]["locator"] = {"line_start": 99, "line_end": 100}
    with pytest.raises(InvalidPackage, match="locator"):
        world.submit_package(project["id"], value)


def test_submission_rejects_unresolvable_package_sources(world, project):
    generation = world.create_generation(project["id"], 0)
    value = package(world, project, generation["id"])
    del value["sources"][0]["artifact_id"]
    with pytest.raises(InvalidPackage, match="source"):
        world.submit_package(project["id"], value)


def test_submission_rejects_code_without_verified_execution(world, project):
    generation = world.create_generation(project["id"], 0)
    value = package(world, project, generation["id"])
    value["code"] = [{"execution_id": "execution:missing", "artifact_id": value["artifacts"][0]["artifact_id"]}]
    with pytest.raises(InvalidPackage, match="execution"):
        world.submit_package(project["id"], value)


def test_submission_requires_claim_classification(world, project):
    generation = world.create_generation(project["id"], 0)
    value = package(world, project, generation["id"])
    del value["claims"][0]["kind"]
    with pytest.raises(InvalidPackage, match="claim kind"):
        world.submit_package(project["id"], value)


def test_hybrid_search_expands_admitted_neighbors(world, project):
    generation = world.create_generation(project["id"], 0)
    candidate = world.submit_package(project["id"], package(world, project, generation["id"]))
    world.review_package(candidate["id"], "a", "approve", "ok")
    world.review_package(candidate["id"], "b", "approve", "ok")
    results = world.search(project["id"], "ideal orbit energy", embed=lambda _: [1.0, 0.0])
    assert len(results) <= 40
    assert {node["kind"] for node in results} >= {"claim", "source", "result"}


def test_hybrid_search_does_not_expand_pending_neighbors(world, project):
    generation = world.create_generation(project["id"], 0)
    world.submit_package(project["id"], package(world, project, generation["id"]))
    results = world.search(project["id"], "planetary orbits")
    assert all(node["status"] == "admitted" for node in results)


def test_support_edges_follow_claim_citations(world, project):
    generation = world.create_generation(project["id"], 0)
    value = package(world, project, generation["id"])
    artifact = world.add_artifact(b"Other evidence.\n", "text/plain")
    snapshot = world.add_source_snapshot(project["id"], "https://example.test/other", artifact, {"line_start": 1, "line_end": 1})
    value["sources"].append({"snapshot_id": snapshot["id"], "artifact_id": artifact["id"], "title": "Other"})
    value["claims"].append({"kind": "evidence", "text": "A separate claim.", "citations": [{"source_snapshot_id": snapshot["id"], "artifact_id": artifact["id"], "locator": {"line_start": 1, "line_end": 1}}]})
    candidate = world.submit_package(project["id"], value)
    world.review_package(candidate["id"], "a", "approve", "ok")
    world.review_package(candidate["id"], "b", "approve", "ok")
    supports = [edge for edge in world.project_edges(project["id"]) if edge["type"] == "supports"]
    assert len(supports) == 2
