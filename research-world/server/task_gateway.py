from __future__ import annotations

from pathlib import Path

from researchharness import tool as harness_tool

from .runner import EnvironmentBuilder, ExperimentRunner


class TaskGateway:
    def __init__(self, world, attempt_id: str, controller):
        self.world = world
        self.attempt = world.attempt(attempt_id)
        self.controller = controller
        self.submitted = {}

    def harness_tools(self) -> list:
        return [graph_search_tool(self), artifact_read_tool(self), artifact_add_tool(self),
                environment_build_tool(self), experiment_run_tool(self), submit_package_tool(self)]

    def graph_search(self, query: str) -> list[dict]:
        project = self.world.attempt_project(self.attempt["id"])
        return self.world.search(project["id"], query)

    def artifact_read(self, artifact_id: str) -> str:
        self.world.require_artifact_access(self.attempt["id"], artifact_id)
        return self.world.artifacts.read(artifact_id).decode()

    def artifact_add(self, content: str, media_type: str) -> dict:
        artifact = self.world.add_artifact(content.encode(), media_type)
        self.world.grant_artifact(self.attempt["id"], artifact["id"], "agent_output")
        return artifact

    def environment_build(self, setup: list[str]) -> dict:
        project = self.world.attempt_project(self.attempt["id"])
        return EnvironmentBuilder(self.world, self.controller).build(project["id"], self.attempt["id"], setup)

    def experiment_run(self, environment_id: str, command: list[str], files: dict[str, str], seed: int) -> dict:
        project = self.world.attempt_project(self.attempt["id"])
        environment = self.world.environment(environment_id)
        if environment["attempt_id"] != self.attempt["id"]:
            raise PermissionError("environment is outside the task capability")
        inputs = {name: content.encode() for name, content in files.items()}
        return ExperimentRunner(self.world, self.controller).run(project["id"], self.attempt["id"], environment, command, inputs, seed)

    def submit(self, payload: dict) -> dict:
        payload["generation_id"] = self.attempt["generation_id"]
        key = str(payload)
        if key not in self.submitted:
            self.submitted[key] = self.world.submit_task_package(self.attempt["id"], payload)
        return self.submitted[key]


def graph_search_tool(gateway: TaskGateway):
    @harness_tool(name="search_admitted_graph", description="Search admitted research graph nodes for this project.")
    def search_admitted_graph(query: str) -> list[dict]:
        return gateway.graph_search(query)
    return search_admitted_graph


def artifact_read_tool(gateway: TaskGateway):
    @harness_tool(name="read_task_artifact", description="Read an artifact granted to this task capability.")
    def read_task_artifact(artifact_id: str) -> str:
        return gateway.artifact_read(artifact_id)
    return read_task_artifact


def artifact_add_tool(gateway: TaskGateway):
    @harness_tool(name="add_task_artifact", description="Add a text artifact owned by this task.")
    def add_task_artifact(content: str, media_type: str) -> dict:
        return gateway.artifact_add(content, media_type)
    return add_task_artifact


def environment_build_tool(gateway: TaskGateway):
    @harness_tool(name="build_task_environment", description="Build and lock a project execution environment.")
    def build_task_environment(setup: list[str]) -> dict:
        return gateway.environment_build(setup)
    return build_task_environment


def experiment_run_tool(gateway: TaskGateway):
    @harness_tool(name="run_task_experiment", description="Run and replay an offline isolated experiment.")
    def run_task_experiment(environment_id: str, command: list[str], files: dict[str, str], seed: int = 0) -> dict:
        return gateway.experiment_run(environment_id, command, files, seed)
    return run_task_experiment


def submit_package_tool(gateway: TaskGateway):
    @harness_tool(name="submit_research_package", description="Submit this generation's complete research package.")
    def submit_research_package(payload: dict) -> dict:
        return gateway.submit(payload)
    return submit_research_package
