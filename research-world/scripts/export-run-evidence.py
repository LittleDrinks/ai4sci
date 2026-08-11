from __future__ import annotations

import argparse
import json
from pathlib import Path

from server.cli import default_world


def rows(connection, sql: str, run_id: str) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, (run_id,))]


def run_evidence(world, run_id: str) -> dict:
    with world.db.connect() as connection:
        run = dict(connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
        generations = generation_evidence(connection, run_id)
        attempts = attempt_evidence(connection, run_id)
        receipts = receipt_evidence(connection, run_id)
        events = event_evidence(connection, run_id)
    return {"schema_version": "1", "run": run, "generations": generations,
            "attempts": attempts, "tool_receipts": receipts, "events": events}


def generation_evidence(connection, run_id: str) -> list[dict]:
    sql = """SELECT g.*,p.status package_status,p.payload package_payload
             FROM generations g JOIN packages p ON p.id=g.package_id
             WHERE g.run_id=? ORDER BY g.ordinal"""
    generations = rows(connection, sql, run_id)
    for generation in generations:
        generation["package"] = json.loads(generation.pop("package_payload"))
        generation["reviews"] = package_reviews(connection, generation["package_id"])
    return generations


def package_reviews(connection, package_id: str) -> list[dict]:
    sql = "SELECT reviewer,decision,feedback,created_at FROM reviews WHERE package_id=? ORDER BY reviewer"
    return [dict(row) for row in connection.execute(sql, (package_id,))]


def attempt_evidence(connection, run_id: str) -> list[dict]:
    sql = """SELECT id,generation_id,actor,status,wire_artifact_id,context_artifact_id,
                    created_at,completed_at FROM attempts WHERE run_id=? ORDER BY created_at"""
    return rows(connection, sql, run_id)


def receipt_evidence(connection, run_id: str) -> list[dict]:
    sql = """SELECT t.id,t.server,t.tool,t.error,t.created_at,a.actor,a.generation_id
             FROM tool_receipts t JOIN attempts a ON a.id=t.attempt_id
             WHERE a.run_id=? ORDER BY t.created_at"""
    return rows(connection, sql, run_id)


def event_evidence(connection, run_id: str) -> list[dict]:
    sql = """SELECT event_id,generation_id,attempt_id,actor,type,time,entity,payload
             FROM events WHERE run_id=? ORDER BY event_id"""
    evidence = rows(connection, sql, run_id)
    for event in evidence:
        event["payload"] = json.loads(event["payload"])
    return evidence


def write_evidence(run_id: str, output: Path, world=None) -> None:
    world = world or default_world()
    evidence = run_evidence(world, run_id)
    output.mkdir(parents=True, exist_ok=True)
    run = evidence["run"]
    (output / "orbits-49-run.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (output / "orbits-49-report.md").write_bytes(world.artifacts.read(run["final_markdown_id"]))
    (output / "orbits-49-report.html").write_bytes(world.artifacts.read(run["final_html_id"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--output", type=Path, default=Path("evidence"))
    args = parser.parse_args()
    write_evidence(args.run_id, args.output)


if __name__ == "__main__":
    main()
