#!/usr/bin/env python3
import argparse
import asyncio
import json
from argparse import Namespace
from pathlib import Path

from evaluation import harness
from evaluation.qa_eval_metrics import eval_from_spec


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--trajectory-id", required=True)
    parser.add_argument("--state-index", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--contains", default="")
    return parser.parse_args()


def find_jsonl(path, key, value):
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row[key] == value:
            return row
    raise KeyError(value)


def reader_args(args):
    return Namespace(
        model=args.model, base_url=args.base_url, timeout_seconds=180,
        max_completion_tokens=300, reasoning_effort=None, temperature=0.0,
        top_p=1.0, presence_penalty=None, top_k=None,
        repetition_penalty=None, reader_enable_thinking=False,
    )


async def generate(args, messages):
    client = harness.create_async_client(args.base_url, "OPENAI_API_KEY", None)
    try:
        return await harness.call_reader_model_async(client, reader_args(args), messages)
    finally:
        await client.close()


def selected_text(state, contains):
    text = state["accessibility_tree"]
    if not contains:
        return text
    return "\n".join(line for line in text.splitlines() if contains.lower() in line.lower())


def build_messages(question, text):
    context = [{"type": "text", "value": text}]
    messages, _ = harness.build_messages(
        system_prompt=harness.get_system_prompt(question["domain"]),
        question_text=question["question"], image_path=None, memory_context=context,
    )
    return messages


def score(question, response):
    parsed = harness.extract_boxed_answer(response)
    value = eval_from_spec(question["eval_function"], parsed, question["answer"])
    return parsed, harness.score_to_bool(value)


def main():
    args = parse_args()
    question = find_jsonl(args.data / "questions.jsonl", "id", args.question_id)
    trajectory = find_jsonl(args.data / "trajectories.jsonl", "id", args.trajectory_id)
    state = next(row for row in trajectory["states"] if row["state_index"] == args.state_index)
    text = selected_text(state, args.contains)
    response, usage = asyncio.run(generate(args, build_messages(question, text)))
    parsed, correct = score(question, response)
    result = {"question_id": args.question_id, "trajectory_id": args.trajectory_id, "state_index": args.state_index, "selector": args.contains or "full_state", "evidence_chars": len(text), "response": response, "parsed": parsed, "correct": correct, "usage": usage}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
