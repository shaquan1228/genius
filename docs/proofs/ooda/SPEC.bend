import Base
import ../types.bend as T
import ./trace.bend as Trace

def NonTrivial(viable_approaches: Nat, uncertain: Bool) -> Type:
  Or(
    {Cmp.is_lt(Nat.cmp(1n, viable_approaches)) == True{} : Bool},
    {uncertain == True{} : Bool}
  )

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
