import Base
import ../types.bend as T

def action_context(ctx: T.Context<T.ExternalUse>) -> T.Context<T.ActionUse>:
  match ctx:
    case T.Frame{actor, T.UseOutput{use, _, _}, before, after, intervention}:
      T.Frame{actor, use, before, after, intervention}

def confirmation_matches(premise: Nat, fact: T.Fact) -> Bool:
  match fact:
    case T.Confirmation{confirmed, T.Direct{}}:
      Nat.is_eq(premise, confirmed)
    case other:
      False{}

def has_direct_confirmation(+premise: Nat, facts: List<&2, T.Fact>) -> Bool:
  match facts:
    case Nil{}:
      False{}
    case head <> tail:
      List.any.if(_ => has_direct_confirmation(premise, tail), confirmation_matches(premise, head))

def premise_gate(ctx: T.Context<T.ActionUse>) -> Bool:
  match ctx:
    case T.Frame{_, T.Use{_, premise, _, _}, before, _, _}:
      has_direct_confirmation(premise, before)

def main() -> Bool:
  premise_gate(
    T.Frame{
      1n,
      T.Use{2n, 3n, 2n, False{}},
      T.Confirmation{3n, T.Direct{}} <> Nil{},
      Nil{},
      T.NoIntervention{}
    }
  )
