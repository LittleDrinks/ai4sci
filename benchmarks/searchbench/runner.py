#!/usr/bin/env python3
"""Compare Matbench planning policies with admission-time review."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


MODEL = "gpt-5.4-mini"
POLICIES = ("B", "B_TO_R", "B_PLUS_F", "R")
FIELDS = (
    "title", "mechanism", "protocol", "code_plan", "validation",
    "expected_observation", "falsifier", "dependencies", "compute_estimate",
)
TASK = {
    "dataset": "Matbench matbench_expt_gap",
    "input": "chemical composition",
    "target": "experimental band gap in eV",
    "evaluation": "official five fixed folds and mean MAE",
    "size": 4604,
    "constraints": [
        "held-out fold targets are unavailable",
        "one executable method per submission",
        "CPU execution under 30 minutes per fold",
        "no external target labels or benchmark result lookup",
    ],
}
HISTORY = {
    "question": "Predict experimental band gap from composition.",
    "admitted_routes": [
        {
            "id": "route.rf-magpie",
            "mechanism": "Weighted elemental Magpie descriptors with a 500-tree random forest.",
            "observation": "Official Matbench mean MAE 0.4461.",
        },
        {
            "id": "route.crabnet",
            "mechanism": "Compositionally restricted self-attention over element and stoichiometry tokens.",
            "observation": "Official Matbench mean MAE 0.3463.",
        }
    ],
}
PLANNER_ROLE = """
Propose one executable method for the supplied scientific benchmark. Return one
JSON object with exactly these string keys: title, mechanism, protocol,
code_plan, validation, expected_observation, falsifier, dependencies,
compute_estimate. Change the core modeling mechanism, not only hyperparameters.
Do not claim execution, invent data, use hidden labels, list alternatives, or
name a method family. No markdown or additional text.
""".strip()
MECHANISM_ROLE = """
Judge whether a candidate action and an admitted route use the same core causal
or algorithmic mechanism. Ignore titles, shared task, data, expected outcome,
hyperparameters, and implementation details that do not change the mechanism.
Return one JSON object only:
{"judgment":"same|different|uncertain","reason":"one sentence"}
""".strip()
EXECUTION_ROLE = """
Audit one proposed action for task fit, hidden-label leakage, executability under
the stated budget, and falsifiability. Do not judge similarity to other methods.
Return one JSON object only:
{"status":"accepted|rejected|uncertain","codes":["short_code"],"reason":"one sentence"}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--harness-path", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--candidates-per-seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--model", default=MODEL)
    return parser.parse_args()


def load_secret(name: str, aliases: tuple[str, ...]) -> str:
    for key in (name, *aliases):
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(f"missing credential environment variable: {name}")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode_json(text: str) -> dict:
    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        try:
            value = json.loads(match.group(0)) if match else {}
        except json.JSONDecodeError:
            value = {}
    return value if isinstance(value, dict) else {}


def candidate_fields(text: str) -> dict[str, str]:
    value = decode_json(text)
    return {key: str(value.get(key, "")).strip() for key in FIELDS}


def candidate_uid(candidate: dict[str, str]) -> str:
    digest = hashlib.sha256(canonical(candidate).encode()).hexdigest()
    return f"candidate:{digest}"


