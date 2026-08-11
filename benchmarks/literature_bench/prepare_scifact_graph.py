import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_jsonl(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def evidence_signature(claim):
    text = " ".join(claim["claim"].lower().split())
    evidence = json.dumps(claim["evidence"], sort_keys=True)
    return text, evidence


def graph_documents(train, dev):
    held_out = {evidence_signature(claim) for claim in dev}
    claims_by_doc = defaultdict(set)
    for claim in train:
        if evidence_signature(claim) in held_out:
            continue
        for doc_id in claim["evidence"]:
            claims_by_doc[int(doc_id)].add(claim["claim"])
    return claims_by_doc


def write_corpus(path, claims_by_doc):
    with Path(path).open("w") as stream:
        for doc_id, claims in sorted(claims_by_doc.items()):
            row = {"doc_id": doc_id, "title": " ".join(sorted(claims)), "abstract": []}
            stream.write(json.dumps(row) + "\n")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--dev", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    claims_by_doc = graph_documents(read_jsonl(args.train), read_jsonl(args.dev))
    write_corpus(args.output, claims_by_doc)
    print(json.dumps({"documents": len(claims_by_doc)}))


if __name__ == "__main__":
    main()
