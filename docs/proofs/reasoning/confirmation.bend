import Base
import ../logic.bend as Logic
import ../types.bend as T
import ./main.bend as Model

def nat_eq_refl(+n: Nat) -> {Nat.is_eq(n, n) == True{}: Bool}:
  match n:
    case 0n:
      {==}
    case 1n+prev:
      nat_eq_refl(prev)

def nat_eq_sound(left: Nat, right: Nat, equal: {Nat.is_eq(left, right) == True{}: Bool})
  -> {left == right: Nat}:
  match left right:
    case 0n 0n:
      {==}
    case 0n 1n+r:
      Empty.absurd({0n == 1n+r: Nat}, Logic.false_is_not_true(equal))
    case 1n+l 0n:
      Empty.absurd({1n+l == 0n: Nat}, Logic.false_is_not_true(equal))
    case 1n+l 1n+r:
      %nat_eq_sound(l, r, equal): {1n+l == 1n+_: Nat}
      {==}

def ConfirmationMatch(premise: Nat, fact: T.Fact) -> Data:
  {T.Confirmation{premise, T.Direct{}} == fact: T.Fact}

def impossible_confirmation(-premise: Nat, -fact: T.Fact, matches: {False{} == True{}: Bool})
  -> ConfirmationMatch(premise, fact):
  Empty.absurd(ConfirmationMatch(premise, fact), Logic.false_is_not_true(matches))

def confirmation_match_sound(
  premise: Nat,
  fact: T.Fact,
  matches: {Model.confirmation_matches(premise, fact) == True{}: Bool}
)
  -> ConfirmationMatch(premise, fact):
  match fact:
    case T.Confirmation{confirmed, T.Direct{}}:
      %nat_eq_sound(
        premise,
        confirmed,
        matches
      ): ConfirmationMatch(premise, T.Confirmation{_, T.Direct{}})
      {==}
    case T.Confirmation{confirmed, T.Derived{}}:
      impossible_confirmation(premise, T.Confirmation{confirmed, T.Derived{}}, matches)
    case T.Confirmation{confirmed, T.Directed{}}:
      impossible_confirmation(premise, T.Confirmation{confirmed, T.Directed{}}, matches)
    case T.Dependency{dependent, prerequisite}:
      impossible_confirmation(premise, T.Dependency{dependent, prerequisite}, matches)
    case T.ExternalLoop{actor, loop}:
      impossible_confirmation(premise, T.ExternalLoop{actor, loop}, matches)
    case T.Observable{actor, output}:
      impossible_confirmation(premise, T.Observable{actor, output}, matches)
    case T.DefaultEstablished{subject}:
      impossible_confirmation(premise, T.DefaultEstablished{subject}, matches)
    case T.CascadeOccurred{action, subject}:
      impossible_confirmation(premise, T.CascadeOccurred{action, subject}, matches)

def confirmation_match_complete(
  +premise: Nat,
  -fact: T.Fact,
  equal: ConfirmationMatch(premise, fact)
)
  -> {Model.confirmation_matches(premise, fact) == True{}: Bool}:
  %equal: {Model.confirmation_matches(premise, _) == True{}: Bool}
  nat_eq_refl(premise)
