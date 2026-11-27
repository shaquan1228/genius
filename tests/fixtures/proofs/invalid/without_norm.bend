import Base
import ./logic.bend as Logic
import ./reasoning/PROOF.bend as Reasoning

def bad() -> (Empty -> Empty) -> Empty:
  Reasoning.validation_burden(Unit, Unit, Unit, Unit, Empty, Unit, Unit,
    n => n, o => o, classified => Unit{}, assumed => Unit{}, risk => risk,
    Logic.Conjunction{Unit{}, Unit{}})
