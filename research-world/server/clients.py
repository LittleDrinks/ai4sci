from __future__ import annotations

import asyncio
import json
import os
import re

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


class EmbeddingClient:
    def __init__(self, base_url: str, api_key: str):
        self.url = base_url.rstrip("/") + "/embeddings"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def __call__(self, text: str) -> list[float]:
        body = {"model": "qwen3.7-text-embedding", "input": text}
        response = httpx.post(self.url, headers=self.headers, json=body, timeout=60)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


class McpClient:
    def list_tools(self, server: dict) -> list[dict]:
        return self._request(server, "tools/list", {}).get("tools", [])

    def call(self, server: dict, name: str, arguments: dict):
        result = self._request(server, "tools/call", {"name": name, "arguments": arguments})
        texts = [item["text"] for item in result.get("content", []) if item.get("type") == "text"]
        return self._decode_text("\n".join(texts)) if texts else result

    def _request(self, server: dict, method: str, params: dict) -> dict:
        if server.get("type") == "stdio":
            return asyncio.run(self._stdio_request(server, method, params))
        if server.get("type") != "http":
            raise ValueError("MCP server type must be http or stdio")
        return asyncio.run(self._http_request(server, method, params))

    async def _http_request(self, server: dict, method: str, params: dict) -> dict:
        async with httpx.AsyncClient(headers=self._headers(server), timeout=60) as client:
            async with streamable_http_client(server["url"], http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await self._session_call(session, method, params)
        return result.model_dump(mode="json")

    async def _stdio_request(self, server: dict, method: str, params: dict) -> dict:
        environment = {**os.environ, **{key: self._expand(value) for key, value in server.get("env", {}).items()}}
        config = StdioServerParameters(command=server["command"], args=server.get("args", []), env=environment)
        async with stdio_client(config) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await self._session_call(session, method, params)
        return result.model_dump(mode="json")

    async def _session_call(self, session, method: str, params: dict):
        if method == "tools/list":
            return await session.list_tools()
        return await session.call_tool(params["name"], params["arguments"])

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
        config = self.broker.research_tools(attempt_id)
        result = self.broker.call(attempt_id, config["server"], config["search"], {"query": query, "max_results": 5})
        return self._parse(result)[:5]

    def extract(self, source: dict, attempt_id: str) -> dict:
        config = self.broker.research_tools(attempt_id)
        result = self.broker.call(attempt_id, config["server"], config["extract"], {"url": source["url"]})
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
