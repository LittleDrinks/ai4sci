from __future__ import annotations

import time

from server.cli import default_world
from server.workflows import default_engine


def main() -> None:
    world = default_world()
    while True:
        workflow = world.claim_workflow()
        if workflow:
            execute(world, workflow)
        else:
            time.sleep(1)


def execute(world, workflow) -> None:
    try:
        default_engine(world).run(workflow["id"])
    except Exception as error:
        world.record_workflow_event(workflow["id"], "control", "workflow_failed", {"error": str(error)})
        world.update_workflow(workflow["id"], "failed", "failed", {"error": str(error)})


if __name__ == "__main__":
    main()