def trace_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def row_usage(row: dict) -> dict[str, int]:
    payload = row.get("payload", {})
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    usage = response.get("usage", {}) if isinstance(response, dict) else {}
    return {key: int(usage.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def trace_metrics(path_value: str) -> dict:
    path = Path(path_value) if path_value else Path("__missing_trace__")
    rows = trace_rows(path)
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    usage = {key: sum(row_usage(row)[key] for row in rows) for key in keys}
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    return {"path": str(path), "sha256": digest, "events": len(rows), "usage": usage}


def make_agent(common: dict, workspace: Path, trace_dir: Path, role: str, output_tokens: int):
    sys.path.insert(0, str(common["harness_path"]))
    from researchharness.runtime import create_agent

    return create_agent(
        model_name=common["model"], api_key=common["api_key"],
        api_base=common["api_base"], timeout_seconds=180,
        max_input_tokens=12000, max_output_tokens=output_tokens, max_retries=2,
        omit_generate_params=("presence_penalty",), max_rounds=1,
        max_runtime_seconds=240, workspace_root=str(workspace),
        trace_dir=str(trace_dir), role_prompt=role, tools=[], require_env=False,
    )


def run_session(agent, prompt: str, workspace: Path, prior: list[dict] | None = None) -> dict:
    return agent._run_session(prompt, workspace_root=str(workspace), prior_messages=prior)


def planner_prompt(mode: str, seed: int, slot: int, codes: list[str] | None = None, history: dict | None = None) -> str:
    payload = {"task": TASK, "seed_label": seed, "candidate_slot": slot}
    if mode != "blind":
        payload["admitted_graph_slice"] = history or HISTORY
    if codes:
        payload["minimal_review_codes"] = codes
    return PLANNER_ROLE + "\n\n" + canonical(payload)


def planner_record(session: dict, mode: str) -> dict:
    text = str(session.get("result_text", ""))
    candidate = candidate_fields(text)
    return {
        "mode": mode, "candidate_uid": candidate_uid(candidate), "candidate": candidate,
        "raw_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "messages": session.get("messages", []),
        "trace": trace_metrics(str(session.get("trace_path", ""))),
    }


def run_planner(common: dict, case: dict, mode: str, codes=None, prior=None, history=None) -> dict:
    workspace = case["workspace"] / mode
    trace_dir = case["traces"] / mode
    workspace.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    agent = make_agent(common, workspace, trace_dir, PLANNER_ROLE, 1000)
    prompt = planner_prompt(mode, case["seed"], case["slot"], codes, history)
    return planner_record(run_session(agent, prompt, workspace, prior), mode)


def mechanism_prompt(candidate: dict, route: dict) -> str:
    payload = {"task": TASK, "admitted_route": route, "candidate": candidate}
    return MECHANISM_ROLE + "\n\n" + canonical(payload)


def execution_prompt(candidate: dict) -> str:
    return EXECUTION_ROLE + "\n\n" + canonical({"task": TASK, "candidate": candidate})


def parse_execution(text: str) -> dict:
    value = decode_json(text)
    status = str(value.get("status", "")).lower()
    codes = value.get("codes", [])
    valid = status in {"accepted", "rejected", "uncertain"}
    return {
        "status": status if valid else "uncertain",
        "codes": [str(code) for code in codes] if isinstance(codes, list) else [],
        "reason": str(value.get("reason", "")), "parse_status": "ok" if valid else "invalid",
    }


def parse_mechanism(text: str) -> dict:
    value = decode_json(text)
    judgment = str(value.get("judgment", "")).lower()
    valid = judgment in {"same", "different", "uncertain"}
    status = {"same": "rejected", "different": "accepted"}.get(judgment, "uncertain")
    codes = ["duplicate_mechanism"] if judgment == "same" else []
    return {"status": status, "judgment": judgment if valid else "uncertain", "codes": codes, "reason": str(value.get("reason", "")), "parse_status": "ok" if valid else "invalid"}


def audit_spec(kind: str) -> tuple[str, str, int]:
    if kind == "mechanism":
        return MECHANISM_ROLE, "mechanism", 350
    return EXECUTION_ROLE, "execution", 500


def audit_tag(suffix: str, kind: str, reviewer: str, route: dict | None) -> str:
    route_tag = f"-{route['id'].split('.')[-1]}" if route else ""
    return f"audit-{suffix}-{kind}{route_tag}-{reviewer.lower()}"


def run_auditor(common: dict, case: dict, candidate: dict, reviewer: str, suffix: str, kind: str, route=None) -> dict:
    tag = audit_tag(suffix, kind, reviewer, route)
    workspace = case["workspace"] / tag
    traces = case["traces"] / tag
    workspace.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)
    role, dimension, output_tokens = audit_spec(kind)
    agent = make_agent(common, workspace, traces, role, output_tokens)
    prompt = mechanism_prompt(candidate, route) if route else execution_prompt(candidate)
    session = run_session(agent, prompt, workspace)
    text = str(session.get("result_text", ""))
    parser = parse_mechanism if kind == "mechanism" else parse_execution
    route_id = route["id"] if route else None
    return {"reviewer": reviewer, "dimension": dimension, "route_id": route_id, **parser(text), "trace": trace_metrics(str(session.get("trace_path", "")))}


def dimension_status(reviews: list[dict]) -> str:
    statuses = [review["status"] for review in reviews]
    return statuses[0] if len(set(statuses)) == 1 else "human_review"


def mechanism_relations(reviews: list[dict]) -> list[dict]:
    ids = [route["id"] for route in HISTORY["admitted_routes"]]
    return [{"route_id": route_id, "status": dimension_status([r for r in reviews if r["route_id"] == route_id])} for route_id in ids]


def mechanism_status(relations: list[dict]) -> str:
    statuses = [relation["status"] for relation in relations]
    if "rejected" in statuses:
        return "rejected"
    return "accepted" if all(status == "accepted" for status in statuses) else "human_review"


def aggregate_audit(reviews: list[dict]) -> dict:
    relations = mechanism_relations([r for r in reviews if r["dimension"] == "mechanism"])
    execution = dimension_status([r for r in reviews if r["dimension"] == "execution"])
    dimensions = {"mechanism": mechanism_status(relations), "execution": execution}
    status = "rejected" if "rejected" in dimensions.values() else "human_review" if "human_review" in dimensions.values() or "uncertain" in dimensions.values() else "accepted"
    codes = sorted({code for review in reviews for code in review["codes"]})
    agreement = all(value != "human_review" for value in dimensions.values())
    return {"status": status, "codes": codes, "dimensions": dimensions, "mechanism_relations": relations, "reviewer_agreement": agreement, "reviews": reviews}


def audit_jobs(suffix: str) -> list[tuple]:
    jobs = [(reviewer, suffix, "mechanism", route) for route in HISTORY["admitted_routes"] for reviewer in ("A", "B")]
    jobs.extend((reviewer, suffix, "execution", None) for reviewer in ("A", "B"))
    return jobs


def audit_candidate(common: dict, case: dict, candidate: dict, suffix: str) -> dict:
    missing = [key for key in FIELDS if not candidate.get(key)]
    if missing:
        review = {"reviewer": "schema", "status": "rejected", "codes": ["missing_fields"], "reason": ",".join(missing), "parse_status": "deterministic"}
        return {"status": "rejected", "codes": ["missing_fields"], "reviewer_agreement": True, "reviews": [review]}
    jobs = audit_jobs(suffix)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        reviews = list(pool.map(lambda job: run_auditor(common, case, candidate, *job), jobs))
    return aggregate_audit(reviews)


def branch_record(policy: str, planner: dict, audit: dict, source: str) -> dict:
    clean = {key: value for key, value in planner.items() if key != "messages"}
    return {"policy": policy, "source": source, "planner": clean, "audit": audit}


def transition(common: dict, case: dict, blind: dict, audit: dict, same_session: bool) -> dict:
    mode = "same_session_feedback" if same_session else "reflect_after_rejection"
    prior = blind["messages"] if same_session else None
    planner = run_planner(common, case, mode, audit["codes"], prior)
    followup_audit = audit_candidate(common, case, planner["candidate"], mode)
    policy = "B_PLUS_F" if same_session else "B_TO_R"
    return branch_record(policy, planner, followup_audit, "transition")


def blind_branches(common: dict, case: dict, blind: dict, audit: dict) -> list[dict]:
    rows = [branch_record("B", blind, audit, "blind")]
    if audit["status"] != "rejected":
        rows.extend(branch_record(policy, blind, audit, "blind_reused") for policy in ("B_TO_R", "B_PLUS_F"))
        return rows
    rows.append(transition(common, case, blind, audit, False))
    rows.append(transition(common, case, blind, audit, True))
    return rows


def run_case(case: dict, common: dict) -> list[dict]:
    blind = run_planner(common, case, "blind")
    blind_audit = audit_candidate(common, case, blind["candidate"], "blind")
    rows = blind_branches(common, case, blind, blind_audit)
    reflect = run_planner(common, case, "reflect")
    reflect_audit = audit_candidate(common, case, reflect["candidate"], "reflect")
    rows.append(branch_record("R", reflect, reflect_audit, "reflect"))
    return [{"case_id": case["id"], "seed": case["seed"], "slot": case["slot"], **row} for row in rows]


def append_jsonl(path: Path, rows: list[dict], lock: threading.Lock) -> None:
    with lock, path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical(row) + "\n")


