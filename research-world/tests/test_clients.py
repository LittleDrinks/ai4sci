from server.clients import HarnessAgents


def test_search_plan_uses_exact_output_contract(tmp_path, monkeypatch):
    agents = HarnessAgents("https://model.test", "key")
    captured = {}

    def respond(prompt, workspace, role):
        captured["prompt"] = prompt
        return {"queries": ["first", "second"]}

    monkeypatch.setattr(agents, "_json_agent", respond)
    assert agents.plan_search({"question": "Q"}, tmp_path) == ["first", "second"]
    assert '{"queries":["first query","second query"]}' in captured["prompt"]


def test_model_json_repairs_unescaped_claim_quotes():
    agents = HarnessAgents("https://model.test", "key")
    value = '{"claim":"the source says "stable" here","code":[]}'
    assert agents._decode_json(value, "producer")["claim"] == 'the source says "stable" here'


def test_report_reads_declared_artifact_not_session_summary(tmp_path, monkeypatch):
    agents = HarnessAgents("https://model.test", "key")

    def respond(prompt, workspace, role):
        (workspace / "report.md").write_text("# Actual report")
        return "I wrote the report."

    monkeypatch.setattr(agents, "_agent", respond)
    assert agents.report({"graph": []}, tmp_path) == "# Actual report"
