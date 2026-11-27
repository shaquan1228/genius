import Base
import ../logic.bend as Logic
import ./latest.bend as Latest
import ./source-laws.bend as Sources
import ./observation.bend as Obs
import ../types.bend as T
import ./main.bend as Model
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws

def Laws.gns004_independent_premise_validation(ctx, applicable, allowed):
  match ctx:
    case T.Frame{_, T.Use{_, T.Claim{_, source, hypothesis}, _, _}, before, _, _}:
      Logic.agreement_sound(Obs.supported(Model.verdict(source, hypothesis, before)), Latest.Evidence(source, hypothesis, before),
        Latest.lookup_agrees(source, hypothesis, before), allowed)

def Laws.gns004_validation_gate_complete(ctx, applicable, confirmed):
  match ctx:
    case T.Frame{_, T.Use{_, T.Claim{_, source, hypothesis}, _, _}, before, _, _}:
      Logic.agreement_complete(Obs.supported(Model.verdict(source, hypothesis, before)), Latest.Evidence(source, hypothesis, before),
        Latest.lookup_agrees(source, hypothesis, before), confirmed)

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

def validation_burden(
  -NonTrivial: Type,
  -PrecededByObservation: Type,
  -DistinguishesKnownFromAssumed: Type,
  -DependsOn: Type,
  -ValidatedIndependently: Type,
  -Assumption: Type,
  -CascadeRisk: Type,
  gns001_observation_precedence: NonTrivial -> PrecededByObservation,
  p1_observation_classifies: PrecededByObservation -> DistinguishesKnownFromAssumed,
  p2_unvalidated_is_assumed: Logic.Conj<
    DistinguishesKnownFromAssumed,
    ValidatedIndependently -> Empty> -> Assumption,
  p3_assumed_dependency_creates_risk: Logic.Conj<DependsOn, Assumption> -> CascadeRisk,
  n_no_cascade_risk: CascadeRisk -> Empty,
  trigger: Logic.Conj<NonTrivial, DependsOn>
) -> (ValidatedIndependently -> Empty) -> Empty:
  match trigger:
    case Logic.Conjunction{nontrivial, depends_on}:
      observed = gns001_observation_precedence(nontrivial)
      classified = p1_observation_classifies(observed)
      unvalidated =>
        assumed = p2_unvalidated_is_assumed(Logic.Conjunction{classified, unvalidated})
        risk = p3_assumed_dependency_creates_risk(Logic.Conjunction{depends_on, assumed})
        n_no_cascade_risk(risk)
