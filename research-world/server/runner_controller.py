from __future__ import annotations

import subprocess
import time
import base64
import hashlib
import secrets
import tempfile
import json
from pathlib import Path

from fastapi import FastAPI


app = FastAPI(title="Research World Runner Controller")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/doctor")
def doctor() -> dict:
    checks = "! wget -T 2 -q -O- https://example.com && ! touch /blocked && touch /tmp/ok"
    spec = {"image": "busybox:1.36", "command": ["sh", "-c", checks],
            "network": "none", "read_only": True, "limits": {"cpus": 1, "memory_mb": 64, "pids": 32}}
    result = run_container(spec)
    return {"ok": result["exit_code"] == 0, "network": "none", "read_only": True, "result": result}


@app.post("/run")
def run(spec: dict) -> dict:
    return run_container(spec)


@app.post("/build")
def build(spec: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="rw-build-") as value:
        root = Path(value)
        write_files(root, spec["files"])
        dockerfile = "FROM python:3.12-slim\nWORKDIR /workspace\nCOPY . .\n" + "\n".join(f"RUN {command}" for command in spec["setup"])
        (root / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        tag = "rw-env-" + hashlib.sha256(dockerfile.encode()).hexdigest()[:16]
        subprocess.run(["docker", "build", "--network", "default", "-t", tag, str(root)], check=True, timeout=900)
        digest = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], capture_output=True, text=True, check=True).stdout.strip()
        lock = lock_image(tag)
    return {"image_digest": digest, "lock": lock}


@app.post("/agent")
def agent(spec: dict) -> dict:
    with tempfile.NamedTemporaryFile(mode="w", prefix="rw-agent-env-", delete=True) as environment:
        environment.write(f"MODEL_API_BASE={spec['base_url']}\nMODEL_API_KEY={spec['api_key']}\n")
        environment.flush()
        command = agent_command(spec, environment.name)
        process = subprocess.run(command, input=json.dumps(spec["request"]), capture_output=True, text=True, timeout=spec.get("timeout", 300))
    if process.returncode:
        raise RuntimeError(process.stderr[-4000:])
    return json.loads(process.stdout)


def agent_command(spec: dict, env_file: str) -> list[str]:
    limits = spec.get("limits", {"cpus": 1, "memory_mb": 768, "pids": 128})
    return ["docker", "run", "--rm", "-i", "--network", "bridge", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", str(limits["cpus"]), "--memory", f"{limits['memory_mb']}m", "--pids-limit", str(limits["pids"]),
            "--env-file", env_file,
            "python:3.12-slim", "python", "-c", AGENT_PROGRAM]


AGENT_PROGRAM = r'''import json, os, sys, urllib.request
request = json.load(sys.stdin)
url = os.environ["MODEL_API_BASE"].rstrip("/") + "/chat/completions"
body = json.dumps(request).encode()
http = urllib.request.Request(url, data=body, headers={"Authorization": "Bearer " + os.environ["MODEL_API_KEY"], "Content-Type": "application/json"})
with urllib.request.urlopen(http, timeout=240) as response:
    raw = json.load(response)
choice = raw["choices"][0]["message"]
print(json.dumps({"text": choice.get("content") or "", "tool_calls": choice.get("tool_calls", []), "usage": raw.get("usage", {}), "model": raw.get("model", request["model"])}))
'''


def lock_image(tag: str) -> str:
    command = ["docker", "run", "--rm", "--network", "none", tag, "python", "-m", "pip", "freeze", "--all"]
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=120).stdout


def write_files(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = safe_target(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(content))


def safe_target(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("input file escapes the execution root") from error
    return target


def run_container(spec: dict) -> dict:
    if not spec.get("files"):
        return invoke_container(spec, None)
    with tempfile.TemporaryDirectory(prefix="rw-run-") as value:
        root = Path(value)
        write_files(root, spec["files"])
        volume = create_input_volume(root)
        try:
            return invoke_container(spec, volume)
        finally:
            subprocess.run(["docker", "volume", "rm", "-f", volume], check=False, capture_output=True)


def create_input_volume(root: Path) -> str:
    volume = "rw-input-" + secrets.token_hex(8)
    subprocess.run(["docker", "volume", "create", volume], check=True, capture_output=True)
    mount = f"type=volume,src={volume},dst=/workspace"
    helper = subprocess.run(["docker", "create", "--mount", mount, "busybox:1.36", "true"], capture_output=True, text=True, check=True).stdout.strip()
    try:
        subprocess.run(["docker", "cp", f"{root}/.", f"{helper}:/workspace"], check=True)
    finally:
        subprocess.run(["docker", "rm", "-f", helper], check=False, capture_output=True)
    return volume


def invoke_container(spec: dict, volume: str | None) -> dict:
    started = time.monotonic()
    command = docker_command(spec, volume)
    process = subprocess.run(command, capture_output=True, text=True, timeout=300)
    return {"exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
            "usage": {"wall_ms": round((time.monotonic() - started) * 1000)}}


def docker_command(spec: dict, volume: str | None = None) -> list[str]:
    limits = spec["limits"]
    command = ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", str(limits["cpus"]), "--memory", f"{limits['memory_mb']}m", "--pids-limit", str(limits["pids"]),
            "--env", f"RW_RANDOM_SEED={spec.get('seed', 0)}"]
    if volume:
        command.extend(["--mount", f"type=volume,src={volume},dst=/workspace,readonly", "--workdir", "/workspace"])
    return [*command, spec["image"], *spec["command"]]
