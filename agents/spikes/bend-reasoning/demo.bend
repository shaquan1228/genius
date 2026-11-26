import Base
import ./evidence.bend as Evidence

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print("Derived claim: " ++ Bool.show(Evidence.validated(Evidence.Derived{})))
    IO.print("Directed claim: " ++ Bool.show(Evidence.validated(Evidence.Directed{})))
    IO.print("Dependent observation: " ++ Bool.show(Evidence.validated(Evidence.Observed{False{}, True{}})))
    IO.print("Unconfirmed observation: " ++ Bool.show(Evidence.validated(Evidence.Observed{True{}, False{}})))
    IO.print("Independent confirmation: " ++ Bool.show(Evidence.validated(Evidence.admit(Evidence.Observed{True{}, True{}}, {==}))))
