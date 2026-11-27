import Base
import ./types.bend as T
import ./ooda/main.bend as Loop
import ./ooda/SPEC.bend as Spec
import ./ooda/LAWS.bend as Laws
import ./ooda/PROOF.bend as Proof

def theorem(
  +viable_approaches: Nat,
  +uncertain: Bool,
  +attempt: T.Attempt,
  +history: List<&2, T.TraceEvent>,
  nontrivial: Spec.NonTrivial(viable_approaches, uncertain),
  allowed: {Loop.observation_allows_act(viable_approaches, uncertain, attempt, history) == True{} : Bool}
) -> Spec.ObservedFirst(attempt, history):
  Laws.gns001_observation_precedence(viable_approaches, uncertain, attempt, history, nontrivial, allowed)
