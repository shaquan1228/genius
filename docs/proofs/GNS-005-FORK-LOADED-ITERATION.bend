import Base
import ./logic.bend as Logic

# GNS-005, source steps 2-3: export P3a at a fixed dwell-state witness.
def loading_is_justified(
  -DwellState: Type,
  -LoadsFork: Type,
  -Justified: Type,
  p3a: Logic.Conj<DwellState, LoadsFork> -> Justified,
  dwell: DwellState
) -> LoadsFork -> Justified:
  loading => p3a(Logic.Conjunction{dwell, loading})

# GNS-005, source steps 2-4: export P3b at the same dwell state.
def not_loading_is_unjustified(
  -DwellState: Type,
  -LoadsFork: Type,
  -Justified: Type,
  p3b: Logic.Conj<DwellState, LoadsFork -> Empty> -> Justified -> Empty,
  dwell: DwellState
) -> (LoadsFork -> Empty) -> Justified -> Empty:
  not_loading => p3b(Logic.Conjunction{dwell, not_loading})

# Source step 5 uses classical contraposition. Its double-negation
# elimination principle is supplied explicitly, rather than assumed by Bend.
def justified_loads_fork(
  -LoadsFork: Type,
  -Justified: Type,
  eliminate_double_negation: ((LoadsFork -> Empty) -> Empty) -> LoadsFork,
  not_loading_is_unjustified: (LoadsFork -> Empty) -> Justified -> Empty,
  justified: Justified
) -> LoadsFork:
  Logic.reductio(
    LoadsFork,
    eliminate_double_negation,
    not_loading => not_loading_is_unjustified(not_loading, justified)
  )

# GNS-005, source steps 1-7. P2 is not used in those steps; it is the
# exhaustive/disjoint premise used by the corollary below.
def fork_loaded_iteration(
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
  not_loading = not_loading_is_unjustified(DwellState, LoadsFork, Justified, p3b, dwell)
  Logic.Equivalence{
    justified => justified_loads_fork(LoadsFork, Justified, eliminate_double_negation, not_loading, justified),
    loading_is_justified(DwellState, LoadsFork, Justified, p3a, dwell)
  }

# Source steps 8-9: the exclusive alternatives entail that tinkering
# excludes loading. This elimination is constructive and needs no DNE.
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

# Corollary GNS-005.1, source steps 8-10. P3a and classical contraposition
# are unnecessary here: P2 gives the negative loading witness directly.
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

# The prose's operational naming heuristic is not an extra theorem here.
# Naming a fork is not a premise proving LoadsFork in this formalization.
