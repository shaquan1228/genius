def total(items):
    """Sum (price, quantity) pairs."""
    return sum(price for price, quantity in items)
