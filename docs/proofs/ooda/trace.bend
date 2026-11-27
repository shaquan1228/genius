import Base
import ../logic.bend as Logic
import ../types.bend as T

def same_attempt(a: T.Attempt, b: T.Attempt) -> Bool:
  match a b:
    case T.AttemptKey{action, number} T.AttemptKey{other_action, other_number}:
      Bool.and(Nat.is_eq(action, other_action), Nat.is_eq(number, other_number))

def first_phase(+attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Maybe<&2, T.Phase>:
  match history:
    case Nil{}: None{}
    case T.Entry{key, phase} <> tail:
      List.find.if(T.Phase, phase, _ => first_phase(attempt, tail), same_attempt(attempt, key))

def check_phase(check: T.Phase -> Bool, first: Maybe<&2, T.Phase>) -> Bool:
  match first:
    case None{}: False{}
    case Some{phase}: check(phase)

def OnMatch(matches: Bool, here: Type, later: Type) -> Type:
  match matches:
    case True{}: here
    case False{}: later

# The first entry for this attempt must satisfy Claim. An empty history has no witness.
def AtFirst(~Claim: T.Phase -> Type, +attempt: T.Attempt, history: List<&2, T.TraceEvent>) -> Type:
  match history:
    case Nil{}: Empty
    case T.Entry{key, phase} <> tail:
      OnMatch(same_attempt(attempt, key), Claim(phase), AtFirst(~Claim, attempt, tail))

# Bend refines the goal in each branch when it matches on the attempt comparison.
def on_match_agrees(~check: T.Phase -> Bool, ~Claim: T.Phase -> Type,
  +matches: Bool, +phase: T.Phase,
  -rest: Maybe<&2, T.Phase>, -Later: Type,
  here: Unit -> Logic.SubjectAgrees(T.Phase, check, Claim, phase),
  later: Unit -> Logic.Agreement(check_phase(check, rest), Later))
  -> Logic.Agreement(check_phase(check,
    List.find.if(T.Phase, phase, _ => rest, matches)),
    OnMatch(matches, Claim(phase), Later)):
  match matches:
    case True{}: here(Unit{})
    case False{}: later(Unit{})

def first_agrees(~check: T.Phase -> Bool, ~Claim: T.Phase -> Type,
  ~agrees: @+phase: T.Phase -> Logic.SubjectAgrees(T.Phase, check, Claim, phase),
  +attempt: T.Attempt, +history: List<&2, T.TraceEvent>)
  -> Logic.Agreement(check_phase(check, first_phase(attempt, history)), AtFirst(~Claim, attempt, history)):
  match history:
    case Nil{}: Logic.false_agrees_with_empty()
    case T.Entry{key, phase} <> tail:
      on_match_agrees(~check, ~Claim, same_attempt(attempt, key), phase,
        first_phase(attempt, tail), AtFirst(~Claim, attempt, tail), _ => agrees(phase),
        _ => first_agrees(~check, ~Claim, ~agrees, attempt, tail))
