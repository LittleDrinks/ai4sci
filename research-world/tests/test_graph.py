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
    return {"text": "An ideal two-body orbit does not dissipate energy.", "citations": [citation]}


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


def test_hybrid_search_expands_admitted_neighbors(world, project):
    generation = world.create_generation(project["id"], 0)
    candidate = world.submit_package(project["id"], package(world, project, generation["id"]))
    world.review_package(candidate["id"], "a", "approve", "ok")
    world.review_package(candidate["id"], "b", "approve", "ok")
    results = world.search(project["id"], "ideal orbit energy", embed=lambda _: [1.0, 0.0])
    assert len(results) <= 40
    assert {node["kind"] for node in results} >= {"claim", "source", "result"}
