import Base
import ../types.bend as T
import ./main.bend as Model
import ./SPEC.bend as Spec

law gns004_independent_premise_validation:
  for +ctx: T.Context<T.ActionUse>
  for applicable: Spec.Predicates.PremiseRequiredBefore(ctx)
  for allowed: {Model.premise_gate(ctx) == True{} : Bool}
  Spec.Predicates.ValidatedBefore(ctx)

law gns004_validation_gate_complete:
  for +ctx: T.Context<T.ActionUse>
  for applicable: Spec.Predicates.PremiseRequiredBefore(ctx)
  for confirmed: Spec.Predicates.ValidatedBefore(ctx)
  {Model.premise_gate(ctx) == True{} : Bool}

law gns006_validation_implies_enforcement:
  for +ctx: T.Context<T.ExternalUse>
  for premises: Spec.Premises.Forward<ctx>
  for confirmed: Spec.Predicates.ValidatedAfter(ctx)
  Spec.Predicates.Enforcement(ctx)

law gns006_structural_enforcement:
  for +ctx: T.Context<T.ExternalUse>
  for premises: Spec.Premises.Enforcement<ctx>
  ((Spec.Predicates.ValidatedAfter(ctx) -> Spec.Predicates.Enforcement(ctx)) &
    (Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>))
