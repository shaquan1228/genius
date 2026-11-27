import Base
import ../logic.bend as Logic
import ../types.bend as T

# None is a factual answer when a completed tree lookup finds no blob.
def same_blob(expected: Maybe<&2, String>, actual: Maybe<&2, String>) -> Bool:
  match expected actual:
    case Some{left} Some{right}:
      String.eq(left, right)
    case None{} None{}:
      True{}
    case other result:
      False{}

def same_outcome(expected: T.ParseOutcome, actual: T.ParseOutcome) -> Bool:
  match expected actual:
    case T.Accepted{} T.Accepted{}: True{}
    case T.Rejected{} T.Rejected{}: True{}
    case _ _: False{}

def agrees(source: T.Source, expected: T.Answer(source), actual: T.Answer(source)) -> Bool:
  match source:
    case T.CommittedFile{_, _}:
      same_blob(expected, actual)
    case T.TestSuite{_, _, _}:
      Cmp.is_eq(Bool.cmp(expected, actual))
    case T.ParserCase{_, _}:
      same_outcome(expected, actual)

def verdict(agreed: Bool) -> T.Verdict:
  match agreed:
    case True{}:
      T.Supported{}
    case False{}:
      T.Contradicted{}

def check(+source: T.Source, hypothesis: T.Hypothesis<source>, observation: T.Observation<source>)
  -> T.Verdict:
  match hypothesis observation:
    case T.Predict{_} T.NoResponse{}:
      T.Undecided{}
    case T.Predict{expected} T.Returned{actual}:
      verdict(agrees(source, expected, actual))

def supported(verdict: T.Verdict) -> Bool:
  match verdict:
    case T.Supported{}:
      True{}
    case other:
      False{}

# The proposition corresponding to a successful check requires a response
# from this source and agreement between its actual and predicted values.
def Evidence(+source: T.Source, hypothesis: T.Hypothesis<source>, observation: T.Observation<source>)
  -> Data:
  match hypothesis observation:
    case T.Predict{_} T.NoResponse{}:
      Empty
    case T.Predict{expected} T.Returned{actual}:
      {agrees(source, expected, actual) == True{}: Bool}

def agreed(flag: Bool, accepted: {supported(verdict(flag)) == True{}: Bool}) -> {flag == True{}: Bool}:
  match flag:
    case True{}:
      {==}
    case False{}:
      accepted

# When the executable check supports a hypothesis, its source returned the expected answer.
def checked_evidence(
  +source: T.Source,
  +hypothesis: T.Hypothesis<source>,
  +observation: T.Observation<source>,
  accepted: {supported(check(source, hypothesis, observation)) == True{}: Bool}
) -> Evidence(source, hypothesis, observation):
  match hypothesis observation:
    case T.Predict{_} T.NoResponse{}:
      Logic.false_is_not_true(accepted)
    case T.Predict{expected} T.Returned{actual}:
      agreed(agrees(source, expected, actual), accepted)

def evidence_supported(+source: T.Source, +hypothesis: T.Hypothesis<source>,
  +observation: T.Observation<source>, evidence: Evidence(source, hypothesis, observation))
  -> {supported(check(source, hypothesis, observation)) == True{}: Bool}:
  match hypothesis observation:
    case T.Predict{_} T.NoResponse{}:
      match evidence:
    case T.Predict{expected} T.Returned{actual}:
      %Equal.sym(Bool, agrees(source, expected, actual), True{}, evidence):
        {supported(verdict(_)) == True{}: Bool}
      {==}
