import Base
import ../types.bend as T
import ./trace.bend as Trace

def is_recorded_observation(phase: T.Phase) -> Bool:
  match phase:
    case T.Observed{source, response}: T.received(source, response)
    case _: False{}

def observed_first(attempt: T.Attempt, history: T.History<T.TraceEvent>) -> Bool:
  Trace.check_phase(is_recorded_observation, Trace.first_phase(attempt, T.oldest_first(T.TraceEvent, history)))

def allow_act(observation_required: Bool, observed: Unit -> Bool) -> Bool:
  match observation_required:
    case True{}:
      observed(Unit{})
    case False{}:
      True{}

def observation_allows_act(viable_approaches: Nat, uncertain: Bool, attempt: T.Attempt, history: T.History<T.TraceEvent>) -> Bool:
  required = Bool.or(Nat.is_lt(1n, viable_approaches), uncertain)
  allow_act(required, _ => observed_first(attempt, history))

def main() -> Bool:
  +attempt: T.Attempt = T.AttemptKey{1n, 1n}
  source: T.Source = T.ParserCase{"parser-v1", "[1,]"}
  event: T.TraceEvent = T.Entry{attempt, T.Observed{source, T.Returned{T.Rejected{}}}}
  history: T.History<T.TraceEvent> = T.Record{event, T.Start{}}
  observation_allows_act(2n, False{}, attempt, history)
