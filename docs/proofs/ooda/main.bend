import Base

type Attempt is Data:
  AttemptKey{action: Nat, number: Nat}

type Phase is Data:
  Observed{facts: String, signals: String, constraints: String}
  Oriented{}
  Decided{}
  Acted{}

type TraceEvent is Data:
  Entry{key: Attempt, phase: Phase}

def same_attempt(a: Attempt, b: Attempt) -> Bool:
  match a b:
    case AttemptKey{action, number} AttemptKey{other_action, other_number}:
      Bool.and(Nat.is_eq(action, other_action), Nat.is_eq(number, other_number))

def has_observation(facts_empty: Bool, signals_empty: Bool, constraints_empty: Bool) -> Bool:
  Bool.not(Bool.and(facts_empty, Bool.and(signals_empty, constraints_empty)))

def is_recorded_observation(phase: Phase) -> Bool:
  match phase:
    case Observed{facts, signals, constraints}:
      has_observation(String.is_empty(facts), String.is_empty(signals), String.is_empty(constraints))
    case other:
      False{}

def check_first_match(matches: Bool, phase: Phase, later: Unit -> Bool) -> Bool:
  match matches:
    case True{}:
      is_recorded_observation(phase)
    case False{}:
      later(Unit{})

def observed_first(+attempt: Attempt, history: List<&2, TraceEvent>) -> Bool:
  match history:
    case Nil{}:
      False{}
    case Entry{key, phase} <> tail:
      check_first_match(same_attempt(attempt, key), phase, _ => observed_first(attempt, tail))

def allow_act(observation_required: Bool, observed: Unit -> Bool) -> Bool:
  match observation_required:
    case True{}:
      observed(Unit{})
    case False{}:
      True{}

def observation_allows_act(viable_approaches: Nat, uncertain: Bool, attempt: Attempt, history: List<&2, TraceEvent>) -> Bool:
  required = Bool.or(Nat.is_lt(1n, viable_approaches), uncertain)
  allow_act(required, _ => observed_first(attempt, history))

def main() -> Bool:
  +attempt: Attempt = AttemptKey{1n, 1n}
  history: List<&2, TraceEvent> = Entry{attempt, Observed{"The input has two viable approaches", "", ""}} <> Nil{}
  observation_allows_act(2n, False{}, attempt, history)
