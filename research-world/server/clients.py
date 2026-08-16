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
