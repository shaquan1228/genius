import Base
import ./logic.bend as Logic

# GNS-004 steps 1-12. For a fixed action A and premise P, the normative
# hypotheses constructively rule out a refutation of validation.
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
  p2_unvalidated_is_assumed:
    Logic.Conj<DistinguishesKnownFromAssumed, ValidatedIndependently -> Empty> -> Assumption,
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

# GNS-004 steps 13-14 use classical reductio. Its double-negation
# elimination principle is an explicit logical hypothesis, not a new
# decidability requirement and not a proof of the normative premise N.
def theorem(
  -NonTrivial: Type,
  -PrecededByObservation: Type,
  -DistinguishesKnownFromAssumed: Type,
  -DependsOn: Type,
  -ValidatedIndependently: Type,
  -Assumption: Type,
  -CascadeRisk: Type,
  classical_reductio:
    ((ValidatedIndependently -> Empty) -> Empty) -> ValidatedIndependently,
  gns001_observation_precedence: NonTrivial -> PrecededByObservation,
  p1_observation_classifies: PrecededByObservation -> DistinguishesKnownFromAssumed,
  p2_unvalidated_is_assumed:
    Logic.Conj<DistinguishesKnownFromAssumed, ValidatedIndependently -> Empty> -> Assumption,
  p3_assumed_dependency_creates_risk: Logic.Conj<DependsOn, Assumption> -> CascadeRisk,
  n_no_cascade_risk: CascadeRisk -> Empty,
  trigger: Logic.Conj<NonTrivial, DependsOn>
) -> ValidatedIndependently:
  Logic.reductio(ValidatedIndependently, classical_reductio, validation_burden(
    NonTrivial, PrecededByObservation, DistinguishesKnownFromAssumed,
    DependsOn, ValidatedIndependently, Assumption, CascadeRisk,
    gns001_observation_precedence, p1_observation_classifies,
    p2_unvalidated_is_assumed, p3_assumed_dependency_creates_risk,
    n_no_cascade_risk, trigger
  ))
