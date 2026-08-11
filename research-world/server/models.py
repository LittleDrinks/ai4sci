from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Actor(BaseModel):
    kind: str = "human"
    id: str = "local-user"


class Command(BaseModel):
    type: str
    actor: Actor = Field(default_factory=Actor)
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeRegistration(BaseModel):
    name: str
    sdk: str
    version: str
    capabilities: list[str]


class RuntimeHeartbeat(BaseModel):
    status: str = "online"


class TaskClaim(BaseModel):
    runtime_id: str


class TaskEvent(BaseModel):
    runtime_id: str
    attempt_id: str
    kind: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditResult(BaseModel):
    decision: Literal["approve", "revise", "restart"]
    feedback: str
    checks: list[Any] = Field(default_factory=list)


class TaskCompletion(BaseModel):
    runtime_id: str
    attempt_id: str
    result_text: str = ""
    submission: dict[str, Any] | None = None
    html: str | None = None
    audit: AuditResult | None = None


class TaskFailure(BaseModel):
    runtime_id: str
    attempt_id: str
    error: str


class TaskHeartbeat(BaseModel):
    runtime_id: str
    attempt_id: str


class MaintenanceClaim(BaseModel):
    runtime_id: str


class MaintenanceCompletion(BaseModel):
    runtime_id: str
