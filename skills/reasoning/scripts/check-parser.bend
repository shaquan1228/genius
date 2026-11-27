import Base
import ../../../docs/proofs/types.bend as T
import ../../../docs/proofs/reasoning/main.bend as Model
import ./observer.bend as Observer
import ./report.bend as Report

type Request is Data:
  Parse{input: String, expected: T.ParseOutcome, version: Maybe<&2, String>}

def outcome(text: String) -> Maybe<&2, T.ParseOutcome>:
  match text:
    case "accepted": Some{T.Accepted{}}
    case "rejected": Some{T.Rejected{}}
    case _: None{}

def checked_case(request: Request, +observed_version: String, answer: Maybe<&2, T.ParseOutcome>) -> IO(Unit):
  match request answer:
    case Parse{+input, expected, version} Some{actual}:
      asked: T.Source = T.ParserCase{Maybe.default(&2, String, version, observed_version), input}
      observed: T.Source = T.ParserCase{observed_version, input}
      do IO<Unit>:
        logged: Unit <- IO.print_err(observed_version)
        Report.decision(Model.verdict(asked, T.Predict{expected}, [T.Reading{observed, actual}]))
    case _ None{}: Report.unavailable("parser returned an unknown outcome")

def report(request: Request, lines: List<&2, String>) -> IO(Unit):
  match lines:
    case SCon{first, rest} <> result <> Nil{}:
      checked_case(request, SCon{first, rest}, outcome(result))
    case _: Report.unavailable("parser did not report its version and outcome")

def completed(request: Request, answer: Result<&1, &1, U32 & String, U32 & (String & String)>) -> IO(Unit):
  match answer:
    case Done{(0, (stdout, _))}: report(request, String.lines(String.trim(stdout)))
    case Done{(_, (_, stderr))}: Report.unavailable(stderr)
    case Fail{(_, detail)}: Report.unavailable(detail)

def run(program: String, +input: String, expected: Maybe<&2, T.ParseOutcome>, version: Maybe<&2, String>) -> IO(Unit):
  match expected:
    case Some{prediction}:
      do IO<Unit>:
        answer: Result<&1, &1, U32 & String, U32 & (String & String)> <-
          Process.run("python3", ["-I", "-B", Observer.path(program, "observe_json.py")], input, 8192, 10000)
        completed(Parse{input, prediction, version}, answer)
    case None{}: Report.unavailable("expected accepted or rejected")

def arguments(args: List<String>) -> IO(Unit):
  match args:
    case program <> input <> expected <> Nil{}: run(program, input, outcome(expected), None{})
    case program <> input <> expected <> version <> Nil{}: run(program, input, outcome(expected), Some{version})
    case _: Report.unavailable("expected the input, predicted outcome, and optionally the parser version")

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    arguments(args)
