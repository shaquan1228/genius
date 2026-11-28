import Base

def Iff(-A: Type, -B: Type) -> Type:
  (A -> B) & (B -> A)

def Xor(-A: Type, -B: Type) -> Type:
  Or(A & (B -> Empty), B & (A -> Empty))

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
  Iff({result == True{} : Bool}, Claim)

def SubjectAgrees(-S: Data, check: S -> Bool, Claim: S -> Type, +subject: S) -> Type:
  Agreement(check(subject), Claim(subject))

def agreement_sound(-result: Bool, -Claim: Type, agreement: Agreement(result, Claim)) -> {result == True{} : Bool} -> Claim:
  (sound, _) = agreement
  sound

def agreement_complete(-result: Bool, -Claim: Type, agreement: Agreement(result, Claim)) -> Claim -> {result == True{} : Bool}:
  (_, complete) = agreement
  complete

def false_agrees_with_empty() -> Agreement(False{}, Empty):
  (false_is_not_true, impossible => Empty.absurd({False{} == True{} : Bool}, impossible))
