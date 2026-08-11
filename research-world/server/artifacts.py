from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .db import Database


def now() -> str:
    return datetime.now(UTC).isoformat()


class ArtifactStore:
    def __init__(self, root: Path, database: Database):
        self.root = root
        self.database = database
        root.mkdir(parents=True, exist_ok=True)

    def add(self, content: bytes, media_type: str) -> dict:
        digest = hashlib.sha256(content).hexdigest()
        path = self.root / digest[:2] / digest
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        self._record(digest, media_type, len(content), path)
        return self.get(f"artifact:{digest}")

    def _record(self, digest: str, media_type: str, size: int, path: Path) -> None:
        sql = "INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?,?)"
        with self.database.connect() as connection:
            connection.execute(sql, (f"artifact:{digest}", digest, media_type, size, str(path), now()))

    def get(self, artifact_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        if not row:
            raise KeyError(artifact_id)
        return dict(row)

    def read(self, artifact_id: str) -> bytes:
        return Path(self.get(artifact_id)["path"]).read_bytes()
