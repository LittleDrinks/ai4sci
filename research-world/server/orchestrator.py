from __future__ import annotations

import os

from .clients import HarnessClient
from .world import World


ACTION_KIND = {"brainstorm": "brainstorm", "reflect": "brainstorm",
               "research": "plan-execute-review-reflect", "replan": "plan-execute-review-reflect"}


class OrchestratorAgent:
    def __init__(self, harness: HarnessClient):
        self.harness = harness

    def decide(self, node: dict, messages: list[dict], message: str, actions: list[str]) -> dict:
        payload = {"node": node_context(node), "conversation": message_context(messages),
                   "message": message, "allowed_actions": actions}
        value = self.harness.json("科研工作流助手", ORCHESTRATOR_PROMPT, payload)
        return validate_decision(value, actions)


class WorkflowManager:
    def __init__(self, world: World, agent=None):
        self.world = world
        self.agent = agent or OrchestratorAgent(HarnessClient(os.getenv("HARNESS_URL", "http://harness:8098")))

    def assist(self, project_id: str, node_id: str, message: str) -> dict:
        node = self._context_node(project_id, node_id)
        messages = self.world.messages(project_id, node_id)
        actions = actions_for(node)
        decision = self.agent.decide(node, messages, message, actions)
        workflow, created = self._start(project_id, node_id, message, decision)
        self.world.add_message(project_id, node_id, "user", message)
        content = decision["content"] + workflow_notice(workflow, created)
        saved = self.world.add_message(project_id, node_id, "assistant", content)
        return {**saved, "actions": actions, "workflow": workflow, "context": node}

    def reset(self, project_id: str, node_id: str) -> None:
        self._context_node(project_id, node_id)
        self.world.clear_messages(project_id, node_id)

    def materialize(self, project_id: str, node_id: str, kind: str, payload: dict) -> dict:
        parent = self._context_node(project_id, node_id)
        node = self.world.create_node(project_id, kind, payload, parent_id=parent["id"])
        self.world.clear_messages(project_id, node_id)
        return node

    def _context_node(self, project_id: str, node_id: str) -> dict:
        node = self.world.node(node_id)
        if node["project_id"] != project_id:
            raise PermissionError("node belongs to another project")
        return node

    def _start(self, project_id: str, node_id: str, message: str, decision: dict) -> tuple[dict | None, bool]:
        if decision["action"] is None:
            return None, False
        existing = self.world.active_workflow(project_id, node_id)
        if existing:
            return existing, False
        kind, payload = workflow_spec(decision, message)
        return self.world.create_workflow(project_id, node_id, kind, payload), True


def actions_for(node: dict) -> list[str]:
    if node["kind"] in {"question", "source"}:
        return ["brainstorm"]
    if node["kind"] == "experiment":
        return ["reflect"]
    if node["direction_status"] == "proposed":
        return ["research"]
    return ["reflect", "replan"]


def workflow_spec(decision: dict, instruction: str) -> tuple[str, dict]:
    action = decision["action"]
    payload = {"instruction": instruction, "mode": action}
    if ACTION_KIND[action] == "brainstorm":
        payload.update({"count": decision["count"], "select": decision["select"]})
    return ACTION_KIND[action], payload


def validate_decision(value: dict, actions: list[str]) -> dict:
    content, action = value.get("content"), value.get("action")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("orchestrator response requires non-empty content")
    if action is not None and action not in actions:
        raise ValueError("orchestrator selected an unavailable action")
    count, select = integer_field(value, "count"), integer_field(value, "select")
    if not 1 <= select <= count <= 20:
        raise ValueError("orchestrator count/select must satisfy 1 <= select <= count <= 20")
    return {"content": content.strip(), "action": action, "count": count, "select": select}


def integer_field(value: dict, field: str) -> int:
    item = value.get(field)
    if type(item) is not int:
        raise ValueError(f"orchestrator response requires integer {field}")
    return item


def node_context(node: dict) -> dict:
    return {key: node.get(key) for key in ("id", "kind", "life_state", "direction_status", "payload", "rebuttal")}


def message_context(messages: list[dict]) -> list[dict]:
    return [{"role": item["role"], "content": item["content"]} for item in messages[-12:]]


def workflow_notice(workflow: dict | None, created: bool) -> str:
    if workflow is None:
        return ""
    if created:
        return "\n\n已按你的要求创建工作流。执行过程可在“活动”中查看。"
    return "\n\n当前节点已有进行中的工作流，已关联到“活动”。"


ORCHESTRATOR_PROMPT = (
    "你是人类唯一直接对话的科研工作流助手。结合节点和对话回答当前消息。"
    "用户明确要求执行时，只能从 allowed_actions 选择 action；讨论、提问或信息不足时 action 为 null。"
    "brainstorm=生成研究方向，research=规划并执行实验，reflect=根据证据或实验反思，replan=重新规划实验。"
    "content 只写给人类看的最终答复，不展示内部推理或 agent 工作过程。"
    "严格返回 {\"content\":\"...\",\"action\":null,\"count\":8,\"select\":4}。"
    "action 必须为 null 或 allowed_actions 成员；count/select 必须满足 1 <= select <= count <= 20。"
)
