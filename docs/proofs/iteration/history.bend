import Base
import ../types.bend as T
import ../logic.bend as Logic

type Decision<-Claim: Type> is Type:
  Found{evidence: Claim}
  Missing{refute: Claim -> Empty}

def Somewhere(~Q: Data, ~Claim: Q -> T.AttemptEvent<T.Fact> -> T.IterationHistory -> Type,
  +query: Q, history: T.IterationHistory) -> Type:
  match history:
    case T.Start{}: Empty
    case T.Record{event, earlier}: Or(Claim(query, event, earlier), Somewhere(~Q, ~Claim, query, earlier))

def refute_either(-A: Type, -B: Type, no_a: A -> Empty, no_b: B -> Empty, either: Or(A, B)) -> Empty:
  match either:
    case Inl{a}: no_a(a)
    case Inr{b}: no_b(b)

def search_earlier(-Here: Type, -Earlier: Type, no_here: Here -> Empty, result: Decision<Earlier>)
  -> Decision<Or(Here, Earlier)>:
  match result:
    case Found{evidence}: Found{Inr{evidence}}
    case Missing{no_earlier}: Missing{refute_either(Here, Earlier, no_here, no_earlier)}

def first_match(-Here: Type, -Earlier: Type, here: Decision<Here>, earlier: Unit -> Decision<Earlier>)
  -> Decision<Or(Here, Earlier)>:
  match here:
    case Found{evidence}: Found{Inl{evidence}}
    case Missing{no_here}: search_earlier(Here, Earlier, no_here, earlier(Unit{}))

def find(~Q: Data, ~Claim: Q -> T.AttemptEvent<T.Fact> -> T.IterationHistory -> Type,
  ~test: @+query: Q -> @+event: T.AttemptEvent<T.Fact> -> @+earlier: T.IterationHistory -> Decision<Claim(query, event, earlier)>,
  +query: Q, +history: T.IterationHistory) -> Decision<Somewhere(~Q, ~Claim, query, history)>:
  match history:
    case T.Start{}: Missing{impossible => impossible}
    case T.Record{event, earlier}:
      first_match(Claim(query, event, earlier), Somewhere(~Q, ~Claim, query, earlier), test(query, event, earlier),
        _ => find(~Q, ~Claim, ~test, query, earlier))

def truth(+value: Bool) -> Decision<{value == True{} : Bool}>:
  match value:
    case True{}: Found{{==}}
    case False{}: Missing{Logic.false_is_not_true}
