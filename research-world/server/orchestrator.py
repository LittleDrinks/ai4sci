from __future__ import annotations

from .world import World


class WorkflowManager:
    def __init__(self, world: World):
        self.world = world

    def assist(self, project_id: str, node_id: str, message: str) -> dict:
        node = self._context_node(project_id, node_id)
        self.world.add_message(project_id, node_id, "user", message)
        reply = self._reply(node)
        saved = self.world.add_message(project_id, node_id, "assistant", reply["content"])
        return {**saved, "actions": reply["actions"], "context": node}

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

    def _reply(self, node: dict) -> dict:
        if node["kind"] == "question":
            return response("已带入问题上下文。先生成并筛选多个研究方向。", ["brainstorm"])
        if node["kind"] == "direction" and node["direction_status"] == "proposed":
            return response("该方向尚未验证。可以规划实验，逐步执行并审查证据。", ["plan-execute-review-reflect"])
        if node["kind"] == "direction":
            return response("该方向已有审查结论。可以反思证据并形成新方向，或重新规划。", ["reflect", "replan"])
        if node["kind"] == "experiment":
            return response("可以解读实验负载与审查意见，并从结果发起反思。", ["reflect"])
        return response("可以围绕该来源补充问题或形成待验证方向。", ["brainstorm"])


def response(content: str, actions: list[str]) -> dict:
    return {"content": content, "actions": actions}
