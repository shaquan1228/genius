import Base
import ./main.bend as Loop

def NonTrivial(viable_approaches: Nat, uncertain: Bool) -> Type:
  Or(
    {Cmp.is_lt(Nat.cmp(1n, viable_approaches)) == True{} : Bool},
    {uncertain == True{} : Bool}
  )

def same_attempt(a: Loop.Attempt, b: Loop.Attempt) -> Bool:
  match a b:
    case Loop.AttemptKey{action, number} Loop.AttemptKey{other_action, other_number}:
      Bool.and(
        Cmp.is_eq(Nat.cmp(action, other_action)),
        Cmp.is_eq(Nat.cmp(number, other_number))
      )

def RecordedObservation(phase: Loop.Phase) -> Type:
  match phase:
    case Loop.Observed{facts, signals, constraints}:
      Or({String.is_empty(facts) == False{} : Bool},
        Or({String.is_empty(signals) == False{} : Bool},
          {String.is_empty(constraints) == False{} : Bool}))
    case other:
      Empty

def FirstMatchingEvent(matches: Bool, phase: Loop.Phase, later: Type) -> Type:
  match matches:
    case True{}:
      RecordedObservation(phase)
    case False{}:
      later

def ObservedFirst(+attempt: Loop.Attempt, history: List<&2, Loop.TraceEvent>) -> Type:
  match history:
    case Nil{}:
      Empty
    case Loop.Entry{key, phase} <> tail:
      FirstMatchingEvent(same_attempt(attempt, key), phase, ObservedFirst(attempt, tail))
