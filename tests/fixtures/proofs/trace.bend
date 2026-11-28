import Base
import ../../../docs/proofs/types.bend as T
import ../../../docs/proofs/logic.bend as Logic
import ../../../docs/proofs/ooda/trace.bend as Trace
import ../../../docs/proofs/ooda/main.bend as Loop

def target() -> T.Attempt:
  T.AttemptKey{7n, 2n}

def parser_returned(actual: T.ParseOutcome) -> T.Phase:
  T.Observed{T.ParserCase{"v1", "[1,]"}, T.Returned{actual}}

def history() -> T.History<T.TraceEvent>:
  previous: T.TraceEvent = T.Entry{T.AttemptKey{7n, 1n}, parser_returned(T.Rejected{})}
  other: T.TraceEvent = T.Entry{T.AttemptKey{8n, 2n}, parser_returned(T.Accepted{})}
  decision: T.TraceEvent = T.Entry{target(), T.Decided{}}
  late_response: T.TraceEvent = T.Entry{target(), parser_returned(T.Rejected{})}
  T.Record{late_response, T.Record{decision, T.Record{other, T.Record{previous, T.Start{}}}}}

def either_parser_answer_counts_as_an_observation(actual: T.ParseOutcome)
  -> {Loop.observed_first(target(), T.Record{T.Entry{target(), parser_returned(actual)}, T.Start{}}) == True{} : Bool}:
  {==}

def a_missing_response_cannot_open_the_observation_gate()
  -> {Loop.observed_first(target(), T.Record{T.Entry{target(), T.Observed{T.ParserCase{"v1", "[1,]"}, T.NoResponse{}}},
    T.Start{}}) == False{} : Bool}:
  {==}

def first_phase_uses_both_parts_of_the_key()
  -> {Trace.first_phase(target(), T.oldest_first(T.TraceEvent, history())) == Some{T.Decided{}} : Maybe<&2, T.Phase>}:
  {==}

def a_later_observation_cannot_justify_the_decision()
  -> {Loop.observed_first(target(), history()) == False{} : Bool}:
  {==}

def missing_attempt_has_no_phase()
  -> {Trace.first_phase(T.AttemptKey{8n, 1n}, T.oldest_first(T.TraceEvent, history())) == None{} : Maybe<&2, T.Phase>}:
  {==}

# A different phase rule accepts any entry. Its proof reuses the same scan.
def any_phase_agrees(+phase: T.Phase) -> Logic.Agreement(True{}, Unit):
  (_ => Unit{}, _ => {==})

def any_event_agrees(+attempt: T.Attempt, +events: List<&2, T.TraceEvent>)
  -> Logic.Agreement(Trace.check_phase(_ => True{}, Trace.first_phase(attempt, events)),
    Trace.AtFirst(~(_ => Unit), attempt, events)):
  Trace.first_agrees(~(_ => True{}), ~(_ => Unit), ~any_phase_agrees, attempt, events)
