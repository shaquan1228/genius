import inspect


def pytest_pycollect_makeitem(collector, name, obj):
    module = getattr(collector, "obj", None)
    if inspect.isfunction(obj) and obj.__module__ != getattr(module, "__name__", None):
        return []
