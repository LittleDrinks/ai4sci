from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from . import repository as repo
from .models import Command, TaskCompletion


JOB_KINDS = {"plan", "research", "html_report"}


def dispatch(command: Command) -> dict[str, Any]:
    handlers: dict[str, Callable[[dict, dict], dict]] = {
        "create_project": create_project, "submit_node": submit_node,
        "review_node": review_node, "create_agent": create_agent,
        "enqueue_job": enqueue_job, "review_artifact": review_artifact,
        "retry_job": retry_job, "invalidate_node": invalidate_node,
    }
    if command.type not in handlers:
        raise HTTPException(400, f"unknown command: {command.type}")
    return handlers[command.type](command.payload, command.actor.model_dump())


def create_project(payload: dict, actor: dict) -> dict:
    require(payload, "title", "question")
    return repo.create_project(str(payload["title"]), str(payload["question"]), actor)


def submit_node(payload: dict, actor: dict) -> dict:
    require(payload, "project_id", "kind", "title")
    value = normalize_node(payload)
    if value["kind"] == "question":
        raise HTTPException(400, "question nodes are created with projects")
    if not repo.project(value["project_id"]):
        raise HTTPException(404, "unknown project")
    if not repo.dependencies_ready(value["project_id"], value["dependencies"]):
        raise HTTPException(409, "dependencies must be admitted nodes")
    return repo.insert_node(value, actor)


def normalize_node(payload: dict) -> dict:
    return {"project_id": str(payload["project_id"]), "kind": str(payload["kind"]),
            "title": str(payload["title"]), "summary": str(payload.get("summary", "")),
            "content": payload.get("content", {}), "dependencies": sorted(set(payload.get("dependencies", []))),
            "source_job_id": payload.get("source_job_id")}


def review_node(payload: dict, actor: dict) -> dict:
    require(payload, "node_id", "decision")
    value = repo.node(str(payload["node_id"]))
    if not value:
        raise HTTPException(404, "unknown node")
    choice, feedback = review_input(payload)
    return repo.review_node(value["id"], choice, feedback, actor)


def create_agent(payload: dict, actor: dict) -> dict:
    require(payload, "name", "runtime_id", "model")
    runtime = repo.runtime(str(payload["runtime_id"]))
    if not runtime:
        raise HTTPException(404, "unknown runtime")
    capabilities = list(payload.get("capabilities", ["research"]))
    if not set(capabilities).issubset(runtime["capabilities"]):
        raise HTTPException(409, "agent capabilities must be provided by its runtime")
    value = {"name": str(payload["name"]), "runtime_id": runtime["id"],
             "model": str(payload["model"]), "instructions": str(payload.get("instructions", "")),
             "capabilities": capabilities}
    return repo.create_agent(value, actor)


def enqueue_job(payload: dict, actor: dict) -> dict:
    require(payload, "project_id", "agent_id", "kind", "subject_id", "prompt")
    if payload["kind"] not in JOB_KINDS:
        raise HTTPException(400, "unsupported job kind")
    agent = repo.agent(str(payload["agent_id"]))
    if not agent:
        raise HTTPException(404, "unknown agent")
    validate_job_target(payload, agent)
    value = {"project_id": str(payload["project_id"]), "agent_id": agent["id"],
             "kind": str(payload["kind"]), "subject_id": str(payload["subject_id"]),
             "prompt": str(payload["prompt"])}
    return repo.create_job(value, actor)


def validate_job_target(payload: dict, agent: dict) -> None:
    subject = repo.node(str(payload["subject_id"]))
    if not subject or subject["project_id"] != str(payload["project_id"]):
        raise HTTPException(404, "unknown subject")
    if subject["status"] != "admitted" or subject["audit"] != "approve":
        raise HTTPException(409, "subject must be an admitted node")
    runtime = repo.runtime(agent["runtime_id"])
    if payload["kind"] not in agent["capabilities"] or payload["kind"] not in runtime["capabilities"]:
        raise HTTPException(409, "agent runtime cannot execute this job kind")


def review_artifact(payload: dict, actor: dict) -> dict:
    require(payload, "artifact_id", "decision")
    if not repo.artifact(str(payload["artifact_id"])):
        raise HTTPException(404, "unknown artifact")
    choice, feedback = review_input(payload)
    return repo.review_artifact(str(payload["artifact_id"]), choice, feedback, actor)


def retry_job(payload: dict, actor: dict) -> dict:
    require(payload, "job_id")
    return repo.retry_job(str(payload["job_id"]), actor)


def invalidate_node(payload: dict, actor: dict) -> dict:
    require(payload, "node_id", "reason")
    return repo.invalidate_node(str(payload["node_id"]), str(payload["reason"]), actor)


def complete_task(job_id: str, completion: TaskCompletion) -> dict:
    current = repo.job(job_id)
    if not current:
        raise HTTPException(404, "unknown job")
    validate_completion_html(current["kind"], completion.html)
    if current["kind"] == "audit":
        return complete_audit(current, completion)
    if completion.audit:
        raise HTTPException(400, "audit results are only valid for audit jobs")
    candidate = completion_candidate(current, completion.submission)
    expected = repo.SUBMISSION_KINDS.get(current["kind"])
    if expected and candidate["kind"] != expected:
        raise HTTPException(409, f"{current['kind']} jobs require kind={expected} submissions")
    return repo.complete_task(job_id, completion.runtime_id, completion.attempt_id,
                              completion.result_text, candidate, completion.html)


def complete_audit(current: dict, completion: TaskCompletion) -> dict:
    if not completion.audit or completion.submission:
        raise HTTPException(400, "audit completion requires only an audit result")
    audit = completion.audit.model_dump()
    return repo.complete_audit_task(current["id"], completion.runtime_id,
                                    completion.attempt_id, audit)


def validate_completion_html(kind: str, html: str | None) -> None:
    if kind == "html_report" and (html is None or not html.strip()):
        raise HTTPException(400, "html_report completion requires non-empty html")
    if kind != "html_report" and html is not None:
        raise HTTPException(400, f"{kind} completion does not accept html")


def completion_candidate(job: dict, submission: dict | None) -> dict:
    if not submission:
        raise HTTPException(400, "submission is required")
    value = normalize_node({**submission, "project_id": job["project_id"], "source_job_id": job["id"]})
    if not value["dependencies"] and job.get("subject_id"):
        value["dependencies"] = [job["subject_id"]]
    return value


def review_input(payload: dict) -> tuple[str, str]:
    choice = str(payload["decision"])
    if choice not in {"approve", "reject", "revise", "restart"}:
        raise HTTPException(400, "decision must be approve, reject, revise, or restart")
    feedback = str(payload.get("feedback", "")).strip()
    if choice != "approve" and not feedback:
        raise HTTPException(400, "feedback is required")
    return choice, feedback


def require(payload: dict, *keys: str) -> None:
    missing = [key for key in keys if payload.get(key) in (None, "")]
    if missing:
        raise HTTPException(400, f"missing fields: {', '.join(missing)}")
