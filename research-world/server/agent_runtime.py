from __future__ import annotations

import json
from dataclasses import dataclass

from json_repair import repair_json


@dataclass(frozen=True)
class AgentResult:
    value: dict
    log: bytes


class ContainerAgents:
    def __init__(self, controller, base_url: str, api_key: str, model: str = "qwen3.7-flash"):
        self.controller = controller
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def invoke(self, role: str, instructions: str, context: dict) -> AgentResult:
        prompt = self._prompt(instructions, context)
        request = {"model": self.model, "messages": [{"role": "system", "content": self._system(role)}, {"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 5000}
        errors = []
        for _ in range(3):
            try:
                response = self.controller.agent(self._spec(request))
                return AgentResult(self._decode(response["text"]), self._log(role, request, response))
            except Exception as error:
                errors.append(str(error))
        raise RuntimeError(f"{role} failed after three attempts: {errors[-1]}")

    def _spec(self, request: dict) -> dict:
        return {"base_url": self.base_url, "api_key": self.api_key, "request": request,
                "limits": {"cpus": 1, "memory_mb": 768, "pids": 128}, "timeout": 300}

    def _system(self, role: str) -> str:
        return f"You are the isolated {role} worker in Research World. Obey the supplied evidence and role boundary. Return one JSON object and no prose."

    def _prompt(self, instructions: str, context: dict) -> str:
        return instructions + "\nINPUT:\n" + json.dumps(context, ensure_ascii=False)

    def _decode(self, text: str) -> dict:
        start = text.find("{")
        if start < 0:
            raise ValueError("agent did not return JSON")
        return repair_json(text[start:], return_objects=True)

    def _log(self, role: str, request: dict, response: dict) -> bytes:
        rows = [{"type": "agent_start", "role": role, "model": self.model},
                {"type": "messages", "messages": request["messages"]},
                {"type": "model_output", **response}]
        return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
