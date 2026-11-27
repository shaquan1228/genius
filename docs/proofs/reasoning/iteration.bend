import Base
import ../logic.bend as Logic

def tinkering_excludes_loading(
  -LoadsFork: Type,
  -Tinkering: Type,
  alternatives: Logic.Xor<LoadsFork, Tinkering>,
  tinkering: Tinkering
) -> LoadsFork -> Empty:
  match alternatives:
    case Logic.ExclusiveLeft{value, excludes}:
      Empty.absurd(LoadsFork -> Empty, excludes(tinkering))
    case Logic.ExclusiveRight{value, excludes}:
      excludes

def tinkering_never_justified(
  -Iteration: Type,
  -DwellState: Data,
  -LoadsFork: Type,
  -Tinkering: Type,
  -Justified: Type,
  p1: Iteration -> DwellState,
  p2: DwellState -> Logic.Xor<LoadsFork, Tinkering>,
  p3b: Logic.Conj<DwellState, LoadsFork -> Empty> -> Justified -> Empty,
  iteration: Iteration,
  tinkering: Tinkering
) -> Justified -> Empty:
  +dwell = p1(iteration)
  not_loading = tinkering_excludes_loading(LoadsFork, Tinkering, p2(dwell), tinkering)
  p3b(Logic.Conjunction{dwell, not_loading})
