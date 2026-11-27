import Base
import ../logic.bend as Logic

def fork_loaded_iteration(
  -Iteration: Type,
  -DwellState: Data,
  -LoadsFork: Type,
  -Justified: Type,
  dwell_of_iteration: Iteration -> DwellState,
  loading_justifies_iteration: DwellState -> LoadsFork -> Justified,
  no_loading_rules_out_justification: DwellState -> (LoadsFork -> Empty) -> Justified -> Empty,
  eliminate_double_negation: ((LoadsFork -> Empty) -> Empty) -> LoadsFork,
  iteration: Iteration
) -> Logic.Iff(Justified, LoadsFork):
  +dwell = dwell_of_iteration(iteration)
  (
    justified => eliminate_double_negation(not_loading =>
      no_loading_rules_out_justification(dwell, not_loading, justified)),
    loading => loading_justifies_iteration(dwell, loading)
  )

def tinkering_excludes_loading(
  -LoadsFork: Type,
  -Tinkering: Type,
  alternatives: Logic.Xor(LoadsFork, Tinkering),
  tinkering: Tinkering
) -> LoadsFork -> Empty:
  match alternatives:
    case Inl{(_, excludes_tinkering)}:
      Empty.absurd(LoadsFork -> Empty, excludes_tinkering(tinkering))
    case Inr{(_, excludes_loading)}:
      excludes_loading

def tinkering_never_justified(
  -Iteration: Type,
  -DwellState: Data,
  -LoadsFork: Type,
  -Tinkering: Type,
  -Justified: Type,
  dwell_of_iteration: Iteration -> DwellState,
  loading_or_tinkering: DwellState -> Logic.Xor(LoadsFork, Tinkering),
  no_loading_rules_out_justification: DwellState -> (LoadsFork -> Empty) -> Justified -> Empty,
  iteration: Iteration,
  tinkering: Tinkering
) -> Justified -> Empty:
  +dwell = dwell_of_iteration(iteration)
  alternatives = loading_or_tinkering(dwell)
  not_loading = tinkering_excludes_loading(LoadsFork, Tinkering, alternatives, tinkering)
  no_loading_rules_out_justification(dwell, not_loading)
