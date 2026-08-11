#!/usr/bin/env python3
"""Adjudicate a small, independent sample of SearchBench candidate pairs."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit


MODEL = "gpt-5.4-mini"
FIELDS = (
    "title", "mechanism", "protocol", "code_plan", "validation",
    "expected_observation", "falsifier", "dependencies", "compute_estimate",
)
LABELS = ("same", "different", "uncertain")
REVIEWERS = ("A", "B")
DEFAULT_PAIR_BUDGET = 30
ROLE_PROMPT = """
You are an independent reviewer for a scientific method-family audit. Judge only
whether the two candidate actions use the same core causal/algorithmic mechanism.
Do not use titles, shared data, Bayesian vocabulary, expected outcomes, or
candidate self-labels as a shortcut. Treat implementation details as different
only when they change the central mechanism. Do not invent a global taxonomy or
assign family names. Return exactly one JSON object:
{"judgment":"same|different|uncertain","confidence":"low|medium|high","rationale":"brief evidence-based reason"}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--harness-path", type=Path, required=True)
    parser.add_argument("--task-info", type=Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--pair-budget", type=int, default=DEFAULT_PAIR_BUDGET)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def load_secret(name: str, aliases: tuple[str, ...]) -> str:
    for key in (name, *aliases):
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError(f"missing credential environment variable: {name}")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def task_text(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    return " ".join(str(value.get("task", "")).split())


def candidate_from_row(row: dict) -> dict | None:
    if row.get("audit", {}).get("status") != "accepted":
        return None
    source = row.get("planner", {}).get("candidate", {})
    fields = {key: str(source.get(key, "")).strip() for key in FIELDS}
    if not all(fields.values()):
        return None
    source_id = str(row.get("planner", {}).get("candidate_uid") or source.get("candidate_id", "")).strip()
    digest = digest_text(canonical(fields))
    return {"id": f"candidate:{digest}", "source_id": source_id, "strategy": row.get("policy", ""), "seed": row.get("seed"), "candidate_index": row.get("slot"), "fields": fields, "sha256": digest}


def load_candidates(path: Path) -> list[dict]:
    candidates = {}
    for row in read_jsonl(path):
        item = candidate_from_row(row)
        if item:
            candidates.setdefault(item["sha256"], item)
    if len(candidates) < 3:
        raise RuntimeError("at least three accepted candidates are required")
    if not all(candidates):
        raise RuntimeError("accepted candidate ids must be non-empty")
    return list(candidates.values())


def stable_order(candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=lambda item: digest_text(item["id"]))


def add_pair(pairs: list[tuple[dict, dict]], seen: set[tuple[str, str]], a: dict, b: dict) -> None:
    key = tuple(sorted((a["id"], b["id"])))
    if a["id"] != b["id"] and key not in seen:
        pairs.append((a, b))
        seen.add(key)


def sample_pairs(candidates: list[dict], budget: int) -> list[tuple[dict, dict]]:
    order = stable_order(candidates)
    maximum = len(order) * (len(order) - 1) // 2
    if budget < len(order) or budget > maximum:
        raise ValueError(f"pair budget must be in [{len(order)}, {maximum}]")
    pairs: list[tuple[dict, dict]] = []
    seen: set[tuple[str, str]] = set()
    for i, candidate in enumerate(order):
        add_pair(pairs, seen, candidate, order[(i + 1) % len(order)])
    offset = 2
    while len(pairs) < budget:
        for i, candidate in enumerate(order):
            add_pair(pairs, seen, candidate, order[(i + offset) % len(order)])
            if len(pairs) == budget:
                break
        offset += 1
    return pairs


def pair_id(a: dict, b: dict) -> str:
    return "pair-" + digest_text("\0".join(sorted((a["id"], b["id"]))))[:12]


def prompt_candidate(candidate: dict) -> dict:
    return {"candidate_ref": candidate["id"], **candidate["fields"]}


def review_prompt(task: str, a: dict, b: dict, reverse: bool) -> str:
    first, second = (b, a) if reverse else (a, b)
    payload = {"task": task, "candidate_first": prompt_candidate(first), "candidate_second": prompt_candidate(second)}
    return ROLE_PROMPT + "\n\nJudge this unordered pair. The presentation order is only a symmetry check.\n" + canonical(payload)


def create_reviewer(harness_path: Path, trace_dir: Path, workspace: Path, model: str, api_key: str, api_base: str):
    sys.path.insert(0, str(harness_path))
    from researchharness.runtime import create_agent

    return create_agent(model_name=model, api_key=api_key, api_base=api_base, timeout_seconds=180, max_input_tokens=12000, max_output_tokens=500, max_retries=2, omit_generate_params=("presence_penalty",), max_rounds=1, max_runtime_seconds=240, workspace_root=str(workspace), trace_dir=str(trace_dir), role_prompt=ROLE_PROMPT, tools=[], require_env=False)


def run_session(agent, prompt: str, workspace: Path) -> dict:
    return agent._run_session(prompt, workspace_root=str(workspace))


def trace_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def usage_from_row(row: dict) -> dict[str, int]:
    payload = row.get("payload", {})
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    usage = response.get("usage", {}) if isinstance(response, dict) else {}
    return {key: int(usage.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}


def trace_metrics(path_value: str) -> dict:
    path = Path(path_value) if path_value else Path("__missing_trace__")
    rows = trace_rows(path)
    usage = {key: sum(usage_from_row(row)[key] for row in rows) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {"trace_path": str(path), "trace_sha256": digest_file(path), "trace_events": len(rows), "usage": usage}


def decode_json(text: str) -> dict:
    try:
        value = json.loads(text.strip())
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        try:
            value = json.loads(match.group(0)) if match else {}
        except json.JSONDecodeError:
            value = {}
        return value if isinstance(value, dict) else {}


def parse_review(text: str) -> dict:
    value = decode_json(text)
    judgment = str(value.get("judgment", "")).strip().lower()
    return {"judgment": judgment if judgment in LABELS else "uncertain", "confidence": str(value.get("confidence", "")).strip().lower(), "rationale": str(value.get("rationale", "")).strip(), "parse_status": "ok" if judgment in LABELS else "invalid"}


def reviewer_record(session: dict, prompt: str, prompt_path: Path, reviewer: str, reverse: bool) -> dict:
    text = str(session.get("result_text", ""))
    return {"reviewer": reviewer, "orientation": "b_then_a" if reverse else "a_then_b", **parse_review(text), "prompt_path": str(prompt_path), "prompt_sha256": digest_text(prompt), "raw_result_sha256": digest_text(text), "trace": trace_metrics(str(session.get("trace_path", "")))}


def failed_reviewer(error: Exception, prompt: str, prompt_path: Path, reviewer: str, reverse: bool) -> dict:
    return {"reviewer": reviewer, "orientation": "b_then_a" if reverse else "a_then_b", "judgment": "uncertain", "confidence": "", "rationale": "", "parse_status": "error", "error_type": type(error).__name__, "prompt_path": str(prompt_path), "prompt_sha256": digest_text(prompt), "raw_result_sha256": "", "trace": trace_metrics("")}


def run_reviewer(job: dict) -> dict:
    prompt_path = job["prompt_path"]
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = review_prompt(job["task"], job["a"], job["b"], job["reverse"])
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    workspace = job["output"] / "workspaces" / job["pair_id"] / job["reviewer"].lower()
    trace_dir = job["output"] / "traces" / job["pair_id"] / job["reviewer"].lower()
    workspace.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)
    try:
        agent = create_reviewer(job["harness_path"], trace_dir, workspace, job["model"], job["api_key"], job["api_base"])
        session = run_session(agent, prompt, workspace)
        return reviewer_record(session, prompt, prompt_path, job["reviewer"], job["reverse"])
    except Exception as error:
        return failed_reviewer(error, prompt, prompt_path, job["reviewer"], job["reverse"])


def run_pair(index: int, pair: tuple[dict, dict], common: dict) -> dict:
    a, b = pair
    pid = pair_id(a, b)
    jobs = [{"pair_id": pid, "a": a, "b": b, "reviewer": reviewer, "reverse": reviewer == "B", "prompt_path": common["output"] / "prompts" / pid / f"reviewer-{reviewer.lower()}.txt", **common} for reviewer in REVIEWERS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        reviews = list(pool.map(run_reviewer, jobs))
    labels = [review["judgment"] for review in reviews]
    agreement = reviews[0]["parse_status"] == reviews[1]["parse_status"] == "ok" and labels[0] == labels[1]
    provisional = labels[0] if agreement else "uncertain"
    return {"pair_index": index, "pair_id": pid, "candidate_a": a["id"], "candidate_b": b["id"], "candidate_a_source_id": a["source_id"], "candidate_b_source_id": b["source_id"], "candidate_a_sha256": a["sha256"], "candidate_b_sha256": b["sha256"], "reviews": reviews, "provisional_judgment": provisional, "reviewer_agreement": agreement, "presentation_order_symmetric": labels[0] == labels[1]}


def pair_type(a: dict, b: dict) -> str:
    left, right = sorted((str(a["strategy"]), str(b["strategy"])))
    return f"{left}__{right}"


def build_pairs(records: list[dict]) -> dict[tuple[str, str], dict]:
    return {tuple(sorted((record["candidate_a"], record["candidate_b"]))): record for record in records}


def triangle_count(candidates: list[dict], pair_keys: set[tuple[str, str]]) -> int:
    ids = [candidate["id"] for candidate in candidates]
    return sum(all(tuple(sorted(edge)) in pair_keys for edge in ((x, y), (y, z), (x, z))) for x, y, z in combinations(ids, 3))


def transitivity_conflicts(records: list[dict], candidates: list[dict]) -> int:
    edges = build_pairs(records)
    ids = [candidate["id"] for candidate in candidates]
    conflicts = 0
    for x, y, z in combinations(ids, 3):
        labels = [edges.get(tuple(sorted(pair)), {}).get("provisional_judgment") for pair in ((x, y), (y, z), (x, z))]
        if labels.count("same") == 2 and labels.count("different") == 1:
            conflicts += 1
    return conflicts


def pair_type_counts(records: list[dict], candidates: list[dict]) -> dict[str, int]:
    lookup = {candidate["id"]: candidate for candidate in candidates}
    counts: dict[str, int] = {}
    for record in records:
        key = pair_type(lookup[record["candidate_a"]], lookup[record["candidate_b"]])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def total_usage(records: list[dict]) -> dict[str, int]:
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    return {key: sum(review["trace"]["usage"][key] for record in records for review in record["reviews"]) for key in keys}


def summarize(records: list[dict], candidates: list[dict], source: Path, model: str, api_base: str) -> dict:
    valid = [record for record in records if all(review["parse_status"] == "ok" for review in record["reviews"])]
    agreements = sum(record["reviewer_agreement"] for record in valid)
    symmetry = sum(record["presentation_order_symmetric"] for record in valid)
    pair_keys = {tuple(sorted((record["candidate_a"], record["candidate_b"]))) for record in records}
    labels = {label: sum(record["provisional_judgment"] == label for record in records) for label in LABELS}
    return {"benchmark": "SearchBench-family-adjudication", "status": "provisional_pair_judgments_only", "source_results": str(source), "source_results_sha256": digest_file(source), "model": model, "api_base_host": urlsplit(api_base).netloc, "accepted_candidates": len(candidates), "sampled_pairs": len(records), "reviewer_sessions": len(records) * 2, "usage": total_usage(records), "valid_pairs": len(valid), "reviewer_agreement_count": agreements, "reviewer_agreement_rate": agreements / len(valid) if valid else None, "presentation_order_symmetric_count": symmetry, "presentation_order_symmetry_rate": symmetry / len(valid) if valid else None, "reviewer_disagreement_count": len(valid) - agreements, "review_error_count": len(records) - len(valid), "provisional_label_counts": labels, "pair_type_counts": pair_type_counts(records, candidates), "closed_triangle_count": triangle_count(candidates, pair_keys), "transitivity_conflict_count": transitivity_conflicts(records, candidates)}


def sample_manifest(candidates: list[dict], pairs: list[tuple[dict, dict]], budget: int) -> dict:
    keys = {tuple(sorted((a["id"], b["id"]))) for a, b in pairs}
    return {"method": "sha256-ordered cycle plus short chords", "pair_budget": budget, "cycle_edges": len(candidates), "chord_edges": max(0, len(pairs) - len(candidates)), "closed_triangles": triangle_count(candidates, keys), "every_candidate_in_sample": len({item["id"] for pair in pairs for item in pair}) == len(candidates), "uses_method_family_hint": False, "global_taxonomy": False}


def write_manifest(output: Path, args: argparse.Namespace, candidates: list[dict], pairs: list[tuple[dict, dict]], api_base: str) -> None:
    manifest = {"benchmark": "SearchBench-family-adjudication", "created_at": datetime.now(timezone.utc).isoformat(), "source_results": str(args.results), "source_results_sha256": digest_file(args.results), "task_info": str(args.task_info), "model": args.model, "api_base_host": urlsplit(api_base).netloc, "accepted_candidates": len(candidates), "sample": sample_manifest(candidates, pairs, args.pair_budget), "reviewers": ["A", "B"], "reviewer_session_policy": "new ResearchHarness session per reviewer and pair; reviewer B sees reversed presentation order", "outputs": ["pair_judgments.jsonl", "summary.json", "prompts/", "traces/", "workspaces/"]}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(canonical(record) + "\n" for record in sorted(records, key=lambda item: item["pair_index"])), encoding="utf-8")


def run_all(args: argparse.Namespace) -> None:
    if args.workers < 1 or args.pair_budget < 1:
        raise ValueError("workers and pair budget must be positive")
    api_base = load_secret("API_BASE", ("BASEURL", "OPENAI_BASE_URL", "baseurl"))
    api_key = load_secret("API_KEY", ("APIKEY", "OPENAI_API_KEY", "apikey"))
    candidates = load_candidates(args.results)
    pairs = sample_pairs(candidates, args.pair_budget)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_manifest(output, args, candidates, pairs, api_base)
    common = {"task": task_text(args.task_info), "output": output, "harness_path": args.harness_path.resolve(), "model": args.model, "api_key": api_key, "api_base": api_base}
    jobs = [(index, pair) for index, pair in enumerate(pairs)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_pair, index, pair, common) for index, pair in jobs]
        records = [future.result() for future in futures]
    write_jsonl(output / "pair_judgments.jsonl", records)
    summary = summarize(records, candidates, args.results, args.model, api_base)
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_all(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
