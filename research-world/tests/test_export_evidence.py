from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "export-run-evidence.py"


def exporter():
    spec = importlib.util.spec_from_file_location("export_run_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exports_run_and_final_reports(world, tmp_path):
    project = world.create_project("orbits", tmp_path, "Why?")
    run = world.create_run(project["id"], 49, False)
    markdown = world.add_artifact(b"# Report", "text/markdown")
    html = world.add_artifact(b"<h1>Report</h1>", "text/html")
    with world.db.connect() as connection:
        connection.execute(
            "UPDATE runs SET final_markdown_id=?,final_html_id=? WHERE id=?",
            (markdown["id"], html["id"], run["id"]),
        )
    exporter().write_evidence(run["id"], tmp_path / "evidence", world)
    data = json.loads((tmp_path / "evidence/orbits-49-run.json").read_text())
    assert data["run"]["id"] == run["id"]
    assert (tmp_path / "evidence/orbits-49-report.md").read_text() == "# Report"
