import Base
import ../../../docs/proofs/types.bend as T
import ../../../docs/proofs/reasoning/SPEC.bend as Spec

def context(intervention: T.Intervention) -> T.Context<T.ExternalUse>:
  +output: T.LoopOutput = T.Output{3n, 7n}
  +claim: T.PremiseClaim = T.Claim{2n, T.ParserCase{"v1", "[1,]"}, T.Predict{T.Rejected{}}}
  use: T.ExternalUse = T.UseOutput{T.Use{1n, claim, 2n, False{}}, output}
  before: List<&2, T.Fact> = [
    T.Dependency{T.Premise{claim}, T.OutputSubject{output}}, T.ExternalLoop{1n, 3n}, T.Observable{1n, output}]
  T.Frame{1n, use, before, Nil{}, intervention}

def the_premise_depends_on_this_external_output()
  -> Spec.Predicates.ExternalDependency(context(T.NoIntervention{})):
  (Inl{{==}}, Inr{Inl{{==}}})

def this_output_was_observable() -> Spec.Predicates.ObservableBefore(context(T.NoIntervention{})):
  Inr{Inr{Inl{{==}}}}

def this_output_was_probed() -> Spec.Predicates.Probed(context(T.Probe{T.Output{3n, 7n}})):
  {==}

def this_output_was_signaled() -> Spec.Predicates.Signaled(context(T.Signal{T.Output{3n, 7n}})):
  {==}
