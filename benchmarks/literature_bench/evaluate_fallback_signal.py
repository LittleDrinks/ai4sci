#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-corpus", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--full-predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def fit_graph(corpus):
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    texts = [row["title"] + " ".join(row["abstract"]) for row in corpus]
    return vectorizer, vectorizer.fit_transform(texts)


def score_claim(vectorizer, matrix, claim, corpus):
    query = vectorizer.transform([claim["claim"]]).todense()
    scores = np.asarray(matrix @ query.T).squeeze()
    order = scores.argsort()[::-1]
    top = {corpus[index]["doc_id"] for index in order[:3]}
    return float(scores[order[0]]), float(scores[order[0]] - scores[order[1]]), top


def rows_for_claims(corpus, claims):
    vectorizer, matrix = fit_graph(corpus)
    graph_ids = {row["doc_id"] for row in corpus}
    rows = []
    for claim in claims:
        if not claim["evidence"]:
            continue
        score, margin, top = score_claim(vectorizer, matrix, claim, corpus)
        gold = set(map(int, claim["evidence"]))
        rows.append({"id": claim["id"], "score": score, "margin": margin, "coverage": bool(gold & graph_ids), "graph_hit": bool(gold & top)})
    return rows


def auc(rows, field, target):
    return float(roc_auc_score([row[target] for row in rows], [row[field] for row in rows]))


def frontier(rows, full_hits):
    ordered = sorted(rows, key=lambda row: row["score"])
    result = []
    for percent in range(0, 101, 10):
        count = round(len(rows) * percent / 100)
        fallback = {row["id"] for row in ordered[:count]}
        hits = sum(full_hits[row["id"]] if row["id"] in fallback else row["graph_hit"] for row in rows)
        result.append({"fallback_percent": percent, "hit_one": hits / len(rows)})
    return result


def full_hits(claims, predictions):
    pred = {row["claim_id"]: set(row["doc_ids"]) for row in predictions}
    return {claim["id"]: bool(set(map(int, claim["evidence"])) & pred[claim["id"]]) for claim in claims if claim["evidence"]}


def main():
    args = parse_args()
    corpus, claims = read_jsonl(args.graph_corpus), read_jsonl(args.claims)
    rows = rows_for_claims(corpus, claims)
    hits = full_hits(claims, read_jsonl(args.full_predictions))
    result = {"evidence_claims": len(rows), "score_auc_for_coverage": auc(rows, "score", "coverage"), "score_auc_for_graph_hit": auc(rows, "score", "graph_hit"), "margin_auc_for_coverage": auc(rows, "margin", "coverage"), "frontier": frontier(rows, hits)}
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
