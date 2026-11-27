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

def reductio(
  -A: Type,
  eliminate: ((A -> Empty) -> Empty) -> A,
  burden: (A -> Empty) -> Empty
) -> A:
  eliminate(burden)

def IsTrue(flag: Bool) -> Data:
  match flag:
    case True{}:
      Unit
    case False{}:
      Empty

def false_is_not_true(equal: {False{} == True{}: Bool}) -> Empty:
  %Equal.sym(Bool, False{}, True{}, equal): IsTrue(_)
  Unit{}
