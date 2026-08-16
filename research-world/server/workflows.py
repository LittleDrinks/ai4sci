from __future__ import annotations

import math
import os
from dataclasses import dataclass

from .clients import EmbeddingClient, EndpointCapabilityError, HarnessClient, RunnerClient
from .config import load_settings
from .world import World


def cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
    return sum(x * y for x, y in zip(left, right, strict=True)) / denominator if denominator else 0.0


def mmr(candidates: list[dict], count: int, weight: float = 0.2) -> list[dict]:
    selected = []
    remaining = list(candidates)
    while remaining and len(selected) < count:
        best = max(remaining, key=lambda item: _mmr_score(item, selected, weight))
        selected.append(best)
        remaining.remove(best)
    return selected


def _mmr_score(candidate: dict, selected: list[dict], weight: float) -> float:
    similarity = max((cosine(candidate["vector"], item["vector"]) for item in selected), default=0)
    return float(candidate.get("quality", 0)) - weight * similarity


class AgentFacade:
    def __init__(self, harness: HarnessClient):
        self.harness = harness

    def brainstorm(self, context: dict, count: int) -> dict:
        value = self.harness.json("科研构思助手", BRAINSTORM_PROMPT, {**context, "count": count})
        candidates = required(value, "candidates")
        if not isinstance(candidates, list) or len(candidates) < count:
            raise ValueError(f"harness field 'candidates' must contain at least {count} items")
        return {**value, "candidates": candidates[:count]}

    def pairwise(self, left: str, right: str) -> bool:
        value = self.harness.json("科研新颖性裁决者", PAIR_PROMPT, {"left": left, "right": right})
        return bool(required(value, "duplicate"))

    def plan(self, direction: dict) -> dict:
        value = self.harness.json("科研实验规划者", PLAN_PROMPT, direction)
        required(value, "steps")
        return value

    def review(self, context: dict, reviewer: str) -> dict:
        value = self.harness.json(f"独立审查者 {reviewer}", REVIEW_PROMPT, context)
        for field in ("decision", "quality", "diversity", "rebuttal"):
            required(value, field)
        return value

    def reflect(self, context: dict) -> dict:
        value = self.harness.json("科研反思助手", REFLECT_PROMPT, context)
        required(value, "text")
        return value


