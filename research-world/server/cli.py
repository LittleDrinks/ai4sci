from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

from .importer import import_to_server


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="research-world")
    commands = root.add_subparsers(dest="command", required=True)
    add_serve_command(commands)
    add_create_command(commands)
    add_submit_command(commands)
    add_snapshot_command(commands)
    add_manifest_command(commands)
    return root


def add_serve_command(commands) -> None:
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8095, type=int)


def add_create_command(commands) -> None:
    create = commands.add_parser("create-project")
    create.add_argument("--server", default="http://127.0.0.1:8095")
    create.add_argument("--title", required=True)
    create.add_argument("--question", required=True)
    create.add_argument("--actor", default="cli-user")


def add_submit_command(commands) -> None:
    submit = commands.add_parser("submit-node")
    add_submit_args(submit)


def add_snapshot_command(commands) -> None:
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--server", default="http://127.0.0.1:8095")
    snapshot.add_argument("--project")


def add_manifest_command(commands) -> None:
    manifest = commands.add_parser("import-manifest")
    manifest.add_argument("manifest", type=Path)
    manifest.add_argument("--server", default="http://127.0.0.1:8095")
    manifest.add_argument("--project")
    manifest.add_argument("--actor", default="cli-importer")


def add_submit_args(value: argparse.ArgumentParser) -> None:
    value.add_argument("--server", default="http://127.0.0.1:8095")
    value.add_argument("--project", required=True)
    value.add_argument("--kind", default="claim")
    value.add_argument("--title", required=True)
    value.add_argument("--summary", default="")
    value.add_argument("--content", default="{}")
    value.add_argument("--dependency", action="append", default=[])
    value.add_argument("--actor", default="cli-user")


def main() -> None:
    args = parser().parse_args()
    if args.command == "serve":
        serve(args)
    elif args.command == "create-project":
        create_project(args)
    elif args.command == "submit-node":
        submit_node(args)
    elif args.command == "import-manifest":
        import_nodes(args)
    else:
        snapshot(args)


def serve(args) -> None:
    import uvicorn
    uvicorn.run("server.app:app", host=args.host, port=args.port, reload=False)


def create_project(args) -> None:
    payload = {"title": args.title, "question": args.question}
    command = {"type": "create_project", "actor": {"kind": "human", "id": args.actor}, "payload": payload}
    response = httpx.post(f"{args.server}/api/commands", json=command, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def submit_node(args) -> None:
    payload = {"project_id": args.project, "kind": args.kind, "title": args.title,
               "summary": args.summary, "content": json.loads(args.content), "dependencies": args.dependency}
    command = {"type": "submit_node", "actor": {"kind": "human", "id": args.actor}, "payload": payload}
    response = httpx.post(f"{args.server}/api/commands", json=command, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def import_nodes(args) -> None:
    result = import_to_server(args.manifest, args.server, args.project, args.actor)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def snapshot(args) -> None:
    response = httpx.get(f"{args.server}/api/bootstrap", params={"project_id": args.project}, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
