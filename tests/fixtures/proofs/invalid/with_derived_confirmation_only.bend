import Base
import ./types.bend as T
import ./GNS004.bend as GNS004
import ./reasoning/SPEC.bend as Spec

def ctx() -> T.Context<T.ActionUse>:
  T.Frame{0n, T.Use{1n, 2n, 2n, False{}},
    T.Dependency{T.Action{1n}, T.Premise{2n}} <>
      T.Confirmation{2n, T.Derived{}} <> Nil{},
    Nil{}, T.NoIntervention{}}

def bad() -> Spec.Predicates.ValidatedBefore(ctx()):
  GNS004.theorem(ctx(), (Inl{{==}}, Inl{{==}}), {==})
