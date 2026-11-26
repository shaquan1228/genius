import Base

# GNS-001, for an arbitrary fixed action A. Proposition parameters denote
# NonTrivial(A), OODA(A), ObserveFirst(A), and PrecededByObservation(A).
# P1, P2, and P3 are hypotheses; this theorem checks their composition.
def theorem(
  -NonTrivial: Type,
  -OODA: Type,
  -ObserveFirst: Type,
  -PrecededByObservation: Type,
  p1_nontrivial_enters_ooda: NonTrivial -> OODA,
  p2_ooda_observes_first: OODA -> ObserveFirst,
  p3_observe_first_precedes_action: ObserveFirst -> PrecededByObservation
) -> NonTrivial -> PrecededByObservation:
  nontrivial =>
    ooda = p1_nontrivial_enters_ooda(nontrivial)
    observe_first = p2_ooda_observes_first(ooda)
    p3_observe_first_precedes_action(observe_first)
