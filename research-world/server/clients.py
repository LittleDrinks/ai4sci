from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from json_repair import repair_json
from researchharness import create_agent


class EmbeddingClient:
    def __init__(self, base_url: str, api_key: str):
        self.url = base_url.rstrip("/") + "/embeddings"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def __call__(self, text: str) -> list[float]:
        body = {"model": "qwen3.7-text-embedding", "input": text}
        response = httpx.post(self.url, headers=self.headers, json=body, timeout=60)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


class HttpMcpClient:
    def list_tools(self, server: dict) -> list[dict]:
        return self._request(server, "tools/list", {}).get("tools", [])

    def call(self, server: dict, name: str, arguments: dict):
        result = self._request(server, "tools/call", {"name": name, "arguments": arguments})
        texts = [item["text"] for item in result.get("content", []) if item.get("type") == "text"]
        return self._decode_text("\n".join(texts)) if texts else result

    def _request(self, server: dict, method: str, params: dict) -> dict:
        if server.get("type") != "http":
            raise ValueError("HttpMcpClient requires type=http")
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = httpx.post(server["url"], headers=self._headers(server), json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(body["error"].get("message", str(body["error"])))
        return body.get("result", {})

    def _headers(self, server: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        for key, value in server.get("headers", {}).items():
            headers[key] = self._expand(value)
        return headers

    def _expand(self, value: str) -> str:
        match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", value)
        return os.environ.get(match.group(1), "") if match else value

    def _decode_text(self, value: str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value


class SearchBroker:
    def __init__(self, broker):
        self.broker = broker

    def search(self, project: dict, query: str, attempt_id: str) -> list[dict]:
        result = self.broker.call(attempt_id, "anysearch", "search", {"query": query, "max_results": 5})
        return self._parse(result)[:5]

    def extract(self, source: dict, attempt_id: str) -> dict:
        result = self.broker.call(attempt_id, "anysearch", "extract", {"url": source["url"]})
        content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        return {**source, "content": content[:50000]}

    def _parse(self, result) -> list[dict]:
        if not isinstance(result, str):
            return self._structured(result)
        pattern = r"### \d+\. (.*?)\n- \*\*URL\*\*: (.*?)\n- (.*?)(?=\n### \d+\.|\Z)"
        return [{"title": title.strip(), "url": url.strip(), "content": text.strip()[:12000]}
                for title, url, text in re.findall(pattern, result, re.S)]

    def _structured(self, result) -> list[dict]:
        items = result.get("results", result.get("items", [])) if isinstance(result, dict) else []
        return [{"title": item.get("title", item["url"]), "url": item["url"],
                 "content": item.get("content", item.get("snippet", ""))[:12000]} for item in items]


class HarnessAgents:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.sessions = {}

    def produce(self, context: dict, workspace: Path) -> dict:
        prompt = self._json_prompt("producer", context, PRODUCER_INSTRUCTIONS)
        return self._json_agent(prompt, workspace, "producer")

    def plan_search(self, context: dict, workspace: Path) -> list[str]:
        instructions = "Formulate two distinct web queries that seek authoritative primary scientific or institutional evidence for the supplied question. Use parent reviewer feedback when present. Do not answer the question."
        schema = ' Return exactly {"queries":["first query","second query"]}.'
        value = self._json_agent(self._json_prompt("producer", context, instructions + schema), workspace, "producer")
        queries = value.get("queries", [])
        if len(queries) != 2 or not all(isinstance(query, str) and query.strip() for query in queries):
            raise ValueError("producer search plan requires two queries")
        return queries

    def select_sources(self, context: dict, workspace: Path) -> list[str]:
        instructions = "Select the most authoritative and directly relevant primary scientific or institutional sources from the supplied candidates. Every selected URL must occur in candidates."
        schema = ' Return exactly {"urls":["https://...", "https://..."]} with three to five URLs.'
        value = self._json_agent(self._json_prompt("producer", context, instructions + schema), workspace, "producer")
        urls = value.get("urls", [])
        allowed = {item["url"] for item in context["candidates"]}
        if not 2 <= len(urls) <= 5 or not all(url in allowed for url in urls):
            raise ValueError("source selection requires two to five candidate URLs")
        return list(dict.fromkeys(urls))

    def review(self, context: dict, workspace: Path) -> dict:
        prompt = self._json_prompt("reviewer", context, REVIEWER_INSTRUCTIONS)
        return self._json_agent(prompt, workspace, "reviewer")

    def report(self, context: dict, workspace: Path) -> str:
        instructions = "Write or replace report.md with the complete scientific Markdown report, never a plan, checklist, coverage summary, path pointer, or commentary about the report. Start with a title. Directly answer and correct the question's premise in the first paragraph. Use only the admitted graph. Include source URLs and locators in References. When review_feedback is present, revise the full report in place."
        prompt = instructions + "\n" + json.dumps(context, ensure_ascii=False)
        self._agent(prompt, workspace, "reporter")
        path = workspace / "report.md"
        if not path.is_file():
            raise ValueError("reporter did not create report.md")
        return path.read_text().strip()

    def capture(self, workspace: Path) -> dict:
        trace_dir = workspace / "traces"
        traces = [{"name": path.name, "jsonl": path.read_text()} for path in sorted(trace_dir.glob("trace_*.jsonl"))]
        return {"messages": self.sessions.get(str(workspace), []), "trace": traces}

    def _json_prompt(self, role: str, context: dict, instructions: str) -> str:
        return f"{instructions}\nReturn one JSON object and no prose.\nINPUT:\n{json.dumps(context, ensure_ascii=False)}"

    def _json_agent(self, prompt: str, workspace: Path, role: str) -> dict:
        value = self._agent(prompt, workspace, role)
        return self._decode_json(value, role)

    def _decode_json(self, value: str, role: str) -> dict:
        start = value.find("{")
        if start < 0:
            raise ValueError(f"{role} did not return JSON")
        try:
            return json.JSONDecoder().raw_decode(value[start:])[0]
        except json.JSONDecodeError:
            return repair_json(value[start:], return_objects=True)

    def _agent(self, prompt: str, workspace: Path, role: str) -> str:
        trace = workspace / "traces"
        trace.mkdir(parents=True, exist_ok=True)
        agent = create_agent(model_name="qwen3.7-flash", api_key=self.api_key, api_base=self.base_url,
                             timeout_seconds=180, max_rounds=6, max_runtime_seconds=600, workspace_root=str(workspace),
                             trace_dir=str(trace), role_prompt=f"You are the independent {role} in a scientific research control plane.", require_env=False)
        key = str(workspace)
        session = agent._run_session(prompt, workspace_root=str(workspace), prior_messages=self.sessions.get(key))
        self.sessions[key] = session["messages"]
        return session["result_text"]


PRODUCER_INSTRUCTIONS = """Investigate only the supplied question and evidence. Submit a concise research package with keys strategy, strategy_change, sources, claims, artifacts, code, no_code_reason. Preserve every supplied snapshot_id and artifact_id exactly. Every source must have this exact shape: {"snapshot_id":"source-snapshot:...","artifact_id":"artifact:...","title":"..."}. Include 3 to 5 claims, only when fully supported. State attribution, scope, conditions, and quantitative values exactly as supported by a source snapshot. Do not calculate or extrapolate a value unless an execution receipt supports it. Every claim must have this exact shape: {"text":"...","citations":[{"source_snapshot_id":"source-snapshot:...","artifact_id":"artifact:...","locator":{"line_start":1,"line_end":1}}]}. Choose the smallest supporting range from the numbered source content. Every artifacts item must have artifact_id and role. Code must be an array of executed code entries. When no execution receipt is supplied, return code as [] and explain why in no_code_reason."""

REVIEWER_INSTRUCTIONS = """Independently review the package for scientific correctness, evidence sufficiency, resolvable citations, and reproducibility. Do not infer producer reasoning. Return exactly {"decision":"approve|revise|uncertain","feedback":"one string","category":"none|mechanical|method|evidence"}."""
