"""Load the research graph already embedded in the readability prototype."""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Any


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "prototype" / "research-world-readability.html"


def _array_literal(source: str, name: str) -> str:
    marker = f"const {name} = ["
    start = source.index(marker) + len(marker) - 1
    end = _matching_bracket(source, start)
    return source[start : end + 1]


def _scan_quote(char: str, quote: str, escaped: bool) -> tuple[str | None, bool]:
    if escaped:
        return quote, False
    if char == "\\":
        return quote, True
    return (None, False) if char == quote else (quote, False)


def _matching_bracket(source: str, start: int) -> int:
    depth = 0
    quote = None
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            quote, escaped = _scan_quote(char, quote, escaped)
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"unterminated JavaScript array: {start}")


def _parse_js_array(literal: str) -> list[dict[str, Any]]:
    quoted_keys = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r"\1'\2':", literal)
    parsed = ast.literal_eval(quoted_keys)
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise TypeError("prototype array is not a list of objects")
    return parsed


def load_dataset(source_path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    source = source_path.read_text(encoding="utf-8")
    return {
        "source_path": str(source_path),
        "artifacts": _parse_js_array(_array_literal(source, "artifacts")),
        "events": _parse_js_array(_array_literal(source, "agentEvents")),
    }
