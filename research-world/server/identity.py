from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def uid(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(canonical(value).encode()).hexdigest()[:20]
    return f"{prefix}:{digest}"


def content_sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
