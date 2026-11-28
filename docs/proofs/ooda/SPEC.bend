import Base
import ../types.bend as T
import ./trace.bend as Trace

def RecordedObservation(phase: T.Phase) -> Type:
  match phase:
    case T.Observed{_, T.Returned{_}}: Unit
    case _: Empty

def ObservedFirst(attempt: T.Attempt, history: T.History<T.TraceEvent>) -> Type:
  Trace.AtFirst(~RecordedObservation, attempt, T.oldest_first(T.TraceEvent, history))
