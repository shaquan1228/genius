"""Verify both defaults, explicit overrides, and invalid input behavior."""

import runpy
from collections.abc import Callable

Timeout = Callable[[int | None], int]


def rejects_zero(timeout: Timeout) -> bool:
    try:
        timeout(0)
    except ValueError:
        return True
    return False


def verify() -> bool:
    config = runpy.run_path("config.py")
    client = runpy.run_path("client.py")
    timeout: Timeout = client["timeout"]
    defaults = (config["TIMEOUT_SECONDS"], client["FALLBACK_TIMEOUT"], timeout(None))
    return defaults == (30, 30, 30) and timeout(5) == 5 and rejects_zero(timeout)
