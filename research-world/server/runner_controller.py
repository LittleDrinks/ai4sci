from __future__ import annotations

import subprocess
import time
import base64
import hashlib
import tempfile
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
    return {"image_digest": digest, "lock": "\n".join(spec["setup"])}


def write_files(root: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(content))


def run_container(spec: dict) -> dict:
    started = time.monotonic()
    command = docker_command(spec)
    process = subprocess.run(command, capture_output=True, text=True, timeout=300)
    return {"exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr,
            "usage": {"wall_ms": round((time.monotonic() - started) * 1000)}}


def docker_command(spec: dict) -> list[str]:
    limits = spec["limits"]
    return ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cpus", str(limits["cpus"]), "--memory", f"{limits['memory_mb']}m", "--pids-limit", str(limits["pids"]),
            "--env", f"RW_RANDOM_SEED={spec.get('seed', 0)}", spec["image"], *spec["command"]]
