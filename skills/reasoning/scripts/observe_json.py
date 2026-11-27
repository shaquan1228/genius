"""Observe how the installed standard-library JSON parser handles the literal input."""
import json
import sys


def parse(text):
    try:
        json.loads(text)
    except ValueError:
        # Includes syntax errors and the decoder's integer-length limit.
        return "rejected"
    return "accepted"


try:
    outcome = parse(sys.stdin.buffer.read().decode("utf-8"))
except (UnicodeError, RecursionError, MemoryError, OSError) as error:
    print(f"JSON parser did not produce a result: {error}", file=sys.stderr)
    sys.exit(2)

print(f"{sys.implementation.name} {sys.version.split()[0]} json.loads")
print(outcome)
