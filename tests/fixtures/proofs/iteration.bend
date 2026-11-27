import Base
import ./types.bend as T
import ./iteration/history.bend as History
import ./iteration/evidence.bend as Evidence
import ./GNS005.bend as GNS005

def attempt() -> T.Attempt:
  T.AttemptKey{7n, 1n}

def plan(key: T.Attempt, decision: Nat) -> T.AttemptEvent<T.Fact>:
  +source: T.Source = T.ParserCase{"v1", "[1,]"}
  claim: T.PremiseClaim = T.Claim{2n, source, T.Predict{T.Rejected{}}}
  T.Entry{key, T.Dependency{T.Action{decision}, T.Premise{claim}}}

def response(key: T.Attempt, input: String, actual: T.ParseOutcome) -> T.AttemptEvent<T.Fact>:
  T.Entry{key, T.Reading{T.ParserCase{"v1", input}, actual}}

def found(-Claim: Type, result: History.Decision<Claim>) -> Bool:
  match result:
    case History.Found{_}: True{}
    case History.Missing{_}: False{}

def prepared(+history: T.IterationHistory) -> Bool:
  +iteration: T.Iteration = T.Prepare{attempt(), 17n}
  found(Evidence.Prepared(iteration, history), GNS005.theorem(iteration, history))

def either_parser_answer_informs_the_decision(actual: T.ParseOutcome)
  -> {prepared([response(attempt(), "[1,]", actual), plan(attempt(), 17n)]) == True{} : Bool}:
  {==}

def an_unanswered_prediction_stays_open()
  -> {prepared([plan(attempt(), 17n)]) == False{} : Bool}:
  {==}

def a_response_needs_an_earlier_dependency()
  -> {prepared([plan(attempt(), 17n), response(attempt(), "[1,]", T.Accepted{})]) == False{} : Bool}:
  {==}

def a_different_parser_input_leaves_the_question_open()
  -> {prepared([response(attempt(), "[]", T.Rejected{}), plan(attempt(), 17n)]) == False{} : Bool}:
  {==}

def another_decisions_dependency_leaves_the_question_open()
  -> {prepared([response(attempt(), "[1,]", T.Accepted{}), plan(attempt(), 18n)]) == False{} : Bool}:
  {==}

def a_different_attempts_response_leaves_the_question_open()
  -> {prepared([response(T.AttemptKey{7n, 2n}, "[1,]", T.Accepted{}), plan(attempt(), 17n)]) == False{} : Bool}:
  {==}

def a_different_actions_plan_leaves_the_question_open()
  -> {prepared([response(attempt(), "[1,]", T.Accepted{}), plan(T.AttemptKey{8n, 1n}, 17n)]) == False{} : Bool}:
  {==}

def unrelated_records_preserve_a_matching_pair()
  -> {prepared([response(attempt(), "[]", T.Rejected{}), response(attempt(), "[1,]", T.Accepted{}),
    plan(attempt(), 18n), plan(attempt(), 17n)]) == True{} : Bool}:
  {==}
