import json

from server.runner import ExperimentRunner
from server.runner_controller import docker_command
from server.tools import ToolBroker


class FakeMcp:
    def list_tools(self, server):
        return [{"name": "search", "description": "Search sources", "inputSchema": {"type": "object"}}]

    def call(self, server, name, arguments):
        return {"items": [{"url": "https://example.test", "content": "evidence"}], "api_key": "must-redact"}


class FakeController:
    def __init__(self):
        self.specs = []

    def run(self, spec):
        self.specs.append(spec)
        return {"exit_code": 0, "stdout": "42\n", "stderr": "", "usage": {"wall_ms": 12}}


def test_tool_broker_records_redacted_receipt(world, project, tmp_path):
    config = {"mcpServers": {"search": {"type": "http", "url": "https://mcp.example.test", "headers": {"Authorization": "Bearer secret"}}}}
    (world.path(project["root"]) / ".mcp.json").write_text(json.dumps(config), encoding="utf-8")
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0, run_id=run["id"])
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "producer")
    broker = ToolBroker(world, FakeMcp())
    result = broker.call(attempt["id"], "search", "search", {"query": "orbits", "api_key": "hidden"})
    receipt = world.tool_receipts(attempt["id"])[0]
    assert result["items"] and "must-redact" not in json.dumps(receipt)
    assert receipt["arguments"]["api_key"] == "[REDACTED]"


def test_harness_tool_call_uses_the_same_broker(world, project):
    config = {"mcpServers": {"search": {"type": "http", "url": "https://mcp.example.test"}}}
    (world.path(project["root"]) / ".mcp.json").write_text(json.dumps(config))
    snapshot = world.sync_project(project["id"])
    run = world.create_run(project["id"], 49, False)
    generation = world.create_generation(project["id"], 0, run_id=run["id"])
    attempt = world.create_attempt(run["id"], generation["id"], snapshot["id"], "producer")
    tools = ToolBroker(world, FakeMcp()).harness_tools(attempt["id"])
    tools[1]("search", "search", {"query": "orbits"})
    assert world.tool_receipts(attempt["id"])[0]["tool"] == "search"


def test_experiment_is_offline_limited_and_replayable(world, project):
    controller = FakeController()
    runner = ExperimentRunner(world, controller)
    environment = {"id": "environment:test", "image_digest": "sha256:image"}
    receipt = runner.run(project["id"], "attempt:test", environment, ["python", "analysis.py"], {"analysis.py": b"print(42)"}, seed=7)
    assert len(controller.specs) == 2
    assert controller.specs[0]["files"]["analysis.py"]
    assert receipt["usage"]["replay_verified"] is True
    assert controller.specs[0]["network"] == "none"
    assert controller.specs[0]["read_only"] is True
    assert controller.specs[0]["limits"] == {"cpus": 1, "memory_mb": 512, "pids": 128}
    assert runner.replay(receipt["id"])["output_hash"] == receipt["output_hash"]


def test_runner_mounts_only_the_execution_input_volume():
    spec = {"image": "busybox:1.36", "command": ["cat", "input.txt"], "seed": 0,
            "limits": {"cpus": 1, "memory_mb": 64, "pids": 32}}
    command = docker_command(spec, "rw-input-test")
    assert "type=volume,src=rw-input-test,dst=/workspace,readonly" in command
    assert "/app/data" not in " ".join(command)
