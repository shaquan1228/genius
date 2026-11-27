import Base
import ./logic.bend as Logic
import ./GNS004.bend as GNS004

def bad() -> (Empty -> Empty) -> Empty:
  GNS004.validation_burden(Unit, Unit, Unit, Unit, Empty, Unit, Unit,
    n => n, o => o, classified => Unit{}, assumed => Unit{}, risk => risk,
    Logic.Conjunction{Unit{}, Unit{}})