@dataclass
class WorkflowEngine:
    world: World
    agents: object
    embedding: object
    runner: object

    def run(self, workflow_id: str) -> dict:
        workflow = self.world.workflow(workflow_id)
        self._event(workflow_id, "control", "workflow_started", {"kind": workflow["kind"]})
        if workflow["kind"] == "brainstorm":
            return self._brainstorm(workflow)
        return self._research(workflow)

    def confirm(self, workflow_id: str) -> dict:
        workflow = self.world.workflow(workflow_id)
        if workflow["status"] != "waiting_human":
            raise ValueError("workflow is not waiting for confirmation")
        if workflow["stage"] == "created":
            return self.run(workflow_id)
        step = next((item for item in self.world.steps(workflow_id) if item["status"] == "pending"), None)
        return self._execute_confirmed(workflow, step)

    def resolve(self, workflow_id: str, decision: str, reason: str) -> dict:
        workflow = self.world.workflow(workflow_id)
        node_id = workflow["payload"].get("conflict_node")
        if workflow["status"] != "waiting_human" or not node_id:
            raise ValueError("workflow has no review conflict")
        node = self.world.node(node_id)
        approved = decision == "approve"
        if node["kind"] == "experiment":
            outputs = [step["output"] for step in self.world.steps(workflow_id)]
            self._resolve_experiment(workflow, node, approved, outputs)
            return self._reflect(workflow, node, outputs)
        self._resolve_node(workflow, node, approved, reason)
        return self._finish_unless_paused(workflow_id)

    def _brainstorm(self, workflow: dict) -> dict:
        origin = self.world.set_working(workflow["node_id"], True)
        self.world.update_workflow(workflow["id"], "brainstorm", "running")
        count = int(workflow["payload"].get("count", 8))
        result = self.agents.brainstorm(agent_context(workflow, origin["payload"]), count)
        self._record_agent(workflow["id"], "brainstormer", result)
        candidates = result["candidates"]
        try:
            pool = self._deduplicate(workflow, origin, candidates)
        except EndpointCapabilityError as error:
            return self._pause(workflow["id"], str(error))
        selected = mmr(pool, int(workflow["payload"].get("select", 4)))
        return self._review_brainstorm(workflow, origin, selected)

    def _deduplicate(self, workflow: dict, origin: dict, candidates: list[dict]) -> list[dict]:
        existing = self._existing_directions(workflow["project_id"])
        pool = []
        for candidate in candidates:
            candidate["vector"] = self.embedding(candidate["text"])
            match, score = self._nearest(candidate, [*existing, *pool])
            if match and self._is_duplicate(candidate, match, score):
                self._blocked_direction(workflow, origin, candidate, match, score)
            else:
                pool.append(candidate)
        return pool

    def _existing_directions(self, project_id: str) -> list[dict]:
        values = []
        for node in self.world.nodes(project_id):
            if node["kind"] != "direction" or node["life_state"] == "ghost":
                continue
            vector = self.world.embedding_for(node["id"]) or self.embedding(node["payload"].get("text", ""))
            values.append({"text": node["payload"].get("text", ""), "vector": vector, "node_id": node["id"]})
        return values

    def _nearest(self, candidate: dict, others: list[dict]) -> tuple[dict | None, float]:
        if not others:
            return None, 0.0
        match = max(others, key=lambda item: cosine(candidate["vector"], item["vector"]))
        return match, cosine(candidate["vector"], match["vector"])

    def _is_duplicate(self, candidate: dict, match: dict, score: float) -> bool:
        if score > 0.8:
            return True
        return score >= 0.6 and self.agents.pairwise(candidate["text"], match["text"])

    def _blocked_direction(self, workflow, origin, candidate, match, score) -> None:
        reason = f"与“{match['text']}”重合（cos={score:.2f}），已阻断并转入 reflect/合并。"
        node = self._candidate_node(workflow, origin, candidate, "ghost")
        self.world.update_node(node["id"], rejection_reason=reason)
        self._event(workflow["id"], "deduplicator", "candidate_blocked", {"node_id": node["id"], "reason": reason})

    def _candidate_node(self, workflow, origin, candidate, life_state="pending") -> dict:
        lineage = f"lineage:{workflow['id'].split(':', 1)[1]}:{abs(hash(candidate['text']))}"
        payload = {"text": candidate["text"], "quality": float(candidate.get("quality", 0))}
        return self.world.create_node(workflow["project_id"], "direction", payload,
                                      parent_id=origin["id"], lineage_id=lineage, life_state=life_state)

    def _review_brainstorm(self, workflow, origin, selected) -> dict:
        for candidate in selected:
            node = self._candidate_node(workflow, origin, candidate)
            outcome = self._double_review(workflow, node, "direction")
            if outcome is None:
                self.world.set_working(origin["id"], False)
                return self.world.workflow(workflow["id"])
            self._resolve_node(workflow, node, outcome, "方向双审完成")
        self.world.set_working(origin["id"], False)
        return self._complete(workflow["id"])

    def _research(self, workflow: dict) -> dict:
        direction = self.world.set_working(workflow["node_id"], True)
        experiment = self.world.create_node(workflow["project_id"], "experiment",
                                            {"title": "待执行实验", "goal": direction["payload"].get("text", "")},
                                            parent_id=direction["id"], lineage_id=direction["lineage_id"], working=True)
        payload = {**workflow["payload"], "experiment_id": experiment["id"]}
        self.world.update_workflow(workflow["id"], "plan", "running", payload)
        self._event(workflow["id"], "control", "experiment_created", {"node_id": experiment["id"]})
        plan = self.agents.plan(agent_context(workflow, direction["payload"]))
        self._record_agent(workflow["id"], "planner", plan)
        for ordinal, step in enumerate(plan["steps"], 1):
            self.world.add_step(workflow["id"], ordinal, "execute", step, not bool(workflow["auto"]))
        status = "running" if workflow["auto"] else "waiting_human"
        self.world.update_workflow(workflow["id"], "execute", status, payload)
        return self._execute_all(self.world.workflow(workflow["id"])) if workflow["auto"] else self.world.workflow(workflow["id"])

    def _execute_all(self, workflow: dict) -> dict:
        for step in self.world.steps(workflow["id"]):
            self._execute_step(workflow, step)
        return self._review_experiment(workflow)

    def _execute_confirmed(self, workflow: dict, step: dict | None) -> dict:
        if step:
            self._execute_step(workflow, step)
        remaining = any(item["status"] == "pending" for item in self.world.steps(workflow["id"]))
        if remaining:
            return self.world.update_workflow(workflow["id"], "execute", "waiting_human")
        return self._review_experiment(workflow)

    def _execute_step(self, workflow: dict, step: dict) -> None:
        self.world.update_step(step["id"], "running")
        output = self.runner.run(step["payload"])
        status = "completed" if output.get("exit_code") == 0 else "failed"
        self.world.update_step(step["id"], status, output)
        self._event(workflow["id"], "runner", "tool_result", {"step_id": step["id"], **output})

    def _review_experiment(self, workflow: dict) -> dict:
        experiment = self.world.node(workflow["payload"]["experiment_id"])
        outputs = [step["output"] for step in self.world.steps(workflow["id"])]
        mechanical = all(output and output.get("exit_code") == 0 for output in outputs)
        outcome = self._double_review(workflow, experiment, "experiment", {"mechanical": mechanical, "outputs": outputs}) if mechanical else False
        if outcome is None:
            return self.world.workflow(workflow["id"])
        self._resolve_experiment(workflow, experiment, bool(outcome), outputs)
        return self._reflect(workflow, experiment, outputs)

    def _double_review(self, workflow, node, subject, extra=None) -> bool | None:
        context = {"subject": subject, "node": node["payload"], **(extra or {})}
        reviews = [self.agents.review(context, name) for name in ("A", "B")]
        for name, review in zip(("A", "B"), reviews, strict=True):
            event = {**review, "node_id": node["id"], "subject": subject}
            self._record_agent(workflow["id"], f"reviewer-{name.lower()}", event)
        self.world.update_node(node["id"], rebuttal={"reviewer_a": clean(reviews[0]), "reviewer_b": clean(reviews[1])})
        decisions = [review.get("decision") == "approve" for review in reviews]
        if decisions[0] != decisions[1]:
            payload = {**workflow["payload"], "conflict_node": node["id"]}
            self.world.update_workflow(workflow["id"], "review", "waiting_human", payload)
            return None
        return decisions[0]

    def _resolve_node(self, workflow, node, approved: bool, reason: str) -> None:
        lineage = self.world.register_review(node["lineage_id"], approved)
        if approved:
            self.world.admit_node(node["id"])
            if workflow["auto"] and node["kind"] == "direction" and not lineage["auto_paused"]:
                self.world.create_workflow(workflow["project_id"], node["id"], "plan-execute-review-reflect")
        else:
            self.world.ghost_node(node["id"], reason, node.get("rebuttal"))
        if lineage["auto_paused"]:
            payload = {**workflow["payload"], "reason": "同一谱系连续 2 次 review 驳回，已升级人工。"}
            self.world.update_workflow(workflow["id"], "review", "paused", payload)

    def _resolve_experiment(self, workflow, experiment, approved, outputs) -> None:
        direction = self.world.node(workflow["node_id"])
        payload = {**experiment["payload"], "outputs": outputs}
        if approved:
            self.world.admit_node(experiment["id"], payload)
            self.world.add_edge(experiment["id"], direction["id"], "supports")
        else:
            self.world.ghost_node(experiment["id"], "机械证据审计或双审未通过", experiment.get("rebuttal"))
            self.world.add_edge(experiment["id"], direction["id"], "refutes")
        self._resolve_direction(direction, approved)
        lineage = self.world.register_review(direction["lineage_id"], approved)
        if lineage["auto_paused"]:
            self.world.update_workflow(workflow["id"], "review", "paused", {**workflow["payload"], "reason": "同一谱系连续 2 次驳回"})

    def _resolve_direction(self, direction: dict, approved: bool) -> None:
        if direction["direction_status"] == "proposed":
            state = "supported" if approved else "refuted"
            self.world.update_node(direction["id"], direction_status=state, working=False)
        else:
            self.world.set_working(direction["id"], False)

    def _reflect(self, workflow, experiment, outputs) -> dict:
        if self.world.workflow(workflow["id"])["status"] == "paused":
            return self.world.workflow(workflow["id"])
        context = {"experiment": experiment["payload"], "outputs": outputs}
        value = self.agents.reflect(agent_context(workflow, context))
        self._record_agent(workflow["id"], "reflector", value)
        node = self.world.create_node(workflow["project_id"], "direction", {"text": value["text"]},
                                     parent_id=experiment["id"], lineage_id=experiment["lineage_id"])
        outcome = self._double_review(workflow, node, "direction")
        if outcome is None:
            return self.world.workflow(workflow["id"])
        self._resolve_node(workflow, node, outcome, "反思方向双审未通过")
        return self._finish_unless_paused(workflow["id"])

    def _finish_unless_paused(self, workflow_id: str) -> dict:
        if self.world.workflow(workflow_id)["status"] == "paused":
            return self.world.workflow(workflow_id)
        return self._complete(workflow_id)

    def _complete(self, workflow_id: str) -> dict:
        self._event(workflow_id, "control", "workflow_completed", {})
        return self.world.update_workflow(workflow_id, "complete", "completed")

    def _pause(self, workflow_id: str, reason: str) -> dict:
        self._event(workflow_id, "control", "workflow_paused", {"reason": reason})
        return self.world.update_workflow(workflow_id, "paused", "paused", {"reason": reason})

    def _record_agent(self, workflow_id: str, actor: str, value: dict) -> None:
        self._event(workflow_id, actor, "assistant", value)

    def _event(self, workflow_id: str, actor: str, event_type: str, payload: dict) -> None:
        self.world.record_workflow_event(workflow_id, actor, event_type, payload)


