import Base
import ./types.bend as T

def bad() -> T.Phase:
  T.Observed{T.ParserCase{"v1", "[1,]"}, "I think the parser works"}
