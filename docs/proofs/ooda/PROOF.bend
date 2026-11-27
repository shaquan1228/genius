import Base
import ../types.bend as T
import ./main.bend as Loop
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws

def IsTrue(flag: Bool) -> Type:
  match flag:
    case True{}:
      Unit
    case False{}:
      Empty

def false_is_not_true(equal: {False{} == True{} : Bool}) -> Empty:
  %Equal.sym(Bool, False{}, True{}, equal) : IsTrue(_)
  Unit{}

def Agreement(+result: Bool, -P: Type) -> Type:
  ({result == True{} : Bool} -> P) & (P -> {result == True{} : Bool})

def agreement_sound(-result: Bool, -P: Type, agreement: Agreement(result, P)) -> {result == True{} : Bool} -> P:
  (sound, complete) = agreement
  sound

def agreement_complete(-result: Bool, -P: Type, agreement: Agreement(result, P)) -> P -> {result == True{} : Bool}:
  (sound, complete) = agreement
  complete

def false_agrees_with_empty() -> Agreement(False{}, Empty):
  (false_is_not_true, impossible => Empty.absurd({False{} == True{} : Bool}, impossible))

def NonemptyEvidence(facts_empty: Bool, signals_empty: Bool, constraints_empty: Bool) -> Type:
  Or({facts_empty == False{} : Bool}, Or({signals_empty == False{} : Bool}, {constraints_empty == False{} : Bool}))

def no_nonempty_evidence(observed: NonemptyEvidence(True{}, True{}, True{})) -> {False{} == True{} : Bool}:
  match observed:
    case Inl{equal}:
      Equal.sym(Bool, True{}, False{}, equal)
    case Inr{Inl{equal}}:
      Equal.sym(Bool, True{}, False{}, equal)
    case Inr{Inr{equal}}:
      Equal.sym(Bool, True{}, False{}, equal)

def has_observation_agrees(+facts_empty: Bool, +signals_empty: Bool, +constraints_empty: Bool)
  -> Agreement(Loop.has_observation(facts_empty, signals_empty, constraints_empty),
    NonemptyEvidence(facts_empty, signals_empty, constraints_empty)):
  match facts_empty signals_empty constraints_empty:
    case False{} s c:
      (_ => Inl{{==}}, _ => {==})
    case True{} False{} c:
      (_ => Inr{Inl{{==}}}, _ => {==})
    case True{} True{} False{}:
      (_ => Inr{Inr{{==}}}, _ => {==})
    case True{} True{} True{}:
      (allowed => Empty.absurd(NonemptyEvidence(True{}, True{}, True{}), false_is_not_true(allowed)),
        observed => no_nonempty_evidence(observed))

def phase_agrees(+phase: T.Phase)
  -> Agreement(Loop.is_recorded_observation(phase), Spec.RecordedObservation(phase)):
  match phase:
    case T.Observed{facts, signals, constraints}:
      has_observation_agrees(String.is_empty(facts), String.is_empty(signals), String.is_empty(constraints))
    case T.Oriented{}:
      false_agrees_with_empty()
    case T.Decided{}:
      false_agrees_with_empty()
    case T.Acted{}:
      false_agrees_with_empty()

def first_match_agrees(+matches: Bool, +phase: T.Phase, -tail_result: Bool, -TailSpec: Type,
  tail_agreement: Unit -> Agreement(tail_result, TailSpec))
  -> Agreement(Loop.check_first_match(matches, phase, _ => tail_result), Spec.FirstMatchingEvent(matches, phase, TailSpec)):
  match matches:
    case True{}:
      phase_agrees(phase)
    case False{}:
      tail_agreement(Unit{})

def same_attempt_agrees(+attempt: T.Attempt, +key: T.Attempt)
  -> {Loop.same_attempt(attempt, key) == Spec.same_attempt(attempt, key) : Bool}:
  match attempt key:
    case T.AttemptKey{action, number} T.AttemptKey{other_action, other_number}:
      {==}

def history_agrees(+attempt: T.Attempt, +history: List<&2, T.TraceEvent>)
  -> Agreement(Loop.observed_first(attempt, history), Spec.ObservedFirst(attempt, history)):
  match history:
    case Nil{}:
      false_agrees_with_empty()
    case T.Entry{key, phase} <> tail:
      %same_attempt_agrees(attempt, key) : Agreement(
        Loop.check_first_match(Loop.same_attempt(attempt, key), phase, _ => Loop.observed_first(attempt, tail)),
        Spec.FirstMatchingEvent(_, phase, Spec.ObservedFirst(attempt, tail)))
      first_match_agrees(Loop.same_attempt(attempt, key), phase, Loop.observed_first(attempt, tail),
        Spec.ObservedFirst(attempt, tail), _ => history_agrees(attempt, tail))

def required_from_spec(+a: Bool, +b: Bool, witness: Or({a == True{} : Bool}, {b == True{} : Bool}))
  -> {Bool.or(a, b) == True{} : Bool}:
  match a:
    case True{}:
      {==}
    case False{}:
      match witness:
        case Inl{equal}:
          Empty.absurd({b == True{} : Bool}, false_is_not_true(equal))
        case Inr{equal}:
          equal

def required_gate_agrees(+required: Bool, -observed: Bool, -Expected: Type,
  proof: {required == True{} : Bool}, agreement: Agreement(observed, Expected))
  -> Agreement(Loop.allow_act(required, _ => observed), Expected):
  %Equal.sym(Bool, required, True{}, proof) : Agreement(Loop.allow_act(_, _ => observed), Expected)
  agreement

def gate_agrees(+viable_approaches: Nat, +uncertain: Bool, +attempt: T.Attempt, +history: List<&2, T.TraceEvent>,
  nontrivial: Spec.NonTrivial(viable_approaches, uncertain))
  -> Agreement(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history), Spec.ObservedFirst(attempt, history)):
  +multiple = Cmp.is_lt(Nat.cmp(1n, viable_approaches))
  required_gate_agrees(Bool.or(multiple, uncertain), Loop.observed_first(attempt, history),
    Spec.ObservedFirst(attempt, history), required_from_spec(multiple, uncertain, nontrivial), history_agrees(attempt, history))

def Laws.gns001_observation_precedence(viable_approaches, uncertain, attempt, history, nontrivial, allowed):
  agreement_sound(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial))(allowed)

def Laws.gns001_observation_gate_complete(viable_approaches, uncertain, attempt, history, nontrivial, observed):
  agreement_complete(Loop.observation_allows_act(viable_approaches, uncertain, attempt, history),
    Spec.ObservedFirst(attempt, history), gate_agrees(viable_approaches, uncertain, attempt, history, nontrivial))(observed)
