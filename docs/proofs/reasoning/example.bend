import Base
import ../types.bend as T
import ./observation.bend as Obs

# One observed result answers two different predictions about the same suite.
def main() -> T.Verdict & (T.Verdict & T.Verdict):
  +source: T.Source = T.TestSuite{"run-17", ".", "parser_test.py"}
  +observation: T.Observation<source> = T.Returned{True{}}
  predicts_pass = Obs.check(source, T.Predict{True{}}, observation)
  predicts_no_pass = Obs.check(source, T.Predict{False{}}, observation)
  prediction_alone = Obs.check(source, T.Predict{True{}}, T.NoResponse{})
  (predicts_pass, (predicts_no_pass, prediction_alone))

def expected() -> {
  main() == (T.Supported{}, (T.Contradicted{}, T.Undecided{})): T.Verdict & (T.Verdict & T.Verdict)
}:
  {==}
