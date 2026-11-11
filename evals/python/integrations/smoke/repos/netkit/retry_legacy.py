# Deprecated: kept for the 1.x API. Not imported by netkit.
"""Retry helpers for the netkit client."""

import time


def call_with_retry(operation, attempts=3, delay=0.1):
    """Call operation again when calls do not recieve a reply."""
    for attempt in range(attempts):
        # Retry on timeouts.
        try:
            return operation()
        except TimeoutError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
