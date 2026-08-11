"""Optional OpenAI-compatible proxy call with a deterministic fallback."""

from __future__ import annotations

import json
from pathlib import Path
import os
from typing import Any
from urllib import error, request

from eval import QUESTIONS, answer_precheck, proxy_prompt


def load_env(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    if path is None or not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip(), value.strip().strip('"\''))
    return values


def _credentials(values: dict[str, str]) -> tuple[str | None, str | None]:
    base = values.get("OPENAI_BASE_URL") or values.get("baseurl")
    key = values.get("OPENAI_API_KEY") or values.get("apikey")
    return base, key


def _endpoint(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions" if base.endswith("/v1") else base + "/v1/chat/completions"


def _call(base: str, key: str, model: str, prompt: str) -> str:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(_endpoint(base), data=data, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def _model_answers(text: str) -> dict[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _score_answers(answers: dict[str, str], rep: dict[str, Any]) -> list[dict[str, Any]]:
    scored = []
    for question in QUESTIONS:
        answer = str(answers.get(question["id"], ""))
        terms = question.get("proxy_terms", question["terms"])
        missing = [term for term in terms if not _term_matches(term, answer)]
        scored.append({"question_id": question["id"], "passed": bool(answer) and not missing, "answer": answer, "missing_terms": missing})
    return scored


def _term_matches(term: str | list[str], answer: str) -> bool:
    choices = term if isinstance(term, list) else [term]
    return any(choice in answer for choice in choices)


def run_proxy(rep: dict[str, Any], model: str, env_path: Path | None, mode: str) -> dict[str, Any]:
    values = load_env(env_path)
    base, key = _credentials(values)
    attempted = mode == "api" or (mode == "auto" and bool(base and key))
    if attempted and base and key:
        try:
            raw = _call(base, key, model, proxy_prompt(rep))
            answers = _model_answers(raw)
            return {"mode": "api", "model": model, "attempted": True, "succeeded": bool(answers), "answers": _score_answers(answers, rep)}
        except (OSError, ValueError, KeyError, error.URLError) as exc:
            return {"mode": "heuristic_fallback", "model": model, "attempted": True, "succeeded": False, "error_type": type(exc).__name__, "answers": _heuristic(rep)}
    return {"mode": "heuristic", "model": model, "attempted": False, "succeeded": False, "answers": _heuristic(rep)}


def _heuristic(rep: dict[str, Any]) -> list[dict[str, Any]]:
    return [answer_precheck(rep, question) for question in QUESTIONS]
