import Base
import ./main.bend as Model
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws

def IsTrue(flag: Bool) -> Data:
  match flag:
    case True{}:
      Unit
    case False{}:
      Empty

def false_is_not_true(equal: {False{} == True{}: Bool}) -> Empty:
  %Equal.sym(Bool, False{}, True{}, equal): IsTrue(_)
  Unit{}

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
      Empty.absurd({0n == 1n+r: Nat}, false_is_not_true(equal))
    case 1n+l 0n:
      Empty.absurd({1n+l == 0n: Nat}, false_is_not_true(equal))
    case 1n+l 1n+r:
      %nat_eq_sound(l, r, equal): {1n+l == 1n+_: Nat}
      {==}

def ConfirmationMatch(premise: Nat, fact: Model.Fact) -> Data:
  {Model.Confirmation{premise, Model.Direct{}} == fact: Model.Fact}

def impossible_confirmation(-premise: Nat, -fact: Model.Fact, matches: {False{} == True{}: Bool})
  -> ConfirmationMatch(premise, fact):
  Empty.absurd(ConfirmationMatch(premise, fact), false_is_not_true(matches))

def confirmation_match_sound(
  premise: Nat,
  fact: Model.Fact,
  matches: {Model.confirmation_matches(premise, fact) == True{}: Bool}
)
  -> ConfirmationMatch(premise, fact):
  match fact:
    case Model.Confirmation{confirmed, Model.Direct{}}:
      %nat_eq_sound(
        premise,
        confirmed,
        matches
      ): ConfirmationMatch(premise, Model.Confirmation{_, Model.Direct{}})
      {==}
    case Model.Confirmation{confirmed, Model.Derived{}}:
      impossible_confirmation(premise, Model.Confirmation{confirmed, Model.Derived{}}, matches)
    case Model.Confirmation{confirmed, Model.Directed{}}:
      impossible_confirmation(premise, Model.Confirmation{confirmed, Model.Directed{}}, matches)
    case Model.Dependency{dependent, prerequisite}:
      impossible_confirmation(premise, Model.Dependency{dependent, prerequisite}, matches)
    case Model.ExternalLoop{actor, loop}:
      impossible_confirmation(premise, Model.ExternalLoop{actor, loop}, matches)
    case Model.Observable{actor, output}:
      impossible_confirmation(premise, Model.Observable{actor, output}, matches)
    case Model.DefaultEstablished{subject}:
      impossible_confirmation(premise, Model.DefaultEstablished{subject}, matches)
    case Model.CascadeOccurred{action, subject}:
      impossible_confirmation(premise, Model.CascadeOccurred{action, subject}, matches)

def confirmation_match_complete(
  +premise: Nat,
  -fact: Model.Fact,
  equal: ConfirmationMatch(premise, fact)
)
  -> {Model.confirmation_matches(premise, fact) == True{}: Bool}:
  %equal: {Model.confirmation_matches(premise, _) == True{}: Bool}
  nat_eq_refl(premise)

def search_found(
  +matches: Bool,
  -rest: Bool,
  -Here: Data,
  -Later: Data,
  here: {matches == True{}: Bool} -> Here,
  later: {rest == True{}: Bool} -> Later,
  found: {List.any.if(_ => rest, matches) == True{}: Bool}
)
  -> Either<&2, &2, Here, Later>:
  match matches:
    case True{}:
      Inl{here({==})}
    case False{}:
      Inr{later(found)}

def direct_confirmation_sound(
  +premise: Nat,
  +facts: List<&2, Model.Fact>,
  found: {Model.has_direct_confirmation(premise, facts) == True{}: Bool}
)
  -> Spec.Predicates.ValidatedAt(premise, facts):
  match facts:
    case Nil{}:
      false_is_not_true(found)
    case head <> tail:
      search_found(
        Model.confirmation_matches(premise, head),
        Model.has_direct_confirmation(premise, tail),
        ConfirmationMatch(premise, head),
        Spec.Predicates.ValidatedAt(premise, tail),
        matches => confirmation_match_sound(premise, head, matches),
        rest => direct_confirmation_sound(premise, tail, rest),
        found
      )

def search_succeeds_at_head(+matches: Bool, -rest: Bool, found: {matches == True{}: Bool})
  -> {List.any.if(_ => rest, matches) == True{}: Bool}:
  %Equal.sym(Bool, matches, True{}, found): {List.any.if(_ => rest, _) == True{}: Bool}
  {==}

def search_succeeds_in_tail(matches: Bool, -rest: Bool, found: {rest == True{}: Bool})
  -> {List.any.if(_ => rest, matches) == True{}: Bool}:
  match matches:
    case True{}:
      {==}
    case False{}:
      found

def direct_confirmation_complete(
  +premise: Nat,
  +facts: List<&2, Model.Fact>,
  confirmed: Spec.Predicates.ValidatedAt(premise, facts)
)
  -> {Model.has_direct_confirmation(premise, facts) == True{}: Bool}:
  match facts:
    case Nil{}:
      match confirmed:
    case head <> tail:
      match confirmed:
        case Inl{equal}:
          search_succeeds_at_head(
            Model.confirmation_matches(premise, head),
            Model.has_direct_confirmation(premise, tail),
            confirmation_match_complete(premise, head, equal)
          )
        case Inr{in_tail}:
          search_succeeds_in_tail(
            Model.confirmation_matches(premise, head),
            Model.has_direct_confirmation(premise, tail),
            direct_confirmation_complete(premise, tail, in_tail)
          )

def Laws.gns004_independent_premise_validation(ctx, applicable, allowed):
  match ctx:
    case Model.Frame{_, Model.Use{_, premise, _, _}, before, _, _}:
      direct_confirmation_sound(premise, before, allowed)

def Laws.gns004_validation_gate_complete(ctx, applicable, confirmed):
  match ctx:
    case Model.Frame{_, Model.Use{_, premise, _, _}, before, _, _}:
      direct_confirmation_complete(premise, before, confirmed)

def eliminate_alternatives(
  -ctx: Model.Context<Model.ExternalUse>,
  alternatives: Or(
    Spec.Predicates.Probed(ctx),
    Or(Spec.Predicates.Signaled(ctx), Spec.Predicates.Enforcement(ctx))
  ),
  no_probe: Spec.Predicates.Probed(ctx) -> Empty,
  no_signal: Spec.Predicates.Signaled(ctx) -> Empty
) -> Spec.Predicates.Enforcement(ctx):
  match alternatives:
    case Inl{probe}:
      Empty.absurd(Spec.Predicates.Enforcement(ctx), no_probe(probe))
    case Inr{Inl{signal}}:
      Empty.absurd(Spec.Predicates.Enforcement(ctx), no_signal(signal))
    case Inr{Inr{enforced}}:
      enforced

def Laws.gns006_validation_implies_enforcement(ctx, premises, confirmed):
  match premises:
    case Spec.Forward{
      dependency,
      signal_cannot_validate,
      classify,
      probe_requires_observability,
      unobservable
    }:
      +evidence = confirmed
      eliminate_alternatives(
        ctx,
        classify(dependency, evidence),
        probe => unobservable(probe_requires_observability(probe)),
        signal => signal_cannot_validate(signal, evidence)
      )

def Laws.gns006_structural_enforcement(ctx, premises):
  match premises:
    case Spec.EnforcementPremises{_, forward, effects}:
      (confirmed => Laws.gns006_validation_implies_enforcement(ctx, forward, confirmed), effects)
