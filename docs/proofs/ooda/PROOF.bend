import Base
import ../logic.bend as Logic
import ../types.bend as T
import ./main.bend as Loop
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws
import ./trace.bend as Trace

# With all three fields empty, any proposed witness would equate True and False.
def empty_field_witness(observed: Spec.NonemptyEvidence(True{}, True{}, True{})) -> {True{} == False{} : Bool}:
  match observed:
    case Inl{fact}: fact
    case Inr{Inl{signal}}: signal
    case Inr{Inr{constraint}}: constraint

def has_observation_agrees(+facts_empty: Bool, +signals_empty: Bool, +constraints_empty: Bool)
  -> Logic.Agreement(Loop.has_observation(facts_empty, signals_empty, constraints_empty),
    Spec.NonemptyEvidence(facts_empty, signals_empty, constraints_empty)):
  match facts_empty signals_empty constraints_empty:
    case False{} _ _:
      Logic.Equivalence{_ => Inl{{==}}, _ => {==}}
    case True{} False{} _:
      Logic.Equivalence{_ => Inr{Inl{{==}}}, _ => {==}}
    case True{} True{} False{}:
      Logic.Equivalence{_ => Inr{Inr{{==}}}, _ => {==}}
    case True{} True{} True{}:
      Logic.Equivalence{
        allowed => Empty.absurd(Spec.NonemptyEvidence(True{}, True{}, True{}), Logic.false_is_not_true(allowed)),
        observed => Equal.sym(Bool, True{}, False{}, empty_field_witness(observed))
      }

def phase_agrees(+phase: T.Phase)
  -> Logic.SubjectAgrees(T.Phase, Loop.is_recorded_observation, Spec.RecordedObservation, phase):
  match phase:
    case T.Observed{facts, signals, constraints}:
      has_observation_agrees(String.is_empty(facts), String.is_empty(signals), String.is_empty(constraints))
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

def gate_agrees(+viable_approaches: Nat, +uncertain: Bool, +attempt: T.Attempt, +history: List<&2, T.TraceEvent>,
  nontrivial: T.NonTrivial(viable_approaches, uncertain))
  -> Logic.Agreement(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history), Spec.ObservedFirst(attempt, history)):
  +multiple = Nat.is_lt(1n, viable_approaches)
  required = required_from_spec(multiple, uncertain, nontrivial)
  first = Trace.first_agrees(~Loop.is_recorded_observation, ~Spec.RecordedObservation, ~phase_agrees, attempt, history)
  required_gate_agrees(Bool.or(multiple, uncertain), Loop.observed_first(attempt, history),
    Spec.ObservedFirst(attempt, history), required, first)

def Laws.gns001_observation_precedence(viable_approaches, uncertain, attempt, history, nontrivial, allowed):
  Logic.agreement_sound(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial))(allowed)

def Laws.gns001_observation_gate_complete(viable_approaches, uncertain, attempt, history, nontrivial, observed):
  Logic.agreement_complete(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial))(observed)
