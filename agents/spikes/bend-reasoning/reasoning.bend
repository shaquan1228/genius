import Base

type Decision<-Proposition: Type> is Type:
  DecidedTrue{witness: Proposition}
  DecidedFalse{refute: Proposition -> Empty}

def decidable_reductio(
  -Proposition: Type,
  decision: Decision<Proposition>,
  refute_refutation: (Proposition -> Empty) -> Empty
) -> Proposition:
  match decision:
    case DecidedTrue{witness}:
      witness
    case DecidedFalse{refute}:
      Empty.absurd(Proposition, refute_refutation(refute))

def observation_precedence(
  -NonTrivial: Type,
  -OODA: Type,
  -ObserveFirst: Type,
  -Observed: Type,
  enters_loop: NonTrivial -> OODA,
  observes_first: OODA -> ObserveFirst,
  observation_occurred: ObserveFirst -> Observed,
  action: NonTrivial
) -> Observed:
  observation_occurred(observes_first(enters_loop(action)))

def validation_burden(
  -Classified: Type,
  -Depends: Type,
  -Validated: Type,
  -Assumption: Type,
  -CascadeRisk: Type,
  classified: Classified,
  depends: Depends,
  unvalidated_is_assumed: Classified -> (Validated -> Empty) -> Assumption,
  assumption_creates_risk: Depends -> Assumption -> CascadeRisk,
  no_cascade_risk: CascadeRisk -> Empty
) -> (Validated -> Empty) -> Empty:
  unvalidated => no_cascade_risk(
    assumption_creates_risk(depends, unvalidated_is_assumed(classified, unvalidated))
  )

def independent_validation(
  -Classified: Type,
  -Depends: Type,
  -Validated: Type,
  -Assumption: Type,
  -CascadeRisk: Type,
  decision: Decision<Validated>,
  classified: Classified,
  depends: Depends,
  unvalidated_is_assumed: Classified -> (Validated -> Empty) -> Assumption,
  assumption_creates_risk: Depends -> Assumption -> CascadeRisk,
  no_cascade_risk: CascadeRisk -> Empty
) -> Validated:
  decidable_reductio(Validated, decision, validation_burden(
    Classified, Depends, Validated, Assumption, CascadeRisk,
    classified, depends, unvalidated_is_assumed,
    assumption_creates_risk, no_cascade_risk
  ))

def independent_validation_for_action(
  -NonTrivial: Type,
  -Observed: Type,
  -Classified: Type,
  -Depends: Type,
  -Validated: Type,
  -Assumption: Type,
  -CascadeRisk: Type,
  observe: NonTrivial -> Observed,
  classify: Observed -> Classified,
  unvalidated_is_assumed: Classified -> (Validated -> Empty) -> Assumption,
  assumption_creates_risk: Depends -> Assumption -> CascadeRisk,
  no_cascade_risk: CascadeRisk -> Empty,
  decision: Decision<Validated>,
  action: NonTrivial,
  depends: Depends
) -> Validated:
  independent_validation(
    Classified, Depends, Validated, Assumption, CascadeRisk,
    decision, classify(observe(action)), depends,
    unvalidated_is_assumed, assumption_creates_risk, no_cascade_risk
  )
