import unittest

from benchmarks.searchbench.runner import FIELDS, aggregate_audit, candidate_uid, planner_prompt


def review(dimension, status, route_id=None):
    return {"dimension": dimension, "status": status, "route_id": route_id, "codes": []}


class CandidateIdentityTest(unittest.TestCase):
    def test_uid_is_content_owned(self):
        candidate = {field: f"value:{field}" for field in FIELDS}
        same = dict(candidate)
        changed = {**candidate, "mechanism": "another mechanism"}
        self.assertEqual(candidate_uid(candidate), candidate_uid(same))
        self.assertNotEqual(candidate_uid(candidate), candidate_uid(changed))

    def test_any_duplicate_route_rejects(self):
        rows = [review("mechanism", "accepted", "route.rf-magpie"), review("mechanism", "accepted", "route.rf-magpie"), review("mechanism", "rejected", "route.crabnet"), review("mechanism", "rejected", "route.crabnet"), review("execution", "accepted"), review("execution", "accepted")]
        self.assertEqual(aggregate_audit(rows)["status"], "rejected")

    def test_relation_disagreement_waits_for_human(self):
        rows = [review("mechanism", "accepted", "route.rf-magpie"), review("mechanism", "accepted", "route.rf-magpie"), review("mechanism", "accepted", "route.crabnet"), review("mechanism", "rejected", "route.crabnet"), review("execution", "accepted"), review("execution", "accepted")]
        self.assertEqual(aggregate_audit(rows)["status"], "human_review")

    def test_planner_uses_supplied_history(self):
        history = {"admitted_routes": [{"id": "route.control"}]}
        prompt = planner_prompt("reflect", 0, 0, history=history)
        self.assertIn("route.control", prompt)
        self.assertNotIn("route.rf-magpie", prompt)


if __name__ == "__main__":
    unittest.main()
