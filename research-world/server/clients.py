from __future__ import annotations

import json

import httpx
from json_repair import repair_json


class EndpointCapabilityError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(self, base_url: str, api_key: str, model: str = "qwen3.7-text-embedding"):
        self.url = base_url.rstrip("/") + "/embeddings"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.model = model

    def __call__(self, text: str) -> list[float]:
        response = httpx.post(self.url, headers=self.headers,
                              json={"model": self.model, "input": text}, timeout=60)
        if response.status_code in {404, 405, 501}:
            raise EndpointCapabilityError("configured endpoint does not support embeddings")
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


class ModelClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.model = model

    def json(self, system: str, payload: dict) -> dict:
        content = self.complete(system, json.dumps(payload, ensure_ascii=False))
        start = content.find("{")
        if start < 0:
            raise ValueError("model did not return JSON")
        return repair_json(content[start:], return_objects=True)

    def complete(self, system: str, prompt: str) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        body = {"model": self.model, "messages": messages}
        response = httpx.post(self.url, headers=self.headers, json=body, timeout=600)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class HarnessClient:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def json(self, role: str, instruction: str, payload: dict) -> dict:
        session = self._request("POST", "/sessions", {"role_prompt": role})
        prompt = f"{instruction}\nReturn one JSON object and no prose.\n{json.dumps(payload, ensure_ascii=False)}"
        turn = self._request("POST", f"/sessions/{session['id']}/turns", {"prompt": prompt})
        if turn["status"] != "completed":
            raise RuntimeError(f"harness turn failed: {turn['status']}")
        value = repair_json((turn["result_text"] or "").lstrip("```json\n").rstrip("`"), return_objects=True)
        return {**value, "_session_id": session["id"], "_turn_id": turn["id"], "_usage": turn["usage"]}

    def trace(self, session_id: str) -> str:
        response = httpx.get(f"{self.url}/sessions/{session_id}/trace", timeout=60)
        response.raise_for_status()
        return response.text

    def _request(self, method: str, path: str, body: dict) -> dict:
        response = httpx.request(method, self.url + path, json=body, timeout=660)
        response.raise_for_status()
        return response.json()


class RunnerClient:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def run(self, step: dict) -> dict:
        spec = {"image": step["image"], "command": step["command"], "files": step.get("files", {}),
                "seed": step.get("seed", 0), "limits": step.get("limits", {"cpus": 1, "memory_mb": 512, "pids": 128})}
        response = httpx.post(f"{self.url}/run", json=spec, timeout=360)
        response.raise_for_status()
        return response.json()
