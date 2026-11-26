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
