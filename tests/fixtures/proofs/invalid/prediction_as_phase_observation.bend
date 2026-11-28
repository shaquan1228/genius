import Base
import ./types.bend as T

def bad(+source: T.Source, prediction: T.Hypothesis<source>) -> T.Phase:
  T.Observed{source, prediction}
