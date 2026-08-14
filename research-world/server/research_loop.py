from __future__ import annotations

import json
import textwrap
from pathlib import Path

from . import profiles
from .artifacts import now
from .research import ResearchState


EXPERIMENT_WORKFLOWS = {"computation", "simulation", "forecast"}


class RevisionRequested(RuntimeError):
    def __init__(self, review: dict):
        super().__init__("review requested revision")
        self.review = review


class ResearchLoop:
    def __init__(self, world, agents, search, controller):
        self.world = world
        self.state = ResearchState(world)
        self.agents = agents
        self.search = search
        self.controller = controller

    def plan_project(self, project_id: str, skeleton: list[dict] | None = None) -> list[dict]:
        project = self.world.project(project_id)
        existing = [node for node in self.world.project_nodes(project_id) if node["kind"] == "direction"]
        if existing:
            return existing
        self.state.add_message(project_id, "user", project["question"])
        context = {"question": project["question"], "workflow_skeleton": skeleton}
        value = self._project_call(project, "project-lead", profiles.LEAD, context)
        directions = self._directions(value)
        directions = self._apply_skeleton(directions, skeleton)
        nodes = self.state.propose_directions(project_id, directions)
        self.state.add_message(project_id, "assistant", self._direction_message(nodes))
        return nodes

    def handle_message(self, project_id: str, content: str, node_id: str | None = None) -> dict:
        project = self.world.project(project_id)
        self.state.add_message(project_id, "user", content, node_id)
        context = self._lead_context(project_id, content, node_id)
        value = self._project_call(project, "project-lead", profiles.LEAD_DIALOGUE, context)
        self.state.add_message(project_id, "assistant", value["response"], value.get("direction_id"))
        return self._apply_lead_action(project_id, value)

    def admit_and_run(self, direction_id: str) -> dict:
        project_id = self.state.node(direction_id)["project_id"]
        existing = next((cycle for cycle in self.state.cycles(project_id) if cycle["direction_id"] == direction_id and cycle["status"] in {"active", "completed"}), None)
        if existing and existing["status"] == "completed":
            return existing
        if existing:
            self.state.block_cycle(existing["id"], {"title": "Interrupted cycle", "open_questions": ["A new cycle superseded an interrupted attempt."]})
        direction = self.state.admit_direction(direction_id)
        cycle = self.state.start_cycle(direction_id)
        try:
            evidence = self._source_work(cycle, direction)
            claims = self._claim_work(cycle, direction, evidence)
            experiment = self._experiment_work(cycle, direction, claims)
            protocol = self._protocol_work(cycle, direction, claims)
            return self._report_work(cycle, direction, evidence, claims, experiment or protocol)
        except Exception as error:
            brief = {"title": direction["payload"]["title"], "learned": [], "evidence": [], "limitations": [str(error)], "open_questions": ["The direction stopped before admission."], "next_moves": ["Inspect the failed attempt log and revise the work item."]}
            self.state.block_cycle(cycle["id"], brief)
            raise

    def _source_work(self, cycle: dict, direction: dict) -> dict:
        work = self.state.create_work_item(cycle["id"], "source", {"direction": direction["payload"]})
        reused = self._reusable_sources(cycle["project_id"], direction["id"])
        if reused:
            return self._reuse_source_work(work, reused)
        sources = self._acquire_sources(work, direction)
        summaries = self._agent_step(work, 1, "source-summarizer", profiles.SOURCE_SUMMARY, {"direction": direction["payload"], "sources": sources})
        review = self._review_step(work, 2, "source-reviewer", {"direction": direction["payload"], "sources": sources, "summaries": summaries})
        output = {"sources": sources, "summaries": summaries, "review": review}
        self.state.complete_work_item(work["id"], output)
        return output

    def _reusable_sources(self, project_id: str, direction_id: str) -> dict | None:
        items = [item for item in self.state.work_items(project_id) if item["direction_id"] == direction_id and item["kind"] == "source" and item["status"] == "completed"]
        return items[-1]["output"] if items else None

    def _reuse_source_work(self, work: dict, output: dict) -> dict:
        for step in work["steps"]:
            self.state.finish_step(step["id"], {"reused_from_frozen_snapshot": True})
        self.state.complete_work_item(work["id"], output)
        return output

    def _acquire_sources(self, work: dict, direction: dict) -> list[dict]:
        step = work["steps"][0]
        attempt = self._start_attempt(work, step, "source-acquirer")
        context = {"question": self.world.project(work["project_id"])["question"], "direction": direction["payload"]}
        result = self.agents.invoke("source-acquirer", profiles.SEARCH_PLAN, context)
        sources = self._search_all(work["project_id"], attempt["id"], result.value["queries"])
        snapshots = [self._snapshot_source(work["project_id"], attempt["id"], item) for item in sources[:4]]
        self._finish_attempt(attempt, context, {"queries": result.value["queries"], "sources": snapshots}, result.log)
        self.state.finish_step(step["id"], {"sources": snapshots})
        return snapshots

    def _claim_work(self, cycle: dict, direction: dict, evidence: dict) -> dict:
        revision = None
        for number in range(3):
            try:
                return self._claim_attempt(cycle, direction, evidence, revision)
            except RevisionRequested as error:
                revision = {"number": number + 1, "review": error.review}
        raise ValueError("claim review revision limit exceeded")

    def _claim_attempt(self, cycle: dict, direction: dict, evidence: dict, revision: dict | None) -> dict:
        work = self.state.create_work_item(cycle["id"], "claim", {"direction": direction["payload"]})
        context = {"direction": direction["payload"], "evidence": evidence, "revision": revision}
        proposed = self._agent_step(work, 0, "claim-worker", profiles.CLAIM_PROPOSE, context)
        rebuttal = self._agent_step(work, 1, "claim-rebuttal", profiles.CLAIM_REBUT, {**context, "proposed": proposed})
        instructions = profiles.PROOF_REVIEW if direction["payload"]["workflow"] == "proof_boundary" else profiles.SCIENCE_REVIEW
        review = self._review_step(work, 2, "claim-reviewer", {**context, "proposed": proposed, "rebuttal": rebuttal}, instructions)
        claims = self._admit_claims(direction, evidence, proposed, rebuttal)
        output = {"claims": claims, "rebuttal": rebuttal, "review": review}
        self.state.complete_work_item(work["id"], output)
        return output

    def _protocol_work(self, cycle: dict, direction: dict, claims: dict) -> dict | None:
        if direction["payload"]["workflow"] != "wet_lab_proposal":
            return None
        work = self.state.create_work_item(cycle["id"], "protocol", {"direction": direction["payload"], "claims": claims})
        protocol = self._agent_step(work, 0, "protocol-planner", profiles.PROTOCOL_PLAN, work["input"])
        review = self._review_step(work, 1, "protocol-reviewer", {"direction": direction["payload"], "claims": claims, "protocol": protocol})
        self.state.finish_step(work["steps"][2]["id"], {"published": True, "observations": "awaiting_manual_input"})
        output = {"protocol": protocol, "review": review, "observations": None}
        node = self.state.add_research_node(direction["project_id"], "experiment", {"kind": "wet_lab_protocol", **output})
        self.state.add_edge(direction["id"], node["id"], "contains")
        self.state.complete_work_item(work["id"], output)
        return output

    def _experiment_work(self, cycle: dict, direction: dict, claims: dict) -> dict | None:
        if direction["payload"]["workflow"] not in EXPERIMENT_WORKFLOWS:
            return None
        revision = None
        for number in range(3):
            try:
                return self._experiment_attempt(cycle, direction, claims, revision)
            except RevisionRequested as error:
                revision = {"number": number + 1, "review": error.review}
        raise ValueError("experiment review revision limit exceeded")

    def _experiment_attempt(self, cycle: dict, direction: dict, claims: dict, revision: dict | None) -> dict:
        work = self.state.create_work_item(cycle["id"], "experiment", {"direction": direction["payload"], "claims": claims})
        context = {**work["input"], "revision": revision}
        plan = self._agent_step(work, 0, "experiment-planner", profiles.EXPERIMENT_PLAN, context)
        execution = self._execute_step(work, plan)
        science = self._review_step(work, 2, "science-reviewer", {"plan": plan, "execution": execution, "claims": claims})
        code = self._review_step(work, 3, "code-reviewer", {"plan": plan, "execution": execution}, profiles.CODE_REVIEW)
        output = {"plan": plan, "execution": execution, "science_review": science, "code_review": code}
        node = self._admit_experiment(direction, plan, execution)
        output["node_id"] = node["id"]
        self.state.complete_work_item(work["id"], output)
        return output

    def _report_work(self, cycle: dict, direction: dict, evidence: dict, claims: dict, experiment: dict | None) -> dict:
        work = self.state.create_work_item(cycle["id"], "report", {"direction": direction["payload"]})
        context = {"question": self.world.project(cycle["project_id"])["question"], "direction": direction["payload"], "evidence": evidence, "claims": claims, "experiment": experiment}
        brief = self._agent_step(work, 0, "synthesizer", profiles.CYCLE_BRIEF, context)
        review = self._review_step(work, 1, "report-reviewer", {**context, "brief": brief})
        brief["review"] = review
        self.state.finish_step(work["steps"][2]["id"], {"published": True})
        self.state.complete_work_item(work["id"], brief)
        cycle = self.state.complete_cycle(cycle["id"], brief)
        self._export_cycle(cycle)
        self.state.add_message(cycle["project_id"], "assistant", self._brief_message(brief), cycle["direction_id"])
        return cycle

    def _agent_step(self, work: dict, ordinal: int, role: str, instructions: str, context: dict) -> dict:
        step = work["steps"][ordinal]
        attempt = self._start_attempt(work, step, role)
        try:
            result = self.agents.invoke(role, instructions, context)
        except Exception as error:
            self._fail_attempt(attempt, step, error)
            raise
        self._finish_attempt(attempt, context, result.value, result.log)
        self.state.finish_step(step["id"], result.value)
        return result.value

    def _review_step(self, work: dict, ordinal: int, role: str, context: dict, instructions: str = profiles.SCIENCE_REVIEW) -> dict:
        output = self._agent_step(work, ordinal, role, instructions, context)
        step = work["steps"][ordinal]
        findings = [self._record_finding(step, role, item, context) for item in output.get("findings", [])]
        if any(item["severity"] == "critical" and item["status"] == "open" for item in findings):
            self.state.revise_work_item(work["id"], {"review": output})
            raise RevisionRequested(output)
        return output

    def _execute_step(self, work: dict, plan: dict) -> dict:
        step = work["steps"][1]
        attempt = self._start_attempt(work, step, "experiment-executor")
        try:
            receipt = self._run_experiment(work, attempt, plan)
        except Exception as error:
            self._fail_attempt(attempt, step, error)
            raise
        output = {**receipt, "stdout": self._execution_stdout(receipt)}
        self._finish_attempt(attempt, plan, output, b"")
        self.state.finish_step(step["id"], output)
        return output

    def _run_experiment(self, work: dict, attempt: dict, plan: dict) -> dict:
        from .runner import EnvironmentBuilder, ExperimentRunner
        setup, command, files = self._safe_plan(plan)
        environment = EnvironmentBuilder(self.world, self.controller).build(work["project_id"], attempt["id"], setup)
        inputs = {name: content.encode() for name, content in files.items()}
        return ExperimentRunner(self.world, self.controller).run(work["project_id"], attempt["id"], environment, command, inputs, int(plan.get("seed", 0)))

    def _start_attempt(self, work: dict, step: dict, role: str) -> dict:
        cycle = self.state.cycle(work["cycle_id"])
        run = self.world.run(cycle["run_id"])
        attempt = self.world.create_attempt(run["id"], work["generation_id"], run["project_snapshot_id"], role)
        self.state.bind_attempt(work["id"], attempt["id"])
        self.state.start_step(step["id"], attempt["id"])
        return attempt

    def _finish_attempt(self, attempt: dict, context: dict, output: dict, agent_log: bytes) -> None:
        receipts = self.world.tool_receipts(attempt["id"])
        log = self._attempt_log(context, output, agent_log, receipts)
        self.state.add_attempt_log(attempt["id"], log)
        wire = json.dumps({"output": output, "tool_receipts": receipts}, ensure_ascii=False).encode()
        model_context = json.dumps({"input": context}, ensure_ascii=False).encode()
        self.world.complete_attempt(attempt["id"], wire, model_context, b'{"files":[]}')

    def _fail_attempt(self, attempt: dict, step: dict, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        self.state.add_attempt_log(attempt["id"], (json.dumps({"type": "error", "error": message}) + "\n").encode())
        self.world.fail_attempt(attempt["id"], message)
        self.state.fail_step(step["id"], message)

    def _project_call(self, project: dict, role: str, instructions: str, context: dict) -> dict:
        run = self.world.create_run(project["id"], 0, False)
        snapshot = self.world.sync_project(project["id"])
        self.world.update_run(run["id"], "running", project_snapshot_id=snapshot["id"])
        generation = self.world.create_generation(project["id"], 0, run_id=run["id"])
        attempt = self.world.create_attempt(run["id"], generation["id"], snapshot["id"], role)
        result = self.agents.invoke(role, instructions, context)
        log = self.state.add_attempt_log(attempt["id"], result.log)
        self.state.add_project_call(project["id"], attempt["id"], role, log["id"])
        self.world.complete_attempt(attempt["id"], json.dumps(result.value).encode(), json.dumps(context).encode(), b'{"files":[]}')
        self.world.update_run(run["id"], "completed", completed_at=now())
        return result.value

    def _search_all(self, project_id: str, attempt_id: str, queries: list[str]) -> list[dict]:
        project = self.world.project(project_id)
        found = [item for query in queries[:2] for item in self.search.search(project, query, attempt_id)]
        unique = list({item["url"]: item for item in found}.values())
        extracted = [value for item in unique[:6] if (value := self._try_extract(item, attempt_id))]
        if len(extracted) < 2:
            raise ValueError("source acquisition produced fewer than two readable sources")
        return extracted[:4]

    def _try_extract(self, source: dict, attempt_id: str) -> dict | None:
        try:
            return self.search.extract(source, attempt_id)
        except Exception:
            return source if source.get("content") else None

    def _snapshot_source(self, project_id: str, attempt_id: str, source: dict) -> dict:
        lines = [line for raw in source["content"].splitlines() for line in (textwrap.wrap(raw, 160) or [""])] or [""]
        artifact = self.world.add_artifact("\n".join(lines).encode(), "text/markdown")
        self.world.grant_artifact(attempt_id, artifact["id"], "source_snapshot")
        locator = {"line_start": 1, "line_end": len(lines)}
        snapshot = self.world.add_source_snapshot(project_id, source["url"], artifact, locator)
        return {"source_id": snapshot["id"], "artifact_id": artifact["id"], "sha256": artifact["sha256"], "title": source["title"], "url": source["url"], "locator": locator, "content": "\n".join(lines[:80])}

    def _admit_claims(self, direction: dict, evidence: dict, proposed: dict, rebuttal: dict) -> list[dict]:
        nodes = []
        sources = {item["source_id"]: item for item in evidence["sources"]}
        for index, claim in enumerate(proposed.get("claims", [])):
            node = self.state.add_research_node(direction["project_id"], "claim", {**claim, "rebuttal": self._rebuttal(index, rebuttal)})
            self.state.add_edge(direction["id"], node["id"], "contains")
            for source_id in claim.get("source_ids", []):
                source = sources.get(source_id)
                if source:
                    source_node = self.state.add_research_node(direction["project_id"], "source", source)
                    self.state.add_edge(source_node["id"], node["id"], "supports")
            nodes.append({"node_id": node["id"], **node["payload"]})
        return nodes

    def _admit_experiment(self, direction: dict, plan: dict, execution: dict) -> dict:
        paths = self._publish_code(direction, plan.get("files", {}))
        node = self.state.add_research_node(direction["project_id"], "experiment", {"plan": plan, "code_paths": paths, "execution_id": execution["id"], "output_artifact_id": execution["output_artifact_id"], "output_hash": execution["output_hash"]})
        self.state.add_edge(direction["id"], node["id"], "contains")
        result = self.state.add_research_node(direction["project_id"], "result", {"execution_id": execution["id"], "stdout": execution["stdout"], "interpretation": plan["expected_observation"], "limitations": plan["cannot_establish"]})
        self.state.add_edge(node["id"], result["id"], "derived_from")
        return node

    def _lead_context(self, project_id: str, content: str, node_id: str | None) -> dict:
        directions = [node for node in self.world.project_nodes(project_id) if node["kind"] == "direction"]
        return {"message": content, "focused_node_id": node_id, "directions": directions, "cycles": self.state.cycles(project_id)}

    def _apply_lead_action(self, project_id: str, value: dict) -> dict:
        action = value.get("action", "none")
        if action == "new_direction" and value.get("direction"):
            node = self.state.propose_directions(project_id, [value["direction"]])[0]
            return {"action": action, "direction_id": node["id"]}
        if action == "continue_direction" and value.get("direction_id"):
            cycle = self.admit_and_run(value["direction_id"])
            return {"action": action, "direction_id": value["direction_id"], "cycle_id": cycle["id"]}
        return {"action": "none"}

    def _publish_code(self, direction: dict, files: dict[str, str]) -> list[str]:
        project = self.world.project(direction["project_id"])
        root = Path(project["root"]) / "research-code" / direction["id"].replace(":", "-")
        root.mkdir(parents=True, exist_ok=True)
        paths = [self._write_code(root, name, content) for name, content in files.items()]
        return [str(path.relative_to(project["root"])) for path in paths]

    def _write_code(self, root: Path, name: str, content: str) -> Path:
        target = root / Path(name).name
        target.write_text(content, encoding="utf-8")
        return target

    def _export_cycle(self, cycle: dict) -> None:
        from .dossier import DossierExporter
        DossierExporter(self.world).export(cycle["project_id"], cycle["id"])

    def _record_finding(self, step: dict, role: str, item: dict, context: dict) -> dict:
        evidence = [entry for entry in item.get("evidence", []) if self._valid_anchor(entry, context)]
        severity = item.get("severity", "info") if evidence else "info"
        value = {**item, "severity": severity, "evidence": evidence, "status": "open" if severity == "critical" else "noted"}
        return self.state.add_finding(step["id"], role, value)

    def _valid_anchor(self, entry: dict, context: dict) -> bool:
        if not isinstance(entry, dict):
            return False
        if not entry.get("id") or not entry.get("locator"):
            return False
        hashes = self._hashes(context)
        return not entry.get("sha256") or entry["sha256"] in hashes

    def _hashes(self, value) -> set[str]:
        if isinstance(value, dict):
            own = {value[key] for key in ("sha256", "output_hash", "input_hash") if value.get(key)}
            return own.union(*(self._hashes(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(self._hashes(item) for item in value)) if value else set()
        return set()

    def _safe_plan(self, plan: dict) -> tuple[list[str], list[str], dict[str, str]]:
        files = plan.get("files", {})
        command = self._normalize_command(plan.get("command", []))
        if len(command) != 2 or command[1] not in files or not command[1].endswith(".py"):
            raise ValueError("experiment command must run one supplied Python file")
        needs_scipy = any("scipy" in content or "numpy" in content for content in files.values())
        setup = ["python -m pip install --no-cache-dir scipy==1.16.1"] if needs_scipy else []
        return setup, command, files

    def _normalize_command(self, command) -> list[str]:
        if isinstance(command, list) and len(command) == 1:
            command = command[0].split()
        if isinstance(command, list) and len(command) == 2 and command[0] in {"python", "python3"}:
            return ["python", command[1]]
        return command

    def _execution_stdout(self, receipt: dict) -> str:
        value = json.loads(self.world.artifacts.read(receipt["output_artifact_id"]))
        return value["stdout"]

    def _receipt_log(self, receipts: list[dict]) -> bytes:
        return "".join(json.dumps({"type": "tool_call", **item}, ensure_ascii=False) + "\n" for item in receipts).encode()

    def _attempt_log(self, context: dict, output: dict, agent_log: bytes, receipts: list[dict]) -> bytes:
        start = json.dumps({"type": "attempt_input", "content": context}, ensure_ascii=False) + "\n"
        end = json.dumps({"type": "attempt_output", "content": output}, ensure_ascii=False) + "\n"
        return start.encode() + agent_log + self._receipt_log(receipts) + end.encode()

    def _directions(self, value: dict) -> list[dict]:
        directions = value.get("directions", [])
        if len(directions) != 4:
            raise ValueError("project lead must propose exactly four directions")
        return directions

    def _apply_skeleton(self, directions: list[dict], skeleton: list[dict] | None) -> list[dict]:
        if not skeleton:
            return directions
        return [{**direction, "workflow": base["workflow"], "completion_test": direction.get("completion_test") or base["completion_test"], "remaining": direction.get("remaining") or base["remaining"]} for direction, base in zip(directions, skeleton)]

    def _rebuttal(self, index: int, value: dict) -> dict:
        return next((item for item in value.get("rebuttals", []) if item.get("claim_index") == index), {})

    def _direction_message(self, nodes: list[dict]) -> str:
        return "我提出了四条可独立推进的方向：\n" + "\n".join(f"{index}. {node['payload']['title']}" for index, node in enumerate(nodes, 1))

    def _brief_message(self, brief: dict) -> str:
        learned = "；".join(brief.get("learned", []))
        remaining = "；".join(brief.get("open_questions", []))
        return f"方向已停在审核后的决策点。已获得：{learned}\n仍未完成：{remaining}"
