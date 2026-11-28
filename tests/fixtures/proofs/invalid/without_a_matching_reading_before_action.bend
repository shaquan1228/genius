import Base
import ./types.bend as T
import ./GNS004.bend as GNS004
import ./reasoning/SPEC.bend as Spec

def ctx() -> T.Context<T.ActionUse>:
  +parser: T.Source = T.ParserCase{"v1", "[1,]"}
  +premise: T.PremiseClaim = T.Claim{2n, parser, T.Predict{T.Rejected{}}}
  before: List<&2, T.Fact> = [T.Dependency{T.Action{1n}, T.Premise{premise}},
    T.Reading{T.TestSuite{"run-17", ".", "missing.py"}, False{}}]
  after: List<&2, T.Fact> = [T.Reading{parser, T.Rejected{}}]
  T.Frame{0n, T.Use{1n, premise, 2n, False{}}, before, after, T.NoIntervention{}}

def bad() -> Spec.Predicates.ValidatedBefore(ctx()):
  GNS004.theorem(ctx(), (Inl{{==}}, Inl{{==}}), {==})
