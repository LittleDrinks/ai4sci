#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import os
import re
from pathlib import Path
from urllib import request


CONDITIONS = ("claim_only", "scoped_evidence", "global_evidence")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--per-label", type=int, default=10)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def evidence_text(claim, corpus):
    passages = []
    for doc_id, groups in claim["evidence"].items():
        document = corpus[int(doc_id)]
        indices = sorted({index for group in groups for index in group["sentences"]})
        passages.append({"doc_id": int(doc_id), "title": document["title"], "sentences": [document["abstract"][i] for i in indices]})
    return passages


def claim_label(claim):
    labels = {group["label"] for groups in claim["evidence"].values() for group in groups}
    return next(iter(labels)) if len(labels) == 1 else ""


def select_cases(data, per_label):
    corpus = {row["doc_id"]: row for row in read_jsonl(data / "corpus.jsonl")}
    counts = {"SUPPORT": 0, "CONTRADICT": 0}
    selected = []
    for claim in read_jsonl(data / "claims_dev.jsonl"):
        label = claim_label(claim)
        if label not in counts or counts[label] >= per_label:
            continue
        counts[label] += 1
        selected.append({"id": claim["id"], "claim": claim["claim"], "label": label, "evidence": evidence_text(claim, corpus)})
    return selected


def prompt(case, condition, pool):
    payload = {"claim": case["claim"]}
    if condition == "scoped_evidence":
        payload["evidence_records"] = case["evidence"]
    if condition == "global_evidence":
        payload["evidence_records"] = pool
    return ("Classify the scientific claim only from the supplied evidence records. "
            "Return one JSON object: {\"label\":\"SUPPORT|CONTRADICT|UNKNOWN\"}. "
            "Use UNKNOWN when the records do not settle the claim. Do not use outside knowledge.\n" + json.dumps(payload))


def decode(text):
    match = re.search(r"\{.*\}", text, flags=re.S)
    value = json.loads(match.group(0)) if match else {}
    label = str(value.get("label", "UNKNOWN")).upper()
    return label if label in {"SUPPORT", "CONTRADICT", "UNKNOWN"} else "UNKNOWN"


def call_model(api, model, text):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": text}], "max_completion_tokens": 100}).encode()
    req = request.Request(api["url"], data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api['key']}"})
    with request.urlopen(req, timeout=180) as response:
        value = json.loads(response.read().decode())
    content = value["choices"][0]["message"]["content"]
    return decode(content), value.get("usage", {})


def run_one(api, model, case, condition, pool):
    prediction, usage = call_model(api, model, prompt(case, condition, pool))
    return {"case_id": case["id"], "condition": condition, "gold": case["label"], "prediction": prediction, "correct": prediction == case["label"], "usage": usage}


def credentials():
    base = next((os.getenv(key, "").strip() for key in ("baseurl", "BASEURL", "OPENAI_BASE_URL") if os.getenv(key, "").strip()), "")
    key = next((os.getenv(name, "").strip() for name in ("apikey", "APIKEY", "OPENAI_API_KEY") if os.getenv(name, "").strip()), "")
    if not base or not key:
        raise RuntimeError("missing endpoint credentials")
    return {"url": base.rstrip("/") + "/chat/completions", "key": key}


def summarize(rows):
    result = {}
    for condition in CONDITIONS:
        selected = [row for row in rows if row["condition"] == condition]
        result[condition] = {"correct": sum(row["correct"] for row in selected), "total": len(selected), "tokens": sum(int(row["usage"].get("total_tokens", 0) or 0) for row in selected)}
    return result


def main():
    args, api = parse_args(), credentials()
    cases = select_cases(args.data, args.per_label)
    pool = [record for case in cases for record in case["evidence"]]
    jobs = [(case, condition) for case in cases for condition in CONDITIONS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(lambda job: run_one(api, args.model, *job, pool), jobs))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    (args.output / "summary.json").write_text(json.dumps(summarize(rows), indent=2) + "\n")


if __name__ == "__main__":
    main()
