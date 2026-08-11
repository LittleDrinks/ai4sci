from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

import markdown as markdown_renderer

from .artifacts import now
from .task_gateway import TaskGateway
from .world import InvalidPackage, World


class Orchestrator:
    def __init__(self, world: World, agents, broker, workspaces: Path, controller):
        self.world = world
        self.agents = agents
        self.broker = broker
        self.workspaces = workspaces
        self.controller = controller
        self.pending = {}
        self.repairs = {}

    def execute(self, run_id: str) -> dict:
        run = self._start(run_id)
        parent = None
        for ordinal in range(3):
            generation, package = self._generation(run, ordinal, parent)
            outcome = self._review(run, generation, package)
            if outcome == "conflict":
                return self._finish(run_id, "human_conflict")
            parent = generation
            if ordinal >= 1 and outcome == "approve":
                return self._report(run, generation)
        return self._finish(run_id, "terminated")

    def resume(self, run_id: str) -> dict:
        run = self.world.update_run(run_id, "running", completed_at=None)
        generation = self.world.generations(run_id)[-1]
        self._event(run, generation, None, "system", "run_resumed", "run", run_id, {})
        package = self._resume_package(run, generation)
        outcome = self._review(run, generation, package)
        if outcome == "conflict":
            return self._finish(run_id, "human_conflict")
        if generation["ordinal"] >= 1 and outcome == "approve":
            return self._report(run, generation)
        return self._continue(run, generation)

    def _resume_package(self, run: dict, generation: dict) -> dict:
        if generation["package_id"]:
            return self.world.package(generation["package_id"])
        generations = self.world.generations(run["id"])
        parent = generations[-2] if len(generations) > 1 else None
        package = self._produce(run, generation, parent)
        change = package["payload"].get("strategy_change") or generation["strategy_change"]
        self.world.update_generation(generation["id"], package["id"], change)
        return package

    def resolve_conflict(self, run_id: str, feedback: str) -> dict:
        run = self.world.run(run_id)
        if run["status"] != "human_conflict":
            raise ValueError("run is not awaiting human resolution")
        parent = self.world.generations(run_id)[-1]
        self.world.update_run(run_id, "running", completed_at=None)
        self._event(run, parent, None, "human", "conflict_resolved", "run", run_id, {"decision": "new_generation", "feedback": feedback})
        return self._continue(self.world.run(run_id), parent)

    def approve_conflict(self, run_id: str, feedback: str) -> dict:
        run = self.world.run(run_id)
        if run["status"] != "human_conflict":
            raise ValueError("run is not awaiting human resolution")
        generation = self.world.generations(run_id)[-1]
        package = self.world.package(generation["package_id"])
        if package["status"] == "admitted":
            return self._human_admit_report(run, generation, feedback)
        self.world.human_admit_package(package["id"], feedback)
        self.world.update_run(run_id, "running", completed_at=None)
        self._event(run, generation, None, "human", "conflict_resolved", "package", package["id"], {"decision": "approve", "feedback": feedback})
        return self._report(self.world.run(run_id), generation) if generation["ordinal"] >= 1 else self._continue(self.world.run(run_id), generation)

    def _human_admit_report(self, run: dict, generation: dict, feedback: str) -> dict:
        attempt = self.world.attempts(run["id"], actor="reporter")[-1]
        output = json.loads(self.world.artifacts.read(attempt["wire_artifact_id"]))["output"]
        md, page = (self.world.artifact_value(output[key]) for key in ("markdown", "html"))
        self.world.admit_artifact_node(run["project_id"], generation["id"], md, "final_markdown")
        self.world.admit_artifact_node(run["project_id"], generation["id"], page, "final_html")
        self.world.update_run(run["id"], "completed", final_markdown_id=md["id"], final_html_id=page["id"], completed_at=now())
        self._event(run, generation, attempt, "human", "report_admitted", "artifact", page["id"], {"feedback": feedback})
        self._apply_if_selected(run, generation, attempt)
        return self.world.run(run["id"])

    def _continue(self, run: dict, parent: dict) -> dict:
        for ordinal in range(parent["ordinal"] + 1, 3):
            generation, package = self._generation(run, ordinal, parent)
            outcome = self._review(run, generation, package)
            if outcome == "conflict":
                return self._finish(run["id"], "human_conflict")
            parent = generation
            if ordinal >= 1 and outcome == "approve":
                return self._report(run, generation)
        return self._finish(run["id"], "terminated")

    def _start(self, run_id: str) -> dict:
        run = self.world.run(run_id)
        snapshot = self.world.sync_project(run["project_id"])
        self.world.update_run(run_id, "running", project_snapshot_id=snapshot["id"])
        self._event(run, None, None, "system", "run_started", "run", run_id, {"snapshot_id": snapshot["id"]})
        return self.world.run(run_id)

    def _generation(self, run: dict, ordinal: int, parent: dict | None) -> tuple[dict, dict]:
        change = "Challenge the admitted parent and address reviewer feedback." if parent else None
        generation = self.world.create_generation(run["project_id"], ordinal, parent and parent["id"], change, run["id"])
        self._event(run, generation, None, "system", "generation_started", "generation", generation["id"], {})
        package = self._produce(run, generation, parent)
        self.world.update_generation(generation["id"], package["id"], package["payload"].get("strategy_change") or change)
        return self.world.generations(run["id"])[-1], package

    def _produce(self, run: dict, generation: dict, parent: dict | None) -> dict:
        attempt, workspace = self._attempt(run, generation, "producer")
        sources = self._sources(run, generation, attempt, workspace, parent)
        context = self._producer_context(run, generation, parent, sources)
        context["attempt_id"] = attempt["id"]
        context["generation_id"] = generation["id"]
        for revision in range(3):
            try:
                package = self.agents.produce(context, workspace)
                payload = package["payload"]
                self.pending[generation["id"]] = (attempt, workspace, context, payload)
                return package
            except (InvalidPackage, KeyError, TypeError, ValueError) as error:
                context["mechanical_feedback"] = str(error)
                self._event(run, generation, attempt, "system", "mechanical_revision", "attempt", attempt["id"], {"error": str(error)})
        raise InvalidPackage("mechanical revision limit exceeded")

    def _sources(self, run: dict, generation: dict, attempt: dict, workspace: Path, parent: dict | None) -> list[dict]:
        project = self.world.project(run["project_id"])
        queries = self._search_queries(project, parent, workspace)
        results = [value for query in queries for value in self.broker.search(project, query, attempt["id"])]
        candidates = list({value["url"]: value for value in results}.values())
        selected = self._select_sources(project, parent, candidates, workspace)
        acquired = self._acquire_sources(selected, attempt["id"])
        if len(acquired) < min(2, len(selected)):
            raise ValueError("source acquisition requires two extracted sources")
        return [self._snapshot_source(project, value, attempt["id"]) for value in acquired]

    def _select_sources(self, project, parent, candidates, workspace) -> list[dict]:
        context = {"question": project["question"], "candidates": candidates}
        if parent:
            context["review_feedback"] = self.world.reviews(parent["package_id"])
        urls = self._retry_value(context, lambda: self.agents.select_sources(context, workspace), "source selection")
        return [value for value in candidates if value["url"] in urls]

    def _acquire_sources(self, sources: list[dict], attempt_id: str) -> list[dict]:
        acquired = []
        for source in sources:
            try:
                acquired.append(self.broker.extract(source, attempt_id))
            except Exception:
                continue
        return acquired

    def _search_queries(self, project: dict, parent: dict | None, workspace: Path) -> list[str]:
        context = {"question": project["question"]}
        if parent:
            context["review_feedback"] = self.world.reviews(parent["package_id"])
        return self._retry_value(context, lambda: self.agents.plan_search(context, workspace), "producer search plan")

    def _retry_value(self, context: dict, operation, label: str):
        for _ in range(3):
            try:
                return operation()
            except ValueError as error:
                context["mechanical_feedback"] = str(error)
        raise ValueError(f"{label} mechanical revision limit exceeded")

    def _snapshot_source(self, project: dict, value: dict, attempt_id: str) -> dict:
        lines = self._source_lines(value["content"])
        content = "\n".join(lines).encode()
        artifact = self.world.add_artifact(content, "text/plain")
        self.world.grant_artifact(attempt_id, artifact["id"], "source_snapshot")
        locator = {"line_start": 1, "line_end": len(lines)}
        snapshot = self.world.add_source_snapshot(project["id"], value["url"], artifact, locator)
        numbered = "\n".join(f"{number}: {line}" for number, line in enumerate(lines, 1))
        return {**value, "content": numbered, "snapshot_id": snapshot["id"], "artifact_id": artifact["id"], "locator": locator}

    def _source_lines(self, content: str) -> list[str]:
        raw_lines = content.splitlines() or [content]
        return [line for raw in raw_lines for line in (textwrap.wrap(raw, 140) or [""])]

    def _producer_context(self, run, generation, parent, sources) -> dict:
        project = self.world.project(run["project_id"])
        context = {"question": project["question"], "ordinal": generation["ordinal"], "sources": sources}
        if parent:
            context["parent"] = self.world.package_nodes(parent["package_id"])
            context["review_feedback"] = self.world.reviews(parent["package_id"])
        return context

    def _review(self, run: dict, generation: dict, package: dict) -> str:
        existing = {value["reviewer"]: value for value in self.world.reviews(package["id"])}
        reviews = []
        for label in ("reviewer-a", "reviewer-b"):
            if label in existing:
                reviews.append(existing[label])
                continue
            attempt, workspace = self._attempt(run, generation, label)
            context = self._review_context(run, package)
            review = self._review_agent(run, generation, attempt, context, workspace, label)
            saved = self.world.review_package(package["id"], label, review["decision"], review["feedback"], review["category"])
            self._complete_attempt(attempt, context, review, workspace)
            reviews.append(saved)
        outcome = self._review_outcome(reviews)
        if outcome == "mechanical":
            return self._repair_package(run, generation, reviews)
        self._complete_producer(generation["id"])
        return outcome

    def _review_outcome(self, reviews: list[dict]) -> str:
        decisions = [review["decision"] for review in reviews]
        if decisions == ["approve", "approve"]:
            return "approve"
        if decisions == ["revise", "revise"]:
            return "mechanical" if all(review["category"] == "mechanical" for review in reviews) else "revise"
        return "conflict"

    def _repair_package(self, run: dict, generation: dict, reviews: list[dict]) -> str:
        count = self.repairs.get(generation["id"], 0) + 1
        self.repairs[generation["id"]] = count
        if count > 2 or generation["id"] not in self.pending:
            self._complete_producer(generation["id"])
            return "conflict"
        attempt, workspace, context, _ = self.pending[generation["id"]]
        context["review_feedback"] = reviews
        context["revision"] = count
        self._event(run, generation, attempt, "system", "mechanical_revision", "attempt", attempt["id"], {"reviews": reviews})
        package = self._revised_package(run, generation, context, workspace)
        change = package["payload"].get("strategy_change") or generation["strategy_change"]
        self.world.update_generation(generation["id"], package["id"], change)
        generation.update({"package_id": package["id"], "strategy_change": change})
        return self._review(run, generation, package)

    def _revised_package(self, run, generation, context, workspace) -> dict:
        for _ in range(3):
            try:
                package = self.agents.produce(context, workspace)
                payload = package["payload"]
                attempt = self.pending[generation["id"]][0]
                self.pending[generation["id"]] = (attempt, workspace, context, payload)
                return package
            except (InvalidPackage, KeyError, TypeError, ValueError) as error:
                context["mechanical_feedback"] = str(error)
        raise InvalidPackage("mechanical review revision limit exceeded")

    def _complete_producer(self, generation_id: str) -> None:
        state = self.pending.pop(generation_id, None)
        if state:
            attempt, workspace, context, payload = state
            self._complete_attempt(attempt, context, payload, workspace)

    def _review_agent(self, run, generation, attempt, context, workspace, label) -> dict:
        for _ in range(3):
            try:
                review = self.agents.review(context, workspace)
                self._validate_review(review)
                return review
            except ValueError as error:
                context["mechanical_feedback"] = str(error)
                self._event(run, generation, attempt, "system", "mechanical_revision", "attempt", attempt["id"], {"error": str(error), "role": label})
        raise ValueError(f"{label} mechanical revision limit exceeded")

    def _validate_review(self, review: dict) -> None:
        if isinstance(review.get("feedback"), list) and all(isinstance(item, str) for item in review["feedback"]):
            review["feedback"] = "\n".join(review["feedback"])
        if review.get("decision") not in {"approve", "revise", "uncertain"}:
            raise ValueError("review decision is invalid")
        if not isinstance(review.get("feedback"), str) or not isinstance(review.get("category"), str):
            raise ValueError("review feedback and category must be strings")

    def _review_context(self, run: dict, package: dict) -> dict:
        sources = [self._review_source(value) for value in package["payload"]["sources"]]
        return {"question": self.world.project(run["project_id"])["question"], "package": package["payload"], "sources": sources}

    def _review_source(self, value: dict) -> dict:
        snapshot = self.world.source_snapshot(value["snapshot_id"])
        content = self.world.artifacts.read(snapshot["artifact_id"]).decode()
        return {**snapshot, "content": content}

    def _report(self, run: dict, generation: dict) -> dict:
        attempt, workspace = self._attempt(run, generation, "reporter")
        context = {"question": self.world.project(run["project_id"])["question"], "graph": self._report_graph(run["project_id"])}
        for _ in range(5):
            markdown, md, page = self._draft_report(context, workspace)
            reviews = self._review_report(run, generation, markdown, page)
            if all(review["decision"] == "approve" for review in reviews):
                return self._admit_report(run, generation, attempt, workspace, context, md, page)
            context["review_feedback"] = reviews
        self._complete_attempt(attempt, context, {"markdown": md["id"], "html": page["id"]}, workspace)
        return self._finish(run["id"], "human_conflict")

    def _report_graph(self, project_id: str) -> list[dict]:
        nodes = self.world.admitted_nodes(project_id)
        for node in nodes:
            if node["kind"] == "source":
                snapshot = self.world.source_snapshot(node["payload"]["snapshot_id"])
                content = self.world.artifacts.read(snapshot["artifact_id"]).decode()
                node["payload"] = {**node["payload"], "url": snapshot["url"], "locator": snapshot["locator"], "content": content}
        return nodes

    def _draft_report(self, context: dict, workspace: Path) -> tuple[str, dict, dict]:
        markdown = self.agents.report(context, workspace)
        md = self.world.add_artifact(markdown.encode(), "text/markdown")
        page = self.world.add_artifact(self._render(markdown).encode(), "text/html")
        return markdown, md, page

    def _admit_report(self, run, generation, attempt, workspace, context, md, page) -> dict:
        self._complete_attempt(attempt, context, {"markdown": md["id"], "html": page["id"]}, workspace)
        self.world.admit_artifact_node(run["project_id"], generation["id"], md, "final_markdown")
        self.world.admit_artifact_node(run["project_id"], generation["id"], page, "final_html")
        self.world.update_run(run["id"], "completed", final_markdown_id=md["id"], final_html_id=page["id"], completed_at=now())
        self._event(run, generation, attempt, "system", "report_admitted", "artifact", page["id"], {})
        self._apply_if_selected(run, generation, attempt)
        return self.world.run(run["id"])

    def _apply_if_selected(self, run: dict, generation: dict, attempt: dict) -> None:
        if run["apply_selected"]:
            applied = self.world.apply_run(run["project_id"], run["id"])
            self._event(run, generation, attempt, "system", "project_applied", "project", run["project_id"], applied)

    def _review_report(self, run: dict, generation: dict, markdown: str, page: dict) -> list[dict]:
        reviews = []
        sources = [node for node in self._report_graph(run["project_id"]) if node["kind"] == "source"]
        context = {"question": self.world.project(run["project_id"])["question"], "report": markdown, "sources": sources, "html_artifact_id": page["id"]}
        for label in ("report-reviewer-a", "report-reviewer-b"):
            attempt, workspace = self._attempt(run, generation, label)
            self._materialize_report(workspace, markdown, page, sources)
            review = self._review_agent(run, generation, attempt, context, workspace, label)
            self._complete_attempt(attempt, context, review, workspace)
            reviews.append(review)
            self._event(run, generation, attempt, label, "report_reviewed", "artifact", page["id"], review)
        return reviews

    def _materialize_report(self, workspace: Path, markdown: str, page: dict, sources: list[dict]) -> None:
        files = {"report.md": markdown.encode(), "report.html": self.world.artifacts.read(page["id"])}
        for name, content in files.items():
            path = workspace / name
            path.write_bytes(content)
            path.chmod(0o444)
        for index, source in enumerate(sources, 1):
            path = workspace / "sources" / f"{index}.txt"
            path.parent.mkdir(exist_ok=True)
            path.write_text(source["payload"]["content"])
            path.chmod(0o444)

    def _render(self, markdown: str) -> str:
        body = markdown_renderer.markdown(markdown, extensions=["extra", "sane_lists"])
        style = "body{font:16px/1.65 system-ui;max-width:780px;margin:48px auto;padding:0 24px;color:#202124}code{white-space:pre-wrap}"
        return f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>{style}</style></head><body><main>{body}</main></body></html>'

    def _attempt(self, run: dict, generation: dict, actor: str) -> tuple[dict, Path]:
        attempt = self.world.create_attempt(run["id"], generation["id"], run["project_snapshot_id"], actor)
        workspace = self.workspaces / attempt["id"].replace(":", "-")
        attempt = self.world.bind_attempt_workspace(attempt["id"], workspace)
        self._materialize(run["project_snapshot_id"], workspace)
        token = self.world.issue_task_token(attempt["id"])
        gateway = TaskGateway(self.world, attempt["id"], self.controller)
        self.agents.bind_task(workspace, token, self._agent_tools(actor, attempt["id"], gateway), gateway.submit)
        self._event(run, generation, attempt, actor, "attempt_started", "attempt", attempt["id"], {"snapshot_id": attempt["snapshot_id"]})
        return attempt, workspace

    def _materialize(self, snapshot_id: str, workspace: Path) -> None:
        project = workspace / "project"
        project.mkdir(parents=True, exist_ok=True)
        (workspace / "home").mkdir(parents=True, exist_ok=True)
        (workspace / "overlay").mkdir(exist_ok=True)
        for entry in self.world.snapshot_manifest(snapshot_id)["files"]:
            target = project / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.world.artifacts.read(entry["artifact_id"]))
            target.chmod(0o444)
        for directory in sorted((path for path in project.rglob("*") if path.is_dir()), reverse=True):
            directory.chmod(0o555)
        project.chmod(0o555)

    def _agent_tools(self, actor: str, attempt_id: str, gateway: TaskGateway) -> list:
        if actor == "producer":
            return ["Glob", "Grep", "Read", *self.broker.agent_tools(attempt_id), *gateway.harness_tools()]
        if actor == "reporter":
            return ["Glob", "Read", "Write", "Edit"]
        return ["Glob", "Read"]

    def _complete_attempt(self, attempt: dict, context: dict, output: dict, workspace: Path) -> None:
        captured = self.agents.capture(workspace)
        wire = {"output": output, "trace": captured.get("trace", [])}
        model_context = {"input": context, "messages": captured.get("messages", [])}
        manifest = {"attempt_id": attempt["id"], "files": self._declared_files(attempt["id"], workspace)}
        self.world.complete_attempt(attempt["id"], json.dumps(wire).encode(), json.dumps(model_context).encode(), json.dumps(manifest).encode())
        self.agents.release(workspace)
        self._remove_workspace(workspace)

    def _remove_workspace(self, workspace: Path) -> None:
        for path in workspace.rglob("*"):
            if path.is_dir():
                path.chmod(0o755)
        shutil.rmtree(workspace)

    def _declared_files(self, attempt_id: str, workspace: Path) -> list[dict]:
        roots = [workspace / "overlay", *(workspace / name for name in ("report.md", "report.html"))]
        paths = [path for root in roots for path in ([root] if root.is_file() else root.rglob("*") if root.exists() else [])]
        return [self._declared_file(attempt_id, workspace, path) for path in paths if path.is_file()]

    def _declared_file(self, attempt_id: str, workspace: Path, path: Path) -> dict:
        artifact = self.world.add_artifact(path.read_bytes(), "application/octet-stream")
        self.world.grant_artifact(attempt_id, artifact["id"], "declared_output")
        return {"path": path.relative_to(workspace).as_posix(), "artifact_id": artifact["id"], "sha256": artifact["sha256"]}

    def _finish(self, run_id: str, status: str) -> dict:
        return self.world.update_run(run_id, status, completed_at=now())

    def _event(self, run, generation, attempt, actor, event_type, entity_type, entity_id, payload) -> None:
        self.world.record_event(run["id"], generation and generation["id"], attempt and attempt["id"], actor, event_type, {"type": entity_type, "id": entity_id}, payload)
