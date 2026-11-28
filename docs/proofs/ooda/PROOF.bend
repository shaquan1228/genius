import Base
import ../logic.bend as Logic
import ../types.bend as T
import ./main.bend as Loop
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws
import ./trace.bend as Trace

def phase_agrees(+phase: T.Phase)
  -> Logic.SubjectAgrees(T.Phase, Loop.is_recorded_observation, Spec.RecordedObservation, phase):
  match phase:
    case T.Observed{_, T.Returned{_}}: (_ => Unit{}, _ => {==})
    case T.Observed{_, T.NoResponse{}}: Logic.false_agrees_with_empty()
    case T.Oriented{}: Logic.false_agrees_with_empty()
    case T.Decided{}: Logic.false_agrees_with_empty()
    case T.Acted{}: Logic.false_agrees_with_empty()

def required_from_spec(+a: Bool, +b: Bool, witness: Either<&2, &2, {a == True{} : Bool}, {b == True{} : Bool}>)
  -> {Bool.or(a, b) == True{} : Bool}:
  match a:
    case True{}:
      {==}
    case False{}:
      match witness:
        case Inl{equal}:
          Empty.absurd({b == True{} : Bool}, Logic.false_is_not_true(equal))
        case Inr{equal}:
          equal

def required_gate_agrees(+required: Bool, -observed: Bool, -Expected: Type,
  proof: {required == True{} : Bool}, agreement: Logic.Agreement(observed, Expected))
  -> Logic.Agreement(Loop.allow_act(required, _ => observed), Expected):
  %Equal.sym(Bool, required, True{}, proof) : Logic.Agreement(Loop.allow_act(_, _ => observed), Expected)
  agreement

def gate_agrees(+viable_approaches: Nat, +uncertain: Bool, +attempt: T.Attempt, +history: T.History<T.TraceEvent>,
  nontrivial: T.NonTrivial(viable_approaches, uncertain))
  -> Logic.Agreement(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history), Spec.ObservedFirst(attempt, history)):
  +multiple = Nat.is_lt(1n, viable_approaches)
  required = required_from_spec(multiple, uncertain, nontrivial)
  first = Trace.first_agrees(~Loop.is_recorded_observation, ~Spec.RecordedObservation, ~phase_agrees, attempt,
    T.oldest_first(T.TraceEvent, history))
  required_gate_agrees(Bool.or(multiple, uncertain), Loop.observed_first(attempt, history),
    Spec.ObservedFirst(attempt, history), required, first)

def Laws.gns001_observation_precedence(viable_approaches, uncertain, attempt, history, nontrivial, allowed):
  agreement = gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial)
  Logic.agreement_sound(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), agreement, allowed)

def Laws.gns001_observation_gate_complete(viable_approaches, uncertain, attempt, history, nontrivial, observed):
  agreement = gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial)
  Logic.agreement_complete(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), agreement, observed)
