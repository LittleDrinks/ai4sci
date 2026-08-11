from __future__ import annotations

import argparse
import signal
import threading

from researchharness import __version__ as harness_version

from .api import ControlPlane
from .config import Settings, load_settings
from .maintenance import execute_maintenance
from .runtime import process_task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local ResearchHarness worker.")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--name", default="Local ResearchHarness")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    return parser.parse_args()


def install_signal_handlers(stop: threading.Event) -> None:
    def request_stop(_signum, _frame) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)


def claim_loop(
    api: ControlPlane, settings: Settings, runtime_id: str, interval: float, stop: threading.Event
) -> None:
    while not stop.is_set():
        api.heartbeat(runtime_id)
        run_maintenance(api, settings, runtime_id)
        task = api.claim(runtime_id)
        if task:
            process_task(api, settings, task)
        else:
            stop.wait(interval)


def run_maintenance(api: ControlPlane, settings: Settings, runtime_id: str) -> None:
    command = api.claim_maintenance(runtime_id)
    if command:
        execute_maintenance(api, settings, command)


def main() -> None:
    args = parse_args()
    settings = load_settings()
    stop = threading.Event()
    install_signal_handlers(stop)
    api = ControlPlane(args.server)
    runtime_id = api.register(args.name, harness_version)
    try:
        claim_loop(api, settings, runtime_id, args.poll_interval, stop)
    finally:
        api.heartbeat(runtime_id, "offline")
        api.close()


if __name__ == "__main__":
    main()
