FALLBACK_TIMEOUT = 30


def timeout(value=None):
    if value is None:
        return FALLBACK_TIMEOUT
    if value <= 0:
        raise ValueError("timeout must be positive")
    return value
