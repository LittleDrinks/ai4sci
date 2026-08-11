from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT.parent / ".env"


@dataclass(frozen=True)
class Settings:
    api_base: str
    api_key: str
    workspace_root: Path


def required(values: dict[str, str | None], key: str) -> str:
    value = values.get(key)
    if not value:
        raise RuntimeError(f"missing {key} in {ENV_PATH}")
    return value


def load_settings() -> Settings:
    values = dotenv_values(ENV_PATH)
    return Settings(
        api_base=required(values, "baseurl"),
        api_key=required(values, "apikey"),
        workspace_root=PROJECT_ROOT / "data" / "workspaces",
    )

