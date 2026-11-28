import Base
import ../../../docs/proofs/types.bend as T
import ../../../docs/proofs/reasoning/observation.bend as Obs

# The runner asks one of two questions of the same observation.
type Question<-source: T.Source> is Data:
  DidRespond{}
  CheckPrediction{hypothesis: T.Hypothesis<source>}

def result(message: String, code: U32) -> IO(Unit):
  do IO<Unit>:
    written: Unit <- IO.print(message)
    IO.exit(code)

def unavailable(detail: String) -> IO(Unit):
  do IO<Unit>:
    logged: Unit <- IO.print_err(detail)
    result("unavailable", 2)

def decision(verdict: T.Verdict) -> IO(Unit):
  match verdict:
    case T.Supported{}:
      result("supported", 0)
    case T.Contradicted{}:
      result("contradicted", 1)
    case T.Undecided{}:
      result("undecided", 2)

def response(recorded: Bool) -> IO(Unit):
  match recorded:
    case True{}:
      result("observed", 0)
    case False{}:
      decision(T.Undecided{})

def check(+source: T.Source, question: Question<source>, observation: T.Observation<source>) -> IO(Unit):
  match question:
    case DidRespond{}:
      response(T.received(source, observation))
    case CheckPrediction{hypothesis}:
      decision(Obs.check(source, hypothesis, observation))
