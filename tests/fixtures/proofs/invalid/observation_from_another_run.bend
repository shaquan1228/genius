import Base
import ./types.bend as T

def bad(obs: T.Observation<T.TestSuite{"run-1", ".", "asked.py"}>) -> Bool:
  T.received(T.TestSuite{"run-2", ".", "asked.py"}, obs)
