import Base
import ../types.bend as T
import ./trace.bend as Trace

def has_observation(facts_empty: Bool, signals_empty: Bool, constraints_empty: Bool) -> Bool:
  Bool.not(Bool.and(facts_empty, Bool.and(signals_empty, constraints_empty)))

def is_recorded_observation(phase: T.Phase) -> Bool:
  match phase:
    case T.Observed{facts, signals, constraints}:
      has_observation(String.is_empty(facts), String.is_empty(signals), String.is_empty(constraints))
    case other:
      False{}

def observed_first(attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Bool:
  Trace.check_phase(is_recorded_observation, Trace.first_phase(attempt, history))

def allow_act(observation_required: Bool, observed: Unit -> Bool) -> Bool:
  match observation_required:
    case True{}:
      observed(Unit{})
    case False{}:
      True{}

def observation_allows_act(viable_approaches: Nat, uncertain: Bool, attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Bool:
  required = Bool.or(Nat.is_lt(1n, viable_approaches), uncertain)
  allow_act(required, _ => observed_first(attempt, history))

def main() -> Bool:
  +attempt: T.Attempt = T.AttemptKey{1n, 1n}
  history: List<&2, T.TraceEvent> = T.Entry{attempt, T.Observed{"The input has two viable approaches", "", ""}} <> Nil{}
  observation_allows_act(2n, False{}, attempt, history)
