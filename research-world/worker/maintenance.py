from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .api import ControlPlane
from .config import Settings


def execute_maintenance(api: ControlPlane, settings: Settings, command: dict[str, Any]) -> None:
    target = maintenance_path(settings.workspace_root, command)
    if target.exists():
        shutil.rmtree(target)
    api.complete_maintenance(command)


def maintenance_path(root: Path, command: dict[str, Any]) -> Path:
    parts = command_parts(command)
    resolved_root = root.resolve()
    target = resolved_root.joinpath(*parts).resolve()
    if target == resolved_root or not target.is_relative_to(resolved_root):
        raise ValueError("maintenance path escapes workspace root")
    return target


def command_parts(command: dict[str, Any]) -> tuple[str, ...]:
    job_id = command_part(command, "job_id")
    if command["action"] == "delete_job_workspace":
        return (job_id,)
    if command["action"] == "delete_attempt_workspace":
        return (job_id, command_part(command, "attempt_id"))
    raise ValueError(f"unknown maintenance action: {command['action']}")


def command_part(command: dict[str, Any], key: str) -> str:
    value = command[key]
    if not isinstance(value, str) or not value or Path(value).name != value or value in {".", ".."}:
        raise ValueError(f"invalid maintenance {key}")
    return value