def clean(value: dict) -> dict:
    return {key: item for key, item in value.items() if not key.startswith("_")}


def agent_context(workflow: dict, context: dict) -> dict:
    return {**context, "instruction": workflow["payload"].get("instruction", ""),
            "mode": workflow["payload"].get("mode", "")}


def required(value: dict, field: str):
    if field not in value:
        raise ValueError(f"harness response missing required field '{field}'")
    return value[field]


def default_engine(world: World) -> WorkflowEngine:
    settings = load_settings()
    if not settings.model_api_base or not settings.model_api_key:
        raise RuntimeError("MODEL_API_BASE and MODEL_API_KEY are required")
    agents = AgentFacade(HarnessClient(os.getenv("HARNESS_URL", "http://harness:8098")))
    embedding = EmbeddingClient(settings.model_api_base, settings.model_api_key)
    runner = RunnerClient(os.getenv("RUNNER_CONTROLLER_URL", "http://runner-controller:8096"))
    return WorkflowEngine(world, agents, embedding, runner)


BRAINSTORM_PROMPT = (
    "输入节点内容与 instruction 是研究约束，count 是候选数。严格执行 instruction，生成恰好 count 个相互差异显著、"
    "可证伪的研究方向。严格返回 {\"candidates\":[{\"text\":\"...\",\"quality\":0.0}]}，quality 范围 0-1。"
)
PAIR_PROMPT = (
    "判断 left 与 right 是否在研究问题、方法和可证伪结论上实质重复。"
    "严格返回 {\"duplicate\":true}，duplicate 只能是布尔值。"
)
PLAN_PROMPT = (
    "严格执行 instruction，把输入方向拆为可独立确认的最小实验步骤。严格返回 "
    "{\"steps\":[{\"image\":\"busybox:1.36\",\"command\":[\"sh\",\"-lc\",\"...\"],"
    "\"files\":{},\"seed\":0,\"limits\":{\"cpus\":1,\"memory_mb\":512,\"pids\":128}}]}。"
)
REVIEW_PROMPT = (
    "机械审计优先，再独立评价质量与多样性。严格返回 "
    "{\"decision\":\"approve\",\"quality\":0.0,\"diversity\":0.0,\"rebuttal\":\"...\"}；"
    "decision 只能是 approve 或 reject，分数范围 0-1。"
)
REFLECT_PROMPT = (
    "严格执行 instruction，基于实验输出与失败边界生成一个可证伪的新方向。严格返回 {\"text\":\"...\"}。"
)
