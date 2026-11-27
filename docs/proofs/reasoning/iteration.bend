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
  dwell_of_iteration: Iteration -> DwellState,
  loading_or_tinkering: DwellState -> Logic.Xor<LoadsFork, Tinkering>,
  no_loading_rules_out_justification: Logic.Conj<DwellState, LoadsFork -> Empty> -> Justified -> Empty,
  iteration: Iteration,
  tinkering: Tinkering
) -> Justified -> Empty:
  +dwell = dwell_of_iteration(iteration)
  alternatives = loading_or_tinkering(dwell)
  not_loading = tinkering_excludes_loading(LoadsFork, Tinkering, alternatives, tinkering)
  no_loading_rules_out_justification(Logic.Conjunction{dwell, not_loading})
