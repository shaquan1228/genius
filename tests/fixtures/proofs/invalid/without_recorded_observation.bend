import Base
import ./types.bend as T
import ./GNS001.bend as GNS001

def bad() -> Empty:
  GNS001.theorem(2n, False{}, T.AttemptKey{1n, 1n}, T.Start{}, Inl{{==}}, {==})
