from __future__ import annotations

import json
from typing import Any

from researchharness import tool as harness_tool

from .world import World


SENSITIVE = ("key", "token", "secret", "password", "authorization")


def redact(value: Any, key: str = "") -> Any:
    if any(part in key.lower() for part in SENSITIVE):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {name: redact(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class ToolBroker:
    def __init__(self, world: World, client):
        self.world = world
        self.client = client

    def list(self, attempt_id: str) -> dict[str, list[dict]]:
        return {name: self.client.list_tools(config) for name, config in self._servers(attempt_id).items()}

    def call(self, attempt_id: str, server: str, tool: str, arguments: dict) -> Any:
        config = self._servers(attempt_id).get(server)
        if not config:
            raise PermissionError(f"server {server} is not in the project snapshot")
        allowed = {value["name"] for value in self.client.list_tools(config)}
        if tool not in allowed:
            raise PermissionError(f"tool {tool} is not exposed by {server}")
        return self._invoke(attempt_id, server, tool, arguments, config)

    def harness_tools(self, attempt_id: str) -> list:
        @harness_tool(name="list_project_tools", description="List MCP tools allowed by the current project snapshot.")
        def list_project_tools() -> dict:
            return self.list(attempt_id)

        @harness_tool(name="call_project_tool", description="Call one allowed project MCP tool. Arguments must match its schema.")
        def call_project_tool(server: str, tool_name: str, arguments: dict) -> Any:
            return self.call(attempt_id, server, tool_name, arguments)

        return [list_project_tools, call_project_tool]

    def _invoke(self, attempt_id, server, tool, arguments, config):
        try:
            result = redact(self.client.call(config, tool, arguments))
            self.world.add_tool_receipt(attempt_id, server, tool, redact(arguments), result)
            return result
        except Exception as error:
            self.world.add_tool_receipt(attempt_id, server, tool, redact(arguments), {}, str(error))
            raise

    def _servers(self, attempt_id: str) -> dict:
        return self._config(attempt_id)["mcpServers"]

    def research_tools(self, attempt_id: str) -> dict:
        return self._config(attempt_id)["researchTools"]

    def _config(self, attempt_id: str) -> dict:
        attempt = self.world.attempt(attempt_id)
        content = self.world.snapshot_file(attempt["snapshot_id"], ".mcp.json")
        return json.loads(content)
