import Base
import ./types.bend as T
import ./reasoning/main.bend as Model
import ./reasoning/SPEC.bend as Spec
import ./reasoning/LAWS.bend as Laws
import ./reasoning/PROOF.bend as Proof

def theorem(
  +ctx: T.Context<T.ActionUse>,
  applicable: Spec.Predicates.PremiseRequiredBefore(ctx),
  allowed: {Model.premise_gate(ctx) == True{}: Bool}
) -> Spec.Predicates.ValidatedBefore(ctx):
  Laws.gns004_independent_premise_validation(ctx, applicable, allowed)
