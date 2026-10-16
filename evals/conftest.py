import inspect


def pytest_pycollect_makeitem(collector: object, name: str, obj: object) -> list[object] | None:
    module = getattr(collector, "obj", None)
    if getattr(module, "__test__", True) is False:
        return []
    if inspect.isfunction(obj):
        if obj.__module__ != getattr(module, "__name__", None):
            return []
    elif callable(obj) and not inspect.isclass(obj):
        return []
    return None
