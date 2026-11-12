import runpy

config = runpy.run_path("config.py")
client = runpy.run_path("client.py")
assert client["timeout"]() == config["timeout_seconds"]
assert client["timeout"](5) == 5
try:
    client["timeout"](0)
except ValueError:
    pass
else:
    raise AssertionError("nonpositive timeout accepted")
