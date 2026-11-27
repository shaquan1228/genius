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
type Postulate<-source: T.Source, -Known: T.Hypothesis<source> -> Type> is Type:
  Assume{knowledge_requires_observation: @h: T.Hypothesis<source> -> Known(h) -> Finding<source>}
