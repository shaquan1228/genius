import Base
import ./main.bend as Model
import ./SPEC.bend as Spec

law gns004_independent_premise_validation:
  for +ctx: Model.Context<Model.ActionUse>
  for applicable: Spec.Predicates.PremiseRequiredBefore(ctx)
  for allowed: {Model.premise_gate(ctx) == True{} : Bool}
  Spec.Predicates.ValidatedBefore(ctx)

law gns004_validation_gate_complete:
  for +ctx: Model.Context<Model.ActionUse>
  for applicable: Spec.Predicates.PremiseRequiredBefore(ctx)
  for confirmed: Spec.Predicates.ValidatedBefore(ctx)
  {Model.premise_gate(ctx) == True{} : Bool}

law gns006_validation_implies_enforcement:
  for +ctx: Model.Context<Model.ExternalUse>
  for premises: Spec.Premises.Forward<ctx>
  for confirmed: Spec.Predicates.ValidatedAfter(ctx)
  Spec.Predicates.Enforcement(ctx)

law gns006_structural_enforcement:
  for +ctx: Model.Context<Model.ExternalUse>
  for premises: Spec.Premises.Enforcement<ctx>
  ((Spec.Predicates.ValidatedAfter(ctx) -> Spec.Predicates.Enforcement(ctx)) &
    (Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>))
