from __future__ import annotations

import time

from server.cli import default_world, execute_run


def main() -> None:
    world = default_world()
    while True:
        run = world.claim_run()
        if not run:
            time.sleep(1)
            continue
        try:
            execute_run(world, run)
        except Exception as error:
            world.update_run(run["id"], "failed")
            world.record_event(run["id"], None, None, "worker", "run_failed", {"type": "run", "id": run["id"]}, {"error": str(error)})


if __name__ == "__main__":
    main()
