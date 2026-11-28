import Base
import ./types.bend as T
import ./iteration/history.bend as History
import ./iteration/evidence.bend as Evidence
import ./GNS005.bend as GNS005
import ./logic.bend as Logic
import ./reasoning/iteration.bend as Derivation

def attempt() -> T.Attempt:
  T.AttemptKey{7n, 1n}

def plan(key: T.Attempt, decision: Nat) -> T.AttemptEvent<T.Fact>:
  +source: T.Source = T.ParserCase{"v1", "[1,]"}
  claim: T.PremiseClaim = T.Claim{2n, source, T.Predict{T.Rejected{}}}
  T.Entry{key, T.Dependency{T.Action{decision}, T.Premise{claim}}}

def response(key: T.Attempt, input: String, actual: T.ParseOutcome) -> T.AttemptEvent<T.Fact>:
  T.Entry{key, T.Reading{T.ParserCase{"v1", input}, actual}}

def planned(key: T.Attempt, decision: Nat) -> T.IterationHistory:
  T.Record{plan(key, decision), T.Start{}}

def found(-Claim: Type, result: History.Decision<Claim>) -> Bool:
  match result:
    case History.Found{_}: True{}
    case History.Missing{_}: False{}

def prepared(+history: T.IterationHistory) -> Bool:
  +iteration: T.Iteration = T.Prepare{attempt(), 17n}
  found(Evidence.Prepared(iteration, history), GNS005.theorem(iteration, history))

def naming_the_decision_is_insufficient()
  -> {prepared(T.Start{}) == False{} : Bool}:
  {==}

def a_named_iteration_can_satisfy_the_premises_while_tinkering() -> Logic.Iff(Empty, Empty):
  iteration: T.Iteration = T.Prepare{attempt(), 17n}
  Derivation.fork_loaded_iteration(T.Iteration, Unit, Empty, Unit, Empty,
    _ => Unit{},
    _ => Inr{(Unit{}, impossible => impossible)},
    _ => loading => loading,
    _ => _ => justified => justified,
    iteration)

def loading_model(+decision: Nat) -> Logic.Iff(Unit, Nat):
  Derivation.fork_loaded_iteration(T.Iteration, Unit, Nat, Empty, Unit,
    _ => Unit{},
    _ => Inl{(decision, impossible => impossible)},
    _ => _ => Unit{},
    _ => no_loading => _ => no_loading(decision),
    T.Prepare{attempt(), decision})

def justification_recovers_the_fork_witness(+decision: Nat)
  -> {Pair.fst(Unit -> Nat, Nat -> Unit, loading_model(decision), Unit{}) == decision : Nat}:
  {==}

def either_parser_answer_informs_the_decision(actual: T.ParseOutcome)
  -> {prepared(T.Record{response(attempt(), "[1,]", actual), planned(attempt(), 17n)}) == True{} : Bool}:
  {==}

def an_unanswered_prediction_stays_open()
  -> {prepared(planned(attempt(), 17n)) == False{} : Bool}:
  {==}

def a_response_needs_an_earlier_dependency()
  -> {prepared(T.Record{plan(attempt(), 17n), T.Record{response(attempt(), "[1,]", T.Accepted{}), T.Start{}}}) == False{} : Bool}:
  {==}

def a_different_parser_input_leaves_the_question_open()
  -> {prepared(T.Record{response(attempt(), "[]", T.Rejected{}), planned(attempt(), 17n)}) == False{} : Bool}:
  {==}

def an_empty_test_suite_cannot_answer_the_parser_question()
  -> {prepared(T.Record{T.Entry{attempt(), T.Reading{T.TestSuite{"run-1", ".", "test_parser.py"}, False{}}},
    planned(attempt(), 17n)}) == False{} : Bool}:
  {==}

def another_decisions_dependency_leaves_the_question_open()
  -> {prepared(T.Record{response(attempt(), "[1,]", T.Accepted{}), planned(attempt(), 18n)}) == False{} : Bool}:
  {==}

def a_different_attempts_response_leaves_the_question_open()
  -> {prepared(T.Record{response(T.AttemptKey{7n, 2n}, "[1,]", T.Accepted{}), planned(attempt(), 17n)}) == False{} : Bool}:
  {==}

def a_different_actions_plan_leaves_the_question_open()
  -> {prepared(T.Record{response(attempt(), "[1,]", T.Accepted{}), planned(T.AttemptKey{8n, 1n}, 17n)}) == False{} : Bool}:
  {==}

def unrelated_records_preserve_a_matching_pair()
  -> {prepared(T.Record{response(attempt(), "[]", T.Rejected{}), T.Record{response(attempt(), "[1,]", T.Accepted{}),
    T.Record{plan(attempt(), 18n), planned(attempt(), 17n)}}}) == True{} : Bool}:
  {==}
