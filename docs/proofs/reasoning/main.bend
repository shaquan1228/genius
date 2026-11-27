import Base
import ../types.bend as T
import ./history.bend as History
import ./observation.bend as Obs

def action_context(ctx: T.Context<T.ExternalUse>) -> T.Context<T.ActionUse>:
  match ctx:
    case T.Frame{actor, T.UseOutput{use, _, _}, before, after, intervention}:
      T.Frame{actor, use, before, after, intervention}

def verdict(+source: T.Source, hypothesis: T.Hypothesis<source>, history: List<&2, T.Fact>) -> T.Verdict:
  Obs.check(source, hypothesis, History.answer_to(source, history))

def premise_gate(ctx: T.Context<T.ActionUse>) -> Bool:
  match ctx:
    case T.Frame{_, T.Use{_, T.Claim{_, source, hypothesis}, _, _}, before, _, _}:
      Obs.supported(verdict(source, hypothesis, before))

def main() -> Bool:
  +source: T.Source = T.ParserCase{"parser-v1", "[1,]"}
  premise: T.PremiseClaim = T.Claim{3n, source, T.Predict{T.Rejected{}}}
  premise_gate(T.Frame{1n, T.Use{2n, premise, 2n, False{}},
    T.Reading{source, T.Rejected{}} <> Nil{}, Nil{}, T.NoIntervention{}})
