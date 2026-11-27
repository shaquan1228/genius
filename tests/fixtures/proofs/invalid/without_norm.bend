import Base
import ./reasoning/PROOF.bend as Reasoning

def bad() -> (Empty -> Empty) -> Empty:
  Reasoning.validation_burden(Unit, Unit, Unit, Unit, Empty, Unit, Unit,
    n => n, o => o, classified => unvalidated => Unit{}, dependency => assumed => Unit{}, risk => risk,
    (Unit{}, Unit{}))
