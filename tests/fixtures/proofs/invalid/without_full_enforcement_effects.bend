import Base
import ./types.bend as T
import ./reasoning/main.bend as Model
import ./reasoning/SPEC.bend as Spec

def bad(+ctx: T.Context<T.ExternalUse>,
  applicable: Spec.Predicates.PremiseRequiredBefore(Model.action_context(ctx)),
  forward: Spec.Premises.Forward<ctx>,
  validates: Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.ValidatedAfter(ctx)
) -> Spec.Premises.Enforcement<ctx>:
  Spec.EnforcementPremises{applicable, forward, validates}
