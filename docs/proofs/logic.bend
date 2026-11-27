import Base

type Conj<-A: Type, -B: Type> is Type:
  Conjunction{left: A, right: B}

type Disj<-A: Type, -B: Type> is Type:
  DisjunctionLeft{value: A}
  DisjunctionRight{value: B}

type Iff<-A: Type, -B: Type> is Type:
  Equivalence{forward: A -> B, backward: B -> A}

type Xor<-A: Type, -B: Type> is Type:
  ExclusiveLeft{value: A, excludes: B -> Empty}
  ExclusiveRight{value: B, excludes: A -> Empty}

def IsTrue(flag: Bool) -> Data:
  match flag:
    case True{}:
      Unit
    case False{}:
      Empty

def false_is_not_true(equal: {False{} == True{}: Bool}) -> Empty:
  %Equal.sym(Bool, False{}, True{}, equal): IsTrue(_)
  Unit{}

# A successful check gives a witness for Claim, and any witness makes the check pass.
def Agreement(+result: Bool, -Claim: Type) -> Type:
  Iff<{result == True{} : Bool}, Claim>

def SubjectAgrees(-S: Data, check: S -> Bool, Claim: S -> Type, +subject: S) -> Type:
  Agreement(check(subject), Claim(subject))

def agreement_sound(-result: Bool, -P: Type, agreement: Agreement(result, P)) -> {result == True{} : Bool} -> P:
  Equivalence{sound, _} = agreement
  sound

def agreement_complete(-result: Bool, -P: Type, agreement: Agreement(result, P)) -> P -> {result == True{} : Bool}:
  Equivalence{_, complete} = agreement
  complete

def false_agrees_with_empty() -> Agreement(False{}, Empty):
  Equivalence{false_is_not_true, impossible => Empty.absurd({False{} == True{} : Bool}, impossible)}
