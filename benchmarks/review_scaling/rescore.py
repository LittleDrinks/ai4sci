#!/usr/bin/env python3
"""Rescore saved ReviewScaling responses after scorer corrections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from questions import score_response
from run import _aggregate, _score_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def rescore(report: dict) -> dict:
    for case in report["cases"]:
        case["scores"] = score_response(case["model_answer"], case["gold"])
        case["summary"] = _score_summary(case["scores"])
    report["aggregate"] = _aggregate(report["cases"])
    report["scorer_version"] = "nested-values-v2"
    return report


def main() -> int:
    args = parse_args()
    report = json.loads(args.source.read_text(encoding="utf-8"))
    result = rescore(report)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
