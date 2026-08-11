"""OpenAI-compatible reviewer call shared with ReviewEval conventions."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any
from urllib import request


REVIEW_EVAL = Path(__file__).resolve().parents[1] / "revieweval"
sys.path.insert(0, str(REVIEW_EVAL))
from proxy import _endpoint, load_env


def _credentials(values: dict[str, str]) -> tuple[str, str]:
    base = values.get("OPENAI_BASE_URL") or values.get("baseurl") or values.get("base_url") or values.get("API_BASE")
    key = values.get("OPENAI_API_KEY") or values.get("apikey") or values.get("api_key") or values.get("API_KEY")
    if not base or not key:
        raise RuntimeError("missing OpenAI-compatible credentials")
    return base, key


def _content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        value = message.get("content", "")
    else:
        value = payload.get("content", "")
    if isinstance(value, list):
        return "".join(item.get("text", "") for item in value if isinstance(item, dict))
    return str(value)


def _usage(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage", {})
    return {key: int(usage.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def _request_payload(prompt: str, model: str, output_budget: int, base: str, key: str) -> dict[str, Any]:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": output_budget}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(_endpoint(base), data=data, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def call_model(prompt: str, model: str, output_budget: int, env_file: Path | None) -> dict[str, Any]:
    base, key = _credentials(load_env(env_file))
    payload = _request_payload(prompt, model, output_budget, base, key)
    return {"text": _content(payload), "usage": _usage(payload), "response_status": payload.get("status", "ok")}
