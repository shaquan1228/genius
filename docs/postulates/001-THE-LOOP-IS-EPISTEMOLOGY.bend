import Base
import ../proofs/types.bend as T

# A completed probe has a recorded response, even when the prediction was wrong.
type Finding<-source: T.Source> is Data:
  Recorded{
    observation: T.Observation<source>,
    returned: {T.received(source, observation) == True{}: Bool}
  }

# Open postulate. Accepting it requires a way to produce a finding about
# the same source for any hypothesis we claim to know.
def no_finding_rules_out_knowledge(
  -source: T.Source,
  -Known: T.Hypothesis<source> -> Type,
  knowledge_requires_observation: @h: T.Hypothesis<source> -> Known(h) -> Finding<source>,
  hypothesis: T.Hypothesis<source>,
  no_finding: Finding<source> -> Empty
) -> Known(hypothesis) -> Empty:
  known => no_finding(knowledge_requires_observation(hypothesis, known))
