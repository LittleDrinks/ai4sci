#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from benchmarks.literature_bench.evaluate_fallback_signal import fit_graph, score_claim
from benchmarks.literature_bench.prepare_scifact_graph import graph_documents


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def graph_corpus(train, held_out):
    mapping = graph_documents(train, held_out)
    return [{"doc_id": doc_id, "title": " ".join(sorted(claims)), "abstract": []} for doc_id, claims in sorted(mapping.items())]


def retrieval_rows(graph, full, claims):
    graph_vectorizer, graph_matrix = fit_graph(graph)
    full_vectorizer, full_matrix = fit_graph(full)
    rows = []
    for claim in claims:
        if not claim["evidence"]:
            continue
        score, _, graph_top = score_claim(graph_vectorizer, graph_matrix, claim, graph)
        _, _, full_top = score_claim(full_vectorizer, full_matrix, claim, full)
        gold = set(map(int, claim["evidence"]))
        rows.append({"id": claim["id"], "score": score, "graph_hit": bool(gold & graph_top), "full_hit": bool(gold & full_top)})
    return rows


def threshold_result(rows, threshold):
    fallback = [row for row in rows if row["score"] < threshold]
    hits = sum(row["full_hit"] if row["score"] < threshold else row["graph_hit"] for row in rows)
    return {"threshold": threshold, "hit_one": hits / len(rows), "fallback_rate": len(fallback) / len(rows)}


def calibrate(rows):
    candidates = sorted({row["score"] for row in rows}) + [float("inf")]
    results = [threshold_result(rows, threshold) for threshold in candidates]
    return max(results, key=lambda row: (row["hit_one"], -row["fallback_rate"]))


def split_train(train):
    calibration = [row for row in train if row["id"] % 5 == 0]
    build = [row for row in train if row["id"] % 5 != 0]
    return build, calibration


def main():
    args = parse_args()
    train = read_jsonl(args.data / "claims_train.jsonl")
    dev, full = read_jsonl(args.data / "claims_dev.jsonl"), read_jsonl(args.data / "corpus.jsonl")
    build, calibration = split_train(train)
    calibration_rows = retrieval_rows(graph_corpus(build, calibration), full, calibration)
    selected = calibrate(calibration_rows)
    dev_rows = retrieval_rows(graph_corpus(train, dev), full, dev)
    result = {"build_claims": len(build), "calibration_claims": len(calibration_rows), "calibration": selected, "dev": threshold_result(dev_rows, selected["threshold"])}
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
