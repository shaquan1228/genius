import runpy

total = runpy.run_path("receipt.py")["total"]
assert total([]) == 0
assert total([(3.0, 1), (4.0, 1)]) == 7.0
