from __future__ import annotations

import json
import secrets

from .artifacts import now
from .world import World, decode, stable_id


WORKFLOWS = {
    "source": ("acquire", "summarize", "review"),
    "claim": ("propose", "rebut", "review"),
    "experiment": ("plan", "execute", "science_review", "code_review"),
    "protocol": ("plan", "science_review", "publish"),
    "report": ("synthesize", "review", "publish"),
}
BLOCKING = {"critical", "major"}


class ResearchState:
    def __init__(self, world: World):
        self.world = world

    def add_message(self, project_id: str, role: str, content: str, node_id: str | None = None) -> dict:
        message_id = f"message:{secrets.token_hex(12)}"
        values = (message_id, project_id, role, content, node_id, now())
        self._execute("INSERT INTO project_messages VALUES(?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM project_messages WHERE id=?", (message_id,))

    def recover_interrupted(self) -> None:
        timestamp = now()
        self._execute("UPDATE attempts SET status='interrupted',completed_at=? WHERE status IN ('created','running')", (timestamp,))
        self._execute("UPDATE workflow_steps SET status='interrupted',output=?,completed_at=? WHERE status='running'", (self._json({"error": "control plane restarted"}), timestamp))
        self._execute("UPDATE work_items SET status='interrupted',completed_at=? WHERE status='active'", (timestamp,))
        for cycle in self._active_cycles():
            self.block_cycle(cycle["id"], self._interrupted_brief())

    def messages(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM project_messages WHERE project_id=? ORDER BY created_at", (project_id,))

    def propose_directions(self, project_id: str, directions: list[dict]) -> list[dict]:
        question_id = self._question_id(project_id)
        return [self._add_direction(project_id, question_id, value, index) for index, value in enumerate(directions)]

    def admit_direction(self, direction_id: str) -> dict:
        self._execute("UPDATE nodes SET status='frontier',admitted_at=? WHERE id=? AND kind='direction'", (now(), direction_id))
        return self.node(direction_id)

    def start_cycle(self, direction_id: str) -> dict:
        direction = self.node(direction_id)
        self._require_status(direction, {"frontier", "blocked"})
        run = self.world.create_run(direction["project_id"], 0, False)
        snapshot = self.world.sync_project(direction["project_id"])
        self.world.update_run(run["id"], "running", project_snapshot_id=snapshot["id"])
        cycle_id = f"cycle:{secrets.token_hex(12)}"
        values = (cycle_id, direction["project_id"], direction_id, run["id"], "active", "{}", now(), None)
        self._execute("INSERT INTO research_cycles VALUES(?,?,?,?,?,?,?,?)", values)
        self._execute("UPDATE nodes SET status='active' WHERE id=?", (direction_id,))
        return self.cycle(cycle_id)

    def create_work_item(self, cycle_id: str, kind: str, input_value: dict) -> dict:
        if kind not in WORKFLOWS:
            raise ValueError(f"unknown workflow: {kind}")
        cycle = self.cycle(cycle_id)
        self._require_status(cycle, {"active"})
        ordinal = len(self.work_items(cycle["project_id"]))
        generation = self.world.create_generation(cycle["project_id"], ordinal, run_id=cycle["run_id"])
        work_id = f"work:{secrets.token_hex(12)}"
        values = (work_id, cycle_id, cycle["project_id"], cycle["direction_id"], generation["id"], kind, "active", self._json(input_value), "{}", now(), None)
        self._execute("INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?,?,?)", values)
        self._insert_steps(work_id, WORKFLOWS[kind])
        return self.work_item(work_id)

    def start_step(self, step_id: str, attempt_id: str | None = None) -> dict:
        values = (attempt_id, now(), step_id)
        self._execute("UPDATE workflow_steps SET status='running',attempt_id=?,started_at=? WHERE id=?", values)
        return self.step(step_id)

    def finish_step(self, step_id: str, output: dict, status: str = "completed") -> dict:
        values = (status, self._json(output), now(), step_id)
        self._execute("UPDATE workflow_steps SET status=?,output=?,completed_at=? WHERE id=?", values)
        return self.step(step_id)

    def fail_step(self, step_id: str, error: str) -> dict:
        return self.finish_step(step_id, {"error": error}, "failed")

    def add_finding(self, step_id: str, reviewer: str, finding: dict) -> dict:
        step = self.step(step_id)
        finding_id = f"finding:{secrets.token_hex(12)}"
        values = (finding_id, step["work_item_id"], step_id, reviewer, finding["check_id"], finding["severity"], self._json(finding.get("evidence", [])), finding.get("recommendation", ""), finding.get("status", "open"), now())
        self._execute("INSERT INTO findings VALUES(?,?,?,?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM findings WHERE id=?", (finding_id,))

    def complete_work_item(self, work_id: str, output: dict) -> dict:
        self._validate_gate(work_id)
        values = (self._json(output), now(), work_id)
        self._execute("UPDATE work_items SET status='completed',output=?,completed_at=? WHERE id=?", values)
        return self.work_item(work_id)

    def revise_work_item(self, work_id: str, output: dict) -> dict:
        values = (self._json(output), work_id)
        self._execute("UPDATE work_items SET status='revision_requested',output=? WHERE id=?", values)
        return self.work_item(work_id)

    def complete_cycle(self, cycle_id: str, brief: dict) -> dict:
        cycle = self.cycle(cycle_id)
        values = (self._json(brief), now(), cycle_id)
        self._execute("UPDATE research_cycles SET status='completed',brief=?,completed_at=? WHERE id=?", values)
        self._execute("UPDATE nodes SET status='completed' WHERE id=?", (cycle["direction_id"],))
        self.world.update_run(cycle["run_id"], "completed", completed_at=now())
        self._add_brief_node(cycle, brief)
        return self.cycle(cycle_id)

    def block_cycle(self, cycle_id: str, brief: dict) -> dict:
        cycle = self.cycle(cycle_id)
        values = (self._json(brief), now(), cycle_id)
        self._execute("UPDATE research_cycles SET status='blocked',brief=?,completed_at=? WHERE id=?", values)
        self._execute("UPDATE nodes SET status='blocked' WHERE id=?", (cycle["direction_id"],))
        self.world.update_run(cycle["run_id"], "terminated", completed_at=now())
        return self.cycle(cycle_id)

    def add_research_node(self, project_id: str, kind: str, payload: dict, status: str = "admitted") -> dict:
        node_id = f"node:{secrets.token_hex(16)}"
        values = (node_id, project_id, None, None, kind, self._json(payload), status, now(), now() if status == "admitted" else None)
        self._execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)", values)
        self._index_node(node_id, project_id, payload)
        return self.node(node_id)

    def add_edge(self, source: str, target: str, kind: str) -> None:
        package_id = stable_id("edge-group", {"source": source, "target": target, "kind": kind})
        self._execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)", (source, target, kind, package_id))

    def bind_attempt(self, work_id: str, attempt_id: str) -> None:
        self._execute("INSERT INTO work_item_attempts VALUES(?,?)", (work_id, attempt_id))

    def add_attempt_log(self, attempt_id: str, content: bytes) -> dict:
        artifact = self.world.add_artifact(content, "text/plain")
        self.world.grant_artifact(attempt_id, artifact["id"], "attempt_log")
        self._write_log_file(attempt_id, content)
        self._execute("INSERT INTO attempt_logs VALUES(?,?)", (attempt_id, artifact["id"]))
        return artifact

    def add_project_call(self, project_id: str, attempt_id: str, role: str, artifact_id: str) -> dict:
        call_id = f"call:{secrets.token_hex(12)}"
        values = (call_id, project_id, attempt_id, role, artifact_id, "completed", now())
        self._execute("INSERT INTO project_calls VALUES(?,?,?,?,?,?,?)", values)
        return self._one("SELECT * FROM project_calls WHERE id=?", (call_id,))

    def project_view(self, project_id: str) -> dict:
        return {"messages": self.messages(project_id), "cycles": self.cycles(project_id),
                "work_items": self.work_items(project_id), "findings": self.project_findings(project_id),
                "attempts": self.project_attempts(project_id), "agent_calls": self.project_calls(project_id)}

    def node(self, node_id: str) -> dict:
        return self._one("SELECT * FROM nodes WHERE id=?", (node_id,))

    def cycle(self, cycle_id: str) -> dict:
        return self._one("SELECT * FROM research_cycles WHERE id=?", (cycle_id,))

    def cycles(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM research_cycles WHERE project_id=? ORDER BY created_at", (project_id,))

    def work_item(self, work_id: str) -> dict:
        value = self._one("SELECT * FROM work_items WHERE id=?", (work_id,))
        value["steps"] = self.steps(work_id)
        value["findings"] = self.findings(work_id)
        return value

    def work_items(self, project_id: str) -> list[dict]:
        return [self.work_item(row["id"]) for row in self._rows("SELECT id FROM work_items WHERE project_id=? ORDER BY created_at", (project_id,))]

    def step(self, step_id: str) -> dict:
        return self._one("SELECT * FROM workflow_steps WHERE id=?", (step_id,))

    def steps(self, work_id: str) -> list[dict]:
        return self._many("SELECT * FROM workflow_steps WHERE work_item_id=? ORDER BY ordinal", (work_id,))

    def findings(self, work_id: str) -> list[dict]:
        return self._many("SELECT * FROM findings WHERE work_item_id=? ORDER BY created_at", (work_id,))

    def project_findings(self, project_id: str) -> list[dict]:
        sql = "SELECT f.* FROM findings f JOIN work_items w ON w.id=f.work_item_id WHERE w.project_id=? ORDER BY f.created_at"
        return self._many(sql, (project_id,))

    def project_attempts(self, project_id: str) -> list[dict]:
        sql = "SELECT a.*,wa.work_item_id,l.artifact_id AS log_artifact_id FROM attempts a JOIN work_item_attempts wa ON wa.attempt_id=a.id LEFT JOIN attempt_logs l ON l.attempt_id=a.id JOIN work_items w ON w.id=wa.work_item_id WHERE w.project_id=? ORDER BY a.created_at"
        return self._many(sql, (project_id,))

    def project_calls(self, project_id: str) -> list[dict]:
        return self._many("SELECT * FROM project_calls WHERE project_id=? ORDER BY created_at", (project_id,))

    def _active_cycles(self) -> list[dict]:
        return self._many("SELECT * FROM research_cycles WHERE status='active'", ())

    def _interrupted_brief(self) -> dict:
        return {"title": "Research cycle interrupted", "learned": [], "limitations": ["Control plane restarted during execution."], "open_questions": ["Resume this direction to continue."], "next_moves": ["Continue this direction from the Project Lead."]}

    def _add_direction(self, project_id: str, question_id: str, value: dict, position: int) -> dict:
        payload = {**value, "position": position}
        direction = self.add_research_node(project_id, "direction", payload, "proposed")
        self.add_edge(question_id, direction["id"], "opens")
        return direction

    def _add_brief_node(self, cycle: dict, brief: dict) -> None:
        node = self.add_research_node(cycle["project_id"], "brief", {**brief, "cycle_id": cycle["id"]})
        self.add_edge(node["id"], cycle["direction_id"], "summarizes")

    def _insert_steps(self, work_id: str, roles: tuple[str, ...]) -> None:
        rows = [(stable_id("step", {"work": work_id, "ordinal": index}), work_id, index, role, "pending", None, "{}", None, None) for index, role in enumerate(roles)]
        with self.world.db.connect() as connection:
            connection.executemany("INSERT INTO workflow_steps VALUES(?,?,?,?,?,?,?,?,?)", rows)

    def _validate_gate(self, work_id: str) -> None:
        steps = self.steps(work_id)
        if any(step["status"] != "completed" for step in steps):
            raise ValueError("workflow coverage is incomplete")
        if any(item["severity"] in BLOCKING and item["status"] == "open" for item in self.findings(work_id)):
            raise ValueError("blocking review findings remain open")

    def _question_id(self, project_id: str) -> str:
        return self._one("SELECT id FROM nodes WHERE project_id=? AND kind='question'", (project_id,))["id"]

    def _require_status(self, value: dict, allowed: set[str]) -> None:
        if value["status"] not in allowed:
            raise ValueError(f"invalid state: {value['status']}")

    def _index_node(self, node_id: str, project_id: str, payload: dict) -> None:
        text = " ".join(str(value) for value in payload.values() if isinstance(value, (str, int, float)))
        self._execute("INSERT INTO node_fts VALUES(?,?,?)", (node_id, project_id, text))

    def _write_log_file(self, attempt_id: str, content: bytes) -> None:
        root = self.world.artifacts.root.parent / "logs"
        root.mkdir(exist_ok=True)
        (root / f"{attempt_id.replace(':', '-')}.log").write_bytes(content)

    def _execute(self, sql: str, values: tuple) -> None:
        with self.world.db.connect() as connection:
            connection.execute(sql, values)

    def _rows(self, sql: str, values: tuple = ()):
        with self.world.db.connect() as connection:
            return connection.execute(sql, values).fetchall()

    def _one(self, sql: str, values: tuple) -> dict:
        rows = self._rows(sql, values)
        if not rows:
            raise KeyError(values[0])
        return decode(rows[0])

    def _many(self, sql: str, values: tuple) -> list[dict]:
        return [decode(row) for row in self._rows(sql, values)]

    def _json(self, value: object) -> str:
        return json.dumps(value, ensure_ascii=False)