def cases(output: Path, seeds: int, slots: int) -> list[dict]:
    values = []
    for seed in range(seeds):
        for slot in range(slots):
            case_id = f"s{seed}-c{slot}"
            values.append({"id": case_id, "seed": seed, "slot": slot, "workspace": output / "workspaces" / case_id, "traces": output / "traces" / case_id})
    return values


def row_traces(row: dict) -> list[dict]:
    traces = [row["planner"]["trace"]]
    for review in row["audit"]["reviews"]:
        if review.get("trace"):
            traces.append(review["trace"])
    return traces


def unique_usage(rows: list[dict]) -> int:
    traces = {trace["path"]: trace for row in rows for trace in row_traces(row)}
    return sum(trace["usage"]["total_tokens"] for trace in traces.values())


def summary(rows: list[dict]) -> dict:
    counts = {policy: sum(row["policy"] == policy for row in rows) for policy in POLICIES}
    statuses = ("accepted", "rejected", "human_review", "uncertain")
    outcome_counts = {status: sum(row["audit"]["status"] == status for row in rows) for status in statuses}
    unique = {row["planner"]["trace"]["path"]: row for row in rows}
    admission_counts = {status: sum(row["audit"]["status"] == status for row in unique.values()) for status in statuses}
    transitions = sum(row["source"] == "transition" for row in rows)
    return {"outcome_rows": len(rows), "planner_calls": len(unique), "policy_counts": counts, "outcome_row_counts": outcome_counts, "unique_admission_counts": admission_counts, "transitions": transitions, "total_tokens": unique_usage(rows), "method_family_adjudication": "not_run"}


