import Base
import ./logic.bend as Logic
import ./reasoning/iteration.bend as Iteration

def theorem(
  -Iteration: Type,
  -DwellState: Data,
  -LoadsFork: Type,
  -Justified: Type,
  dwell_of_iteration: Iteration -> DwellState,
  loading_justifies_iteration: Logic.Conj<DwellState, LoadsFork> -> Justified,
  no_loading_rules_out_justification: Logic.Conj<DwellState, LoadsFork -> Empty> -> Justified -> Empty,
  eliminate_double_negation: ((LoadsFork -> Empty) -> Empty) -> LoadsFork,
  iteration: Iteration
) -> Logic.Iff<Justified, LoadsFork>:
  +dwell = dwell_of_iteration(iteration)
  Logic.Equivalence{
    justified => eliminate_double_negation(not_loading =>
      no_loading_rules_out_justification(Logic.Conjunction{dwell, not_loading}, justified)),
    loading => loading_justifies_iteration(Logic.Conjunction{dwell, loading})
  }
