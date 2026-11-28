import Base
import ../types.bend as T
import ./main.bend as Loop
import ./SPEC.bend as Spec

law gns001_observation_precedence:
  for +viable_approaches: Nat
  for +uncertain: Bool
  for +attempt: T.Attempt
  for +history: T.History<T.TraceEvent>
  for nontrivial: T.NonTrivial(viable_approaches, uncertain)
  for allowed: {
    Loop.observation_allows_act(viable_approaches, uncertain, attempt, history) == True{} : Bool
  }
  Spec.ObservedFirst(attempt, history)

law gns001_observation_gate_complete:
  for +viable_approaches: Nat
  for +uncertain: Bool
  for +attempt: T.Attempt
  for +history: T.History<T.TraceEvent>
  for nontrivial: T.NonTrivial(viable_approaches, uncertain)
  for observed: Spec.ObservedFirst(attempt, history)
  {
    Loop.observation_allows_act(viable_approaches, uncertain, attempt, history) == True{} : Bool
  }
