import Base
import ../types.bend as T
import ./trace.bend as Trace

def NonemptyEvidence(facts_empty: Bool, signals_empty: Bool, constraints_empty: Bool) -> Type:
  Or({facts_empty == False{} : Bool}, Or({signals_empty == False{} : Bool}, {constraints_empty == False{} : Bool}))

def RecordedObservation(phase: T.Phase) -> Type:
  match phase:
    case T.Observed{facts, signals, constraints}:
      NonemptyEvidence(String.is_empty(facts), String.is_empty(signals), String.is_empty(constraints))
    case other:
      Empty

def ObservedFirst(attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Type:
  Trace.AtFirst(~RecordedObservation, attempt, history)
