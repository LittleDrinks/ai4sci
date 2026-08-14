from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_MCP = {
    "mcpServers": {"anysearch": {"type": "http", "url": "https://api.anysearch.com/mcp"}},
    "researchTools": {"server": "anysearch", "search": "search", "extract": "extract"},
}


def initialize_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    content = json.dumps(DEFAULT_MCP, ensure_ascii=False, indent=2) + "\n"
    (root / ".mcp.json").write_text(content, encoding="utf-8")


def project_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "research-project"
