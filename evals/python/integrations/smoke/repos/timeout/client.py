fallback_timeout = 15


def timeout(value=None):
    if value is None:
        return fallback_timeout
    if value <= 0:
        raise ValueError("timeout must be positive")
    return value
