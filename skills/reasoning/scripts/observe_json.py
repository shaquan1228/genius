import json
import sys


def parse(text):
    try:
        json.loads(text)
    except ValueError:
        return "rejected"
    return "accepted"


try:
    outcome = parse(sys.stdin.buffer.read().decode("utf-8"))
except (UnicodeError, RecursionError, MemoryError, OSError) as error:
    print(f"JSON parser did not produce a result: {error}", file=sys.stderr)
    sys.exit(2)

print(f"{sys.implementation.name} {sys.version.split()[0]} json.loads")
print(outcome)
