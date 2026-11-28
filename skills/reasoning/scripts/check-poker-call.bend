import Base
import ../../../docs/proofs/reasoning/observation.bend as Obs
import ./report.bend as Report

def report(valid: Bool, +amount: Nat, expected: Nat) -> IO(Unit):
  match valid:
    case True{}:
      do IO<Unit>:
        logged: Unit <- IO.print_err(String.append("Amount to match (hundredths): ", Nat.show(amount)))
        Report.decision(Obs.verdict(Nat.is_eq(amount, expected)))
    case False{}:
      Report.unavailable("The street commitment exceeds the current wager.")

def check(wager: Maybe<&2, Nat>, committed: Maybe<&2, Nat>, expected: Maybe<&2, Nat>) -> IO(Unit):
  match wager committed expected:
    case Some{+street_wager} Some{+contribution} Some{prediction}:
      report(Nat.is_ge(street_wager, contribution), Nat.sub(street_wager, contribution), prediction)
    case _ _ _:
      Report.unavailable("Expected a wager, street commitment, and prediction in hundredths.")

def arguments(args: List<String>) -> IO(Unit):
  match args:
    case _ <> wager <> committed <> expected <> Nil{}:
      check(Nat.read(wager), Nat.read(committed), Nat.read(expected))
    case _:
      Report.unavailable("Expected three arguments in hundredths.")

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    arguments(args)