def write_manifest(output: Path, args: argparse.Namespace, api_base: str, values: list[dict]) -> None:
    manifest = {
        "benchmark": "SearchBench-v3-Matbench-multi-route-planning",
        "created_at": datetime.now(timezone.utc).isoformat(), "model": args.model,
        "api_base_host": urlsplit(api_base).netloc, "task": TASK, "history": HISTORY,
        "policies": list(POLICIES), "cases": len(values), "execution": "planning_and_admission_only",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def run_all(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    api_base = load_secret("API_BASE", ("BASEURL", "OPENAI_BASE_URL", "baseurl"))
    api_key = load_secret("API_KEY", ("APIKEY", "OPENAI_API_KEY", "apikey"))
    common = {"model": args.model, "api_base": api_base, "api_key": api_key, "harness_path": args.harness_path.resolve()}
    values = cases(output, args.seeds, args.candidates_per_seed)
    write_manifest(output, args, api_base, values)
    path, lock = output / "results.jsonl", threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_case, case, common) for case in values]
        for future in concurrent.futures.as_completed(futures):
            append_jsonl(path, future.result(), lock)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    (output / "summary.json").write_text(json.dumps(summary(rows), indent=2) + "\n")


def main() -> int:
    args = parse_args()
    if min(args.seeds, args.candidates_per_seed, args.workers) < 1:
        raise SystemExit("seeds, candidates-per-seed, and workers must be positive")
    run_all(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
