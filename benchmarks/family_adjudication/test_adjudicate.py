import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.family_adjudication.adjudicate import FIELDS, load_candidates


def row(candidate_id: str, mechanism: str) -> dict:
    candidate = {field: f"value:{field}" for field in FIELDS}
    candidate["candidate_id"] = candidate_id
    candidate["mechanism"] = mechanism
    return {"audit": {"status": "accepted"}, "planner": {"candidate": candidate}}


class CandidateIdentityTest(unittest.TestCase):
    def test_content_identity_ignores_agent_id(self):
        rows = [row("same-id", "first"), row("same-id", "second"), row("other-id", "first"), row("third-id", "third")]
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "results.jsonl"
            path.write_text("".join(json.dumps(item) + "\n" for item in rows))
            candidates = load_candidates(path)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(len({item["id"] for item in candidates}), 3)


if __name__ == "__main__":
    unittest.main()
