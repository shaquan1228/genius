import Base
import ../types.bend as T

def NonTrivial(viable_approaches: Nat, uncertain: Bool) -> Type:
  Or(
    {Cmp.is_lt(Nat.cmp(1n, viable_approaches)) == True{} : Bool},
    {uncertain == True{} : Bool}
  )

def same_attempt(a: T.Attempt, b: T.Attempt) -> Bool:
  match a b:
    case T.AttemptKey{action, number} T.AttemptKey{other_action, other_number}:
      Bool.and(
        Cmp.is_eq(Nat.cmp(action, other_action)),
        Cmp.is_eq(Nat.cmp(number, other_number))
      )

def RecordedObservation(phase: T.Phase) -> Type:
  match phase:
    case T.Observed{facts, signals, constraints}:
      Or({String.is_empty(facts) == False{} : Bool},
        Or({String.is_empty(signals) == False{} : Bool},
          {String.is_empty(constraints) == False{} : Bool}))
    case other:
      Empty

def FirstMatchingEvent(matches: Bool, phase: T.Phase, later: Type) -> Type:
  match matches:
    case True{}:
      RecordedObservation(phase)
    case False{}:
      later

def ObservedFirst(+attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Type:
  match history:
    case Nil{}:
      Empty
    case T.Entry{key, phase} <> tail:
      FirstMatchingEvent(same_attempt(attempt, key), phase, ObservedFirst(attempt, tail))
