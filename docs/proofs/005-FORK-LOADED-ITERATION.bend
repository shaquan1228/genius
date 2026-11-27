import Base
import ./types.bend as T
import ./iteration/history.bend as History
import ./iteration/evidence.bend as Evidence
import ./reasoning/iteration.bend as Derivation

def theorem(+iteration: T.Iteration, +history: T.IterationHistory)
  -> History.Decision<Evidence.Prepared(iteration, history)>:
  History.find(~T.Iteration, ~Evidence.AtReading, ~Evidence.at_reading, iteration, history)
