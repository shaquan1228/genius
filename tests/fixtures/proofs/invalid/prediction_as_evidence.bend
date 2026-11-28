import Base
import ./types.bend as T

def bad(-source: T.Source, h: T.Hypothesis<source>) -> Bool:
  T.received(source, h)
