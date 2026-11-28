import Base
import ./types.bend as T
import ./reasoning/SPEC.bend as Spec
import ./reasoning/LAWS.bend as Laws
import ./reasoning/PROOF.bend as Proof

def theorem(
  +ctx: T.Context<T.ExternalUse>,
  premises: Spec.Premises.Enforcement<ctx>
) -> (
  (Spec.Predicates.ValidatedAfter(ctx) -> Spec.Predicates.Enforcement(ctx)) &
  (Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>)
):
  Laws.gns006_structural_enforcement(ctx, premises)
