import json

from server.orchestrator import Orchestrator

from conftest import project as project_fixture


class FakeBroker:
    def __init__(self):
        self.calls = []

    def search(self, project, query, attempt_id):
        self.calls.append((project["id"], query, attempt_id))
        return [{"title": "Mechanics", "url": "https://example.test/mechanics", "content": "Ideal two-body motion conserves orbital energy.\nReal dissipation requires a physical coupling."}]

    def extract(self, source, attempt_id):
        return source


class FakeAgents:
    def __init__(self, decisions=None, fail_first=False):
        self.decisions = iter(decisions or ["approve"] * 6)
        self.fail_first = fail_first
        self.productions = 0

    def produce(self, context, workspace):
        self.productions += 1
        if self.fail_first and self.productions == 1:
            return {"strategy": "missing graph"}
        source = context["sources"][0]
        return {
            "strategy": "Separate conservative dynamics from dissipative effects.",
            "strategy_change": "Challenge the parent premise directly." if context["ordinal"] else None,
            "sources": [{"snapshot_id": source["snapshot_id"], "artifact_id": source["artifact_id"], "title": source["title"]}],
            "claims": [{"text": "Stable ideal orbits conserve energy.", "citations": [{
                "source_snapshot_id": source["snapshot_id"], "artifact_id": source["artifact_id"],
                "locator": {"line_start": 1, "line_end": 1},
            }]}],
            "artifacts": [{"artifact_id": source["artifact_id"], "role": "source_text"}],
            "code": [], "no_code_reason": "No numerical experiment is needed for the mechanism claim.",
        }

    def select_sources(self, context, workspace):
        return [item["url"] for item in context["candidates"]]

    def review(self, context, workspace):
        return {"decision": next(self.decisions), "feedback": "Evidence and locator are sufficient.", "category": "none"}

    def report(self, context, workspace):
        report = "# Planetary orbit stability\n\nIdeal orbital motion conserves energy. [1]"
        (workspace / "report.md").write_text(report)
        return report

    def capture(self, workspace):
        return {"messages": [{"role": "user", "content": "captured"}], "trace": [{"type": "model_call"}]}


def test_two_generation_run_keeps_lineage_and_independent_reviews(world, project, tmp_path):
    run = world.create_run(project["id"], 49, True)
    engine = Orchestrator(world, FakeAgents(), FakeBroker(), tmp_path / "workspaces")
    result = engine.execute(run["id"])
    generations = world.generations(run["id"])
    assert result["status"] == "completed" and len(generations) == 2
    assert generations[1]["parent_id"] == generations[0]["id"]
    assert generations[1]["strategy_change"]
    assert all(len(world.reviews(item["package_id"])) == 2 for item in generations)
    assert world.run(run["id"])["final_markdown_id"]
    report_ids = {node["payload"].get("artifact_id") for node in world.admitted_nodes(project["id"])}
    assert result["final_markdown_id"] in report_ids
    assert result["final_html_id"] in report_ids
    assert_attempt_capture(world, run["id"])
    assert any(event["type"] == "project_applied" for event in world.events(run["id"]))


def assert_attempt_capture(world, run_id):
    producer = world.attempts(run_id, actor="producer")[0]
    context = json.loads(world.artifacts.read(producer["context_artifact_id"]))
    wire = json.loads(world.artifacts.read(producer["wire_artifact_id"]))
    assert context["messages"][0]["content"] == "captured"
    assert wire["trace"][0]["type"] == "model_call"


def test_mechanical_failure_revises_in_same_attempt(world, project, tmp_path):
    run = world.create_run(project["id"], 49, False)
    agents = FakeAgents(fail_first=True)
    engine = Orchestrator(world, agents, FakeBroker(), tmp_path / "workspaces")
    engine.execute(run["id"])
    attempts = world.attempts(run["id"], actor="producer")
    assert agents.productions == 3
    assert len(attempts) == 2
    assert any(event["type"] == "mechanical_revision" for event in world.events(run["id"]))


def test_reviewer_disagreement_enters_human_conflict(world, project, tmp_path):
    run = world.create_run(project["id"], 49, False)
    agents = FakeAgents(decisions=["approve", "revise"])
    result = Orchestrator(world, agents, FakeBroker(), tmp_path / "workspaces").execute(run["id"])
    assert result["status"] == "human_conflict"
    assert len(world.generations(run["id"])) == 1


def test_human_approval_admits_conflict_and_continues_run(world, project, tmp_path):
    run = world.create_run(project["id"], 49, False)
    agents = FakeAgents(decisions=["approve", "revise", "approve", "approve", "approve", "approve"])
    engine = Orchestrator(world, agents, FakeBroker(), tmp_path / "workspaces")
    assert engine.execute(run["id"])["status"] == "human_conflict"
    result = engine.approve_conflict(run["id"], "Approve the complete candidate package.")
    assert result["status"] == "completed"
    assert world.package(world.generations(run["id"])[0]["package_id"])["status"] == "admitted"


def test_review_feedback_list_is_normalized():
    review = {"decision": "revise", "feedback": ["first", "second"], "category": "method"}
    Orchestrator(None, None, None, None)._validate_review(review)
    assert review["feedback"] == "first\nsecond"
