import Base
import ../../../docs/proofs/types.bend as T
import ./report.bend as Report
import ./observer.bend as Observer

# The observer writes a fresh run ID only after unittest returns a result.
def checked_run(directory: String, pattern: String, run_id: String, passed: Bool) -> IO(Unit):
  source: T.Source = T.TestSuite{run_id, directory, pattern}
  Report.check(source, Report.CheckPrediction{T.Predict{True{}}}, T.Returned{passed})

def read_result(directory: String, pattern: String, code: U32, lines: List<&2, String>) -> IO(Unit):
  match code lines:
    case 0 SCon{first, rest} <> Nil{}:
      checked_run(directory, pattern, SCon{first, rest}, True{})
    case 1 SCon{first, rest} <> Nil{}:
      checked_run(directory, pattern, SCon{first, rest}, False{})
    case _ _:
      Report.unavailable("unittest did not return a completed run")

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
      "python3", ["-I", "-B", Observer.path(program, "observe_suite.py"), directory, pattern], "", 2097152, 120000)
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
