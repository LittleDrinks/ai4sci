from __future__ import annotations

import hashlib
import json
import secrets
import base64

import httpx

from .artifacts import now
from .world import World


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ExperimentRunner:
    def __init__(self, world: World, controller):
        self.world = world
        self.controller = controller

    def run(self, project_id: str, attempt_id: str, environment: dict,
            command: list[str], inputs: dict[str, bytes], seed: int) -> dict:
        bundle = self._input_bundle(inputs)
        artifact = self.world.add_artifact(bundle, "application/json")
        spec = self._spec(environment, command, artifact, inputs, seed)
        result = self.controller.run(spec)
        replay = self.controller.run(spec)
        self._verify_replay(result, replay)
        result["usage"] = {**result["usage"], "replay_verified": True, "replay_output_hash": self._output(replay)[1]}
        execution = self._record(project_id, attempt_id, environment, command, artifact, spec, result, seed)
        self.world.grant_artifact(attempt_id, artifact["id"], "execution_input")
        self.world.grant_artifact(attempt_id, execution["output_artifact_id"], "execution_output")
        return execution

    def replay(self, execution_id: str) -> dict:
        receipt = self.world.execution(execution_id)
        result = self.controller.run(receipt["spec"])
        output_hash = self._output(result)[1]
        if output_hash != receipt["output_hash"]:
            raise RuntimeError("offline replay output differs")
        return {**receipt, "output_hash": output_hash, "replayed": True}

    def _input_bundle(self, inputs: dict[str, bytes]) -> bytes:
        values = {path: {"sha256": digest(content), "content_base64": base64.b64encode(content).decode()} for path, content in sorted(inputs.items())}
        return json.dumps(values, sort_keys=True).encode()

    def _spec(self, environment, command, artifact, inputs, seed) -> dict:
        return {"image": environment["image_digest"], "command": command, "input_artifact_id": artifact["id"], "seed": seed,
                "files": {path: base64.b64encode(content).decode() for path, content in inputs.items()},
                "network": "none", "read_only": True, "limits": {"cpus": 1, "memory_mb": 512, "pids": 128}}

    def _verify_replay(self, result: dict, replay: dict) -> None:
        if self._output(result)[1] != self._output(replay)[1]:
            raise RuntimeError("offline replay output differs")

    def _record(self, project_id, attempt_id, environment, command, artifact, spec, result, seed):
        output, output_hash = self._output(result)
        output_artifact = self.world.add_artifact(output, "application/json")
        values = {"id": f"execution:{secrets.token_hex(12)}", "project_id": project_id, "attempt_id": attempt_id,
                  "environment_id": environment["id"], "image_digest": environment["image_digest"], "command": command,
                  "input_artifact_id": artifact["id"], "input_hash": artifact["sha256"], "seed": seed, "spec": spec,
                  "exit_code": result["exit_code"], "output_artifact_id": output_artifact["id"], "output_hash": output_hash,
                  "usage": result["usage"], "created_at": now()}
        return self.world.add_execution(values)

    def _output(self, result: dict) -> tuple[bytes, str]:
        value = json.dumps({key: result[key] for key in ("exit_code", "stdout", "stderr")}, sort_keys=True).encode()
        return value, digest(value)


class EnvironmentBuilder:
    def __init__(self, world: World, controller):
        self.world = world
        self.controller = controller

    def build(self, project_id: str, attempt_id: str, setup: list[str]) -> dict:
        attempt = self.world.attempt(attempt_id)
        files = self._files(attempt["snapshot_id"])
        result = self.controller.build({"files": files, "setup": setup})
        lock = self.world.add_artifact(result["lock"].encode(), "text/plain")
        self.world.grant_artifact(attempt_id, lock["id"], "environment_lock")
        return self.world.add_environment(project_id, attempt_id, result["image_digest"], lock["id"], setup)

    def _files(self, snapshot_id: str) -> dict[str, str]:
        manifest = self.world.snapshot_manifest(snapshot_id)
        return {entry["path"]: base64.b64encode(self.world.artifacts.read(entry["artifact_id"])).decode() for entry in manifest["files"]}


class HttpRunnerController:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def run(self, spec: dict) -> dict:
        return self._post("run", spec)

    def build(self, spec: dict) -> dict:
        return self._post("build", spec)

    def agent(self, spec: dict) -> dict:
        return self._post("agent", spec)

    def _post(self, path: str, spec: dict) -> dict:
        response = httpx.post(f"{self.url}/{path}", json=spec, timeout=600)
        response.raise_for_status()
        return response.json()
