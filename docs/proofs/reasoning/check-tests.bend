import Base
import ../types.bend as T
import ./report.bend as Report

# Resolve the observer from the installed checker, independent of the test checkout.
def observer_path(program: String) -> String:
  parts = List.reverse(&2, String, String.split(program, '/'))
  parents = List.drop(&2, String, parts, 1n)
  directory = String.join(List.reverse(&2, String, parents), "/")
  directory ++ "/../../../skills/reasoning/scripts/observe_suite.py"

def check_count(
  +run_id: String, directory: String, pattern: String, code: U32, count: String, complete: Bool
) -> IO(Unit):
  match complete:
    case False{}:
      Report.unavailable("unittest did not return a run ID and passing-test count")
    case True{}:
      passed = Bool.and(U32.is_eq(code, 0), Bool.not(String.starts_with(count, "0")))
      source: T.Source = T.TestSuite{run_id, directory, pattern}
      Report.check(source, T.CheckPrediction{T.Predict{True{}}}, T.Returned{passed})

def read_result(directory: String, pattern: String, +code: U32, lines: List<&2, String>) -> IO(Unit):
  match lines:
    case +run_id <> +count <> Nil{}:
      valid_id = Bool.not(String.is_empty(run_id))
      digits = List.all(&2, Char, Char.is_digit, String.to_list(count))
      valid_count = Bool.and(digits, Bool.not(String.is_empty(count)))
      complete = Bool.and(U32.is_le(code, 1), Bool.and(valid_id, valid_count))
      check_count(run_id, directory, pattern, code, count, complete)
    case other:
      Report.unavailable("unittest did not return a run ID and passing-test count")

def report(directory: String, pattern: String,
  answer: Result<&1, &1, U32 & String, U32 & (String & String)>) -> IO(Unit):
  match answer:
    case Done{(code, (stdout, stderr))}:
      do IO<Unit>:
        logged: Unit <- IO.print_err(stderr)
        read_result(directory, pattern, code, String.lines(String.trim(stdout)))
    case Fail{(_, detail)}:
      Report.unavailable(detail)

def run(program: String, +directory: String, +pattern: String) -> IO(Unit):
  do IO<Unit>:
    answer: Result<&1, &1, U32 & String, U32 & (String & String)> <- Process.run(
      "python3", ["-I", "-B", observer_path(program), directory, pattern], "", 2097152, 120000)
    report(directory, pattern, answer)

def arguments(args: List<String>) -> IO(Unit):
  match args:
    case program <> directory <> pattern <> Nil{}:
      run(program, directory, pattern)
    case other:
      Report.unavailable("expected a suite directory and a discovery pattern")

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    arguments(args)
