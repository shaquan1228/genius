import Base
import ./types.bend as T
import ./reasoning/SPEC.bend as Spec

def ctx() -> T.Context<T.ActionUse>:
  +parser: T.Source = T.ParserCase{"v1", "[1,]"}
  original: T.PremiseClaim = T.Claim{2n, parser, T.Predict{T.Rejected{}}}
  replacement: T.PremiseClaim = T.Claim{2n, parser, T.Predict{T.Accepted{}}}
  before: List<&2, T.Fact> = [T.Dependency{T.Action{1n}, T.Premise{original}},
    T.Reading{parser, T.Accepted{}}]
  T.Frame{0n, T.Use{1n, replacement, 2n, False{}}, before, Nil{}, T.NoIntervention{}}

# A dependency on the original prediction cannot be reused for its opposite.
def bad() -> Spec.Predicates.PremiseRequiredBefore(ctx()):
  (Inl{{==}}, Inl{{==}})
