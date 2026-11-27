import Base

# This file states Postulate 001 as a hypothesis. It does not prove the
# hypothesis, and none of GNS-001..006 imports it as a foundation.
type LoopHypothesis<-Known: Type, -PassedThroughLoop: Type> is Type:
  Hypothesis{knowledge_requires_loop: Known -> PassedThroughLoop}

# A direct conditional consequence of accepting the postulate.
def knowledge_requires_loop(
  -Known: Type,
  -PassedThroughLoop: Type,
  hypothesis: LoopHypothesis<Known, PassedThroughLoop>,
  known: Known
) -> PassedThroughLoop:
  match hypothesis:
    case Hypothesis{knowledge_requires_loop}:
      knowledge_requires_loop(known)

# Derivation alone does not establish knowledge when there is no loop witness.
# The Derivation witness is deliberately not a substitute for that witness.
def derivation_without_loop_is_not_knowledge(
  -Known: Type,
  -PassedThroughLoop: Type,
  -Derivation: Type,
  hypothesis: LoopHypothesis<Known, PassedThroughLoop>,
  derivation: Derivation,
  has_not_passed_loop: PassedThroughLoop -> Empty
) -> Known -> Empty:
  known => has_not_passed_loop(
    knowledge_requires_loop(Known, PassedThroughLoop, hypothesis, known)
  )
