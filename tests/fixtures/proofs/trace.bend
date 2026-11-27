import Base
import ../../../docs/proofs/types.bend as T
import ../../../docs/proofs/logic.bend as Logic
import ../../../docs/proofs/ooda/trace.bend as Trace
import ../../../docs/proofs/ooda/main.bend as Loop

def target() -> T.Attempt:
  T.AttemptKey{7n, 2n}

def history() -> List<&2, T.TraceEvent>:
  T.Entry{T.AttemptKey{7n, 1n}, T.Observed{"earlier attempt", "", ""}} <>
  T.Entry{T.AttemptKey{8n, 2n}, T.Observed{"different action", "", ""}} <>
  T.Entry{target(), T.Decided{}} <>
  T.Entry{target(), T.Observed{"too late", "", ""}} <> Nil{}

def first_phase_uses_both_parts_of_the_key()
  -> {Trace.first_phase(target(), history()) == Some{T.Decided{}} : Maybe<&2, T.Phase>}:
  {==}

def a_later_observation_cannot_justify_the_decision()
  -> {Loop.observed_first(target(), history()) == False{} : Bool}:
  {==}

def missing_attempt_has_no_phase()
  -> {Trace.first_phase(T.AttemptKey{8n, 1n}, history()) == None{} : Maybe<&2, T.Phase>}:
  {==}

# A different phase rule accepts any entry. Its proof reuses the same scan.
def any_phase_agrees(+phase: T.Phase) -> Logic.Agreement(True{}, Unit):
  Logic.Equivalence{_ => Unit{}, _ => {==}}

def any_event_agrees(+attempt: T.Attempt, +events: List<&2, T.TraceEvent>)
  -> Logic.Agreement(Trace.check_phase(_ => True{}, Trace.first_phase(attempt, events)),
    Trace.AtFirst(~(_ => Unit), attempt, events)):
  Trace.first_agrees(~(_ => True{}), ~(_ => Unit), ~any_phase_agrees, attempt, events)
