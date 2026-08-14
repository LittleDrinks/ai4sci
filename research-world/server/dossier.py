from __future__ import annotations

import json
from pathlib import Path

from .research import ResearchState


class DossierExporter:
    def __init__(self, world):
        self.world = world
        self.state = ResearchState(world)

    def export(self, project_id: str, cycle_id: str) -> dict:
        project = self.world.project(project_id)
        cycle = self.state.cycle(cycle_id)
        payload = self._payload(project, cycle)
        root = Path(project["root"]) / "research-dossier"
        root.mkdir(parents=True, exist_ok=True)
        payload["log_files"] = self._write_logs(root, payload["attempts"])
        payload["code_files"] = self._write_code(Path(project["root"]), payload["work_items"])
        json_path = root / "cycle.json"
        markdown_path = root / "README.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(self._markdown(payload), encoding="utf-8")
        return {"json": str(json_path), "markdown": str(markdown_path)}

    def _write_logs(self, root: Path, attempts: list[dict]) -> list[str]:
        target = root / "logs"
        target.mkdir(exist_ok=True)
        return [self._write_log(target, attempt) for attempt in attempts if attempt.get("log_artifact_id")]

    def _write_log(self, root: Path, attempt: dict) -> str:
        path = root / f"{attempt['id'].replace(':', '-')}.log"
        path.write_bytes(self._complete_log(attempt))
        return path.relative_to(root.parent).as_posix()

    def _complete_log(self, attempt: dict) -> bytes:
        content = self.world.artifacts.read(attempt["log_artifact_id"])
        if b'"type": "attempt_output"' in content:
            return content
        values = [("attempt_input", attempt.get("context_artifact_id")), ("attempt_output", attempt.get("wire_artifact_id"))]
        return content + b"".join(self._artifact_log(kind, artifact_id) for kind, artifact_id in values if artifact_id)

    def _artifact_log(self, kind: str, artifact_id: str) -> bytes:
        content = json.loads(self.world.artifacts.read(artifact_id))
        return (json.dumps({"type": kind, "content": content}, ensure_ascii=False) + "\n").encode()

    def _write_code(self, project: Path, work: list[dict]) -> list[str]:
        files = [item["output"].get("plan", {}).get("files", {}) for item in work if item["kind"] == "experiment"]
        return [self._write_code_file(project, name, content) for values in files for name, content in values.items()]

    def _write_code_file(self, project: Path, name: str, content: str) -> str:
        root = project / "research-code"
        root.mkdir(exist_ok=True)
        path = root / Path(name).name
        path.write_text(content, encoding="utf-8")
        return path.relative_to(project).as_posix()

    def _payload(self, project: dict, cycle: dict) -> dict:
        direction = self.state.node(cycle["direction_id"])
        work = [item for item in self.state.work_items(project["id"]) if item["cycle_id"] == cycle["id"]]
        attempts = [item for item in self.state.project_attempts(project["id"]) if item["work_item_id"] in {value["id"] for value in work}]
        return {"project": self._project(project), "direction": direction, "cycle": cycle,
                "work_items": work, "attempts": attempts, "findings": self._findings(work)}

    def _project(self, project: dict) -> dict:
        return {key: project[key] for key in ("id", "name", "question", "created_at")}

    def _findings(self, work: list[dict]) -> list[dict]:
        return [finding for item in work for finding in item["findings"]]

    def _markdown(self, payload: dict) -> str:
        brief = payload["cycle"]["brief"]
        sections = [f"# {payload['project']['name']}", payload["project"]["question"],
                    f"## Direction\n{payload['direction']['payload']['title']}\n\n{payload['direction']['payload']['rationale']}",
                    self._list("Learned", brief.get("learned", [])), self._list("Evidence", brief.get("evidence", [])),
                    self._list("Limitations", brief.get("limitations", [])), self._list("Open Questions", brief.get("open_questions", [])),
                    self._list("Next Moves", brief.get("next_moves", [])), self._artifacts(payload),
                    self._work(payload["work_items"]), self._review(payload["findings"])]
        return "\n\n".join(section for section in sections if section).strip() + "\n"

    def _list(self, title: str, values: list) -> str:
        return f"## {title}\n" + "\n".join(f"- {value}" for value in values) if values else ""

    def _work(self, values: list[dict]) -> str:
        rows = ["## Work Items"]
        rows.extend(f"- `{item['kind']}`: {item['status']} ({len(item['steps'])} steps)" for item in values)
        return "\n".join(rows)

    def _artifacts(self, payload: dict) -> str:
        values = [*(f"Log: `{path}`" for path in payload["log_files"]), *(f"Code: `{path}`" for path in payload["code_files"])]
        return self._list("Artifacts", values)

    def _review(self, values: list[dict]) -> str:
        if not values:
            return ""
        rows = ["## Review Findings"]
        rows.extend(f"- `{item['severity']}` `{item['check_id']}`: {item['recommendation']}" for item in values)
        return "\n".join(rows)
