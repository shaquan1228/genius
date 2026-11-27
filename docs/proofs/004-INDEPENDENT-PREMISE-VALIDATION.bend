import Base
import ./types.bend as T
import ./reasoning/observation.bend as Obs
import ./logic.bend as Logic
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

# When the executable check supports a hypothesis, its source returned the expected answer.
def checked_evidence(
  +source: T.Source,
  +hypothesis: T.Hypothesis<source>,
  +observation: T.Observation<source>,
  accepted: {Obs.supported(Obs.check(source, hypothesis, observation)) == True{}: Bool}
) -> Obs.Evidence(source, hypothesis, observation):
  match hypothesis observation:
    case T.Predict{_} T.NoResponse{}:
      Logic.false_is_not_true(accepted)
    case T.Predict{expected} T.Returned{actual}:
      Obs.agreed(Obs.agrees(source, expected, actual), accepted)
