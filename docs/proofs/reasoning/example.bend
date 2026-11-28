import Base
import ../types.bend as T
import ./observation.bend as Obs
import ./main.bend as Model

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

def rejects_trailing_comma(history: List<&2, T.Fact>) -> T.Verdict:
  Model.verdict(T.ParserCase{"v1", "[1,]"}, T.Predict{T.Rejected{}}, history)

def unrelated_results() -> List<&2, T.Fact>:
  [T.Reading{T.TestSuite{"run-17", ".", "parser_test.py"}, False{}},
   T.Reading{T.ParserCase{"v1", "[1]"}, T.Accepted{}},
   T.Reading{T.ParserCase{"v2", "[1,]"}, T.Rejected{}}]

def no_parser_answer() -> {rejects_trailing_comma(unrelated_results()) == T.Undecided{}: T.Verdict}:
  {==}

def observed_rejection() -> {rejects_trailing_comma(
  T.Reading{T.ParserCase{"v2", "[1,]"}, T.Accepted{}} <>
  T.Reading{T.ParserCase{"v1", "[1,]"}, T.Rejected{}} <> Nil{}) == T.Supported{}: T.Verdict}:
  {==}

def observed_acceptance() -> {rejects_trailing_comma(
  T.Reading{T.ParserCase{"v1", "[1,]"}, T.Accepted{}} <>
  T.Reading{T.ParserCase{"v1", "[1,]"}, T.Rejected{}} <> Nil{}) == T.Contradicted{}: T.Verdict}:
  {==}
