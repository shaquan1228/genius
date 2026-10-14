"""Verify quantity handling using held-out examples."""

import runpy
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiptItem:
    price: float
    quantity: int


@dataclass(frozen=True)
class ReceiptExample:
    items: list[ReceiptItem]
    expected_total: float


def verify() -> bool:
    total: Callable[[list[tuple[float, int]]], float] = runpy.run_path("receipt.py")["total"]
    examples = [
        ReceiptExample(items=[], expected_total=0),
        ReceiptExample(items=[ReceiptItem(price=3, quantity=4)], expected_total=12),
        ReceiptExample(items=[ReceiptItem(price=3, quantity=0)], expected_total=0),
        ReceiptExample(
            items=[ReceiptItem(price=2, quantity=3), ReceiptItem(price=4, quantity=2)],
            expected_total=14,
        ),
        ReceiptExample(items=[ReceiptItem(price=1.5, quantity=2)], expected_total=3),
    ]
    return all(
        total([(item.price, item.quantity) for item in example.items]) == example.expected_total
        for example in examples
    )
