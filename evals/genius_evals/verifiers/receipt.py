"""Verify quantity handling using held-out examples."""

import runpy
from collections.abc import Callable


def verify() -> bool:
    total: Callable[[list[tuple[float, int]]], float] = runpy.run_path("receipt.py")["total"]
    examples: list[tuple[list[tuple[float, int]], float]] = [
        ([], 0),
        ([(3, 4)], 12),
        ([(3, 0)], 0),
        ([(2, 3), (4, 2)], 14),
        ([(1.5, 2)], 3),
    ]
    return all(total(items) == expected for items, expected in examples)
