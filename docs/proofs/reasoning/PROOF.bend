import Base
import ./confirmation.bend as Confirmation
import ../types.bend as T
import ./main.bend as Model
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws

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
  +facts: List<&2, T.Fact>,
  found: {Model.has_direct_confirmation(premise, facts) == True{}: Bool}
)
  -> Spec.Predicates.ValidatedAt(premise, facts):
  match facts:
    case Nil{}:
      Confirmation.false_is_not_true(found)
    case head <> tail:
      search_found(
        Model.confirmation_matches(premise, head),
        Model.has_direct_confirmation(premise, tail),
        Confirmation.ConfirmationMatch(premise, head),
        Spec.Predicates.ValidatedAt(premise, tail),
        matches => Confirmation.confirmation_match_sound(premise, head, matches),
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
  +facts: List<&2, T.Fact>,
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
            Confirmation.confirmation_match_complete(premise, head, equal)
          )
        case Inr{in_tail}:
          search_succeeds_in_tail(
            Model.confirmation_matches(premise, head),
            Model.has_direct_confirmation(premise, tail),
            direct_confirmation_complete(premise, tail, in_tail)
          )

def Laws.gns004_independent_premise_validation(ctx, applicable, allowed):
  match ctx:
    case T.Frame{_, T.Use{_, premise, _, _}, before, _, _}:
      direct_confirmation_sound(premise, before, allowed)

def Laws.gns004_validation_gate_complete(ctx, applicable, confirmed):
  match ctx:
    case T.Frame{_, T.Use{_, premise, _, _}, before, _, _}:
      direct_confirmation_complete(premise, before, confirmed)

def eliminate_alternatives(
  -ctx: T.Context<T.ExternalUse>,
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
