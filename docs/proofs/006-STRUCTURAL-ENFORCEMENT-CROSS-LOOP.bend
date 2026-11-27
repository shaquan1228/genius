import Base
import ./types.bend as T
import ./logic.bend as Logic
import ./reasoning/SPEC.bend as Spec
import ./reasoning/LAWS.bend as Laws
import ./reasoning/PROOF.bend as Proof

def theorem(
  +ctx: T.Context<T.ExternalUse>,
  premises: Spec.Premises.Enforcement<ctx>
) -> (
  (
    Spec.Predicates.ValidatedAfter(ctx) -> Spec.Predicates.Enforcement(ctx)
  )
    & (Spec.Predicates.Enforcement(ctx) -> Spec.Predicates.EnforcementEffects<ctx>)
):
  Laws.gns006_structural_enforcement(ctx, premises)

def validation_implies_enforcement(
  +ctx: T.Context<T.ExternalUse>,
  premises: Spec.Premises.Forward<ctx>,
  confirmed: Spec.Predicates.ValidatedAfter(ctx)
) -> Spec.Predicates.Enforcement(ctx):
  Laws.gns006_validation_implies_enforcement(ctx, premises, confirmed)

def initial_assumption(
  -DependsOutput0: Type,
  -Exogenous: Type,
  -Assumption0: Type,
  p1: DependsOutput0 -> Exogenous -> Assumption0,
  depends_output0: DependsOutput0,
  exogenous: Exogenous
) -> Assumption0:
  p1(depends_output0, exogenous)

def trusted_agent_corollary(
  -Agent: Type,
  -Trusted: Type,
  -Validated1: Type,
  -Enforce01: Type,
  parent: Logic.Iff<Validated1, Enforce01>,
  agent: Agent,
  trusted: Trusted
) -> Logic.Iff<Validated1, Enforce01>:
  parent
