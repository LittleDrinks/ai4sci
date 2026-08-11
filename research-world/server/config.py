from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database: Path
    artifacts: Path
    projects_root: Path
    model_api_base: str | None
    model_api_key: str | None


def load_settings() -> Settings:
    data = Path(os.getenv("RW_DATA_ROOT", ROOT / "data"))
    return Settings(
        database=data / "research-world.db",
        artifacts=data / "artifacts",
        projects_root=Path(os.getenv("RW_PROJECTS_ROOT", ROOT / "projects")),
        model_api_base=os.getenv("MODEL_API_BASE"),
        model_api_key=os.getenv("MODEL_API_KEY"),
    )
