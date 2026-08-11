"""Run GraphBench and write a JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

import networkx

sys.path.insert(0, str(Path(__file__).parent))

from scenarios import run_all


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("graphbench-report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_all()
    report = {
        "benchmark": "GraphBench",
        "version": "2026-08-09",
        "implementation": "networkx.DiGraph topology; stdlib event log and RLock semantics",
        "reused_library": {"name": "networkx", "version": networkx.__version__, "role": "dependency topology and descendant propagation"},
        "property_testing": "seeded deterministic traces; Hypothesis unavailable in execution environment",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": results,
        "passed": all(bool(result["passed"]) for result in results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "passed": report["passed"], "scenarios": len(results)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
