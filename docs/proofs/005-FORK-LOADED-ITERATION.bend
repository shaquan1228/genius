import Base
import ./logic.bend as Logic
import ./reasoning/iteration.bend as Iteration

def theorem(
  -Iteration: Type,
  -DwellState: Data,
  -LoadsFork: Type,
  -Justified: Type,
  p1: Iteration -> DwellState,
  p3a: Logic.Conj<DwellState, LoadsFork> -> Justified,
  p3b: Logic.Conj<DwellState, LoadsFork -> Empty> -> Justified -> Empty,
  eliminate_double_negation: ((LoadsFork -> Empty) -> Empty) -> LoadsFork,
  iteration: Iteration
) -> Logic.Iff<Justified, LoadsFork>:
  +dwell = p1(iteration)
  Logic.Equivalence{
    justified => eliminate_double_negation(not_loading =>
      p3b(Logic.Conjunction{dwell, not_loading}, justified)),
    loading => p3a(Logic.Conjunction{dwell, loading})
  }
