#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import threading
from pathlib import Path

from benchmarks.searchbench.runner import canonical, cases, dimension_status, load_secret, run_auditor, run_planner, row_traces


MODES = ("blind_redraw", "fresh_reflect", "same_session_feedback")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--harness-path", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--cases", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def control_route(planner):
    candidate = planner["candidate"]
    return {
        "id": f"route.control.{planner['candidate_uid'].split(':')[1][:12]}",
        "mechanism": candidate["mechanism"], "protocol": candidate["protocol"],
        "code_plan": candidate["code_plan"], "observation": "Known duplicate control.",
    }


def control_history(route):
    return {"question": "Predict experimental band gap from composition.", "admitted_routes": [route]}


def audit(common, case, candidate, route, suffix):
    jobs = [(reviewer, suffix, "mechanism", route) for reviewer in ("A", "B")]
    jobs += [(reviewer, suffix, "execution", None) for reviewer in ("A", "B")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        reviews = list(pool.map(lambda job: run_auditor(common, case, candidate, *job), jobs))
    return {
        "mechanism": dimension_status(reviews[:2]),
        "execution": dimension_status(reviews[2:]), "reviews": reviews,
    }


def redraw_case(case):
    return {**case, "workspace": case["workspace"] / "redraw", "traces": case["traces"] / "redraw"}


def recovery_planner(common, case, blind, route, mode):
    if mode == "blind_redraw":
        planner = run_planner(common, redraw_case(case), "blind")
        return {**planner, "mode": mode}
    prior = blind["messages"] if mode == "same_session_feedback" else None
    history = control_history(route)
    return run_planner(common, case, mode, ["duplicate_mechanism"], prior, history)


def clean_planner(planner):
    return {key: value for key, value in planner.items() if key != "messages"}


def run_case(common, case):
    blind = run_planner(common, case, "blind")
    route = control_route(blind)
    rows = []
    for mode in MODES:
        planner = recovery_planner(common, case, blind, route, mode)
        result = audit(common, case, planner["candidate"], route, mode)
        rows.append({"case_id": case["id"], "mode": mode, "control": route, "control_planner": clean_planner(blind), "planner": clean_planner(planner), "audit": result})
    return rows


def usage(rows):
    traces = {trace["path"]: trace for row in rows for trace in row_traces(row)}
    traces.update({row["control_planner"]["trace"]["path"]: row["control_planner"]["trace"] for row in rows})
    return sum(trace["usage"]["total_tokens"] for trace in traces.values())


def count_dimension(selected, dimension):
    statuses = ("accepted", "rejected", "human_review", "uncertain")
    return {status: sum(row["audit"][dimension] == status for row in selected) for status in statuses}


def summarize(rows):
    modes = {}
    for mode in MODES:
        selected = [row for row in rows if row["mode"] == mode]
        modes[mode] = {dimension: count_dimension(selected, dimension) for dimension in ("mechanism", "execution")}
    return {"rows": len(rows), "modes": modes, "total_tokens": usage(rows)}


def write_rows(path, rows, lock):
    with lock, path.open("a") as stream:
        for row in rows:
            stream.write(canonical(row) + "\n")


def common_args(args):
    return {
        "model": args.model,
        "api_base": load_secret("API_BASE", ("BASEURL", "OPENAI_BASE_URL", "baseurl")),
        "api_key": load_secret("API_KEY", ("APIKEY", "OPENAI_API_KEY", "apikey")),
        "harness_path": args.harness_path.resolve(),
    }


def write_manifest(output, args):
    manifest = {"benchmark": "SearchBench-recovery-control", "model": args.model, "cases": args.cases, "modes": list(MODES)}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def run_all(args):
    output, common = args.output.resolve(), common_args(args)
    output.mkdir(parents=True, exist_ok=True)
    write_manifest(output, args)
    path, lock = output / "results.jsonl", threading.Lock()
    values = cases(output, args.cases, 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_case, common, case) for case in values]
        for future in concurrent.futures.as_completed(futures):
            write_rows(path, future.result(), lock)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    (output / "summary.json").write_text(json.dumps(summarize(rows), indent=2) + "\n")


if __name__ == "__main__":
    run_all(parse_args())
