import Base
import ../types.bend as T
import ../reasoning/history.bend as Readings
import ./history.bend as History

type Reading is Data:
  Result{iteration: T.Iteration, source: T.Source, actual: T.Answer(source)}

def answers_dependency(reading: Reading, event: T.AttemptEvent<T.Fact>) -> Bool:
  Result{T.Prepare{attempt, decision}, +recorded, actual} = reading
  T.Entry{key, fact} = event
  match fact:
    case T.Dependency{T.Action{action}, T.Premise{T.Claim{_, +source, _}}}:
      same_decision = Bool.and(T.same_attempt(attempt, key), Nat.is_eq(decision, action))
      observation = Readings.reading(source, recorded, actual)
      Bool.and(same_decision, T.received(source, observation))
    case _: False{}

def Dependency(reading: Reading, event: T.AttemptEvent<T.Fact>, older: T.IterationHistory) -> Type:
  {answers_dependency(reading, event) == True{} : Bool}

def dependency(+reading: Reading, +event: T.AttemptEvent<T.Fact>, +older: T.IterationHistory)
  -> History.Decision<Dependency(reading, event, older)>:
  History.truth(answers_dependency(reading, event))

def reading_for(iteration: T.Iteration, event: T.AttemptEvent<T.Fact>) -> Maybe<&2, Reading>:
  match iteration event:
    case T.Prepare{+attempt, decision} T.Entry{key, T.Reading{+source, actual}}:
      reading: Reading = Result{T.Prepare{attempt, decision}, source, actual}
      Bool.pick(Maybe<&2, Reading>, T.same_attempt(attempt, key), Some{reading}, None{})
    case _ _: None{}

def PriorDependency(reading: Maybe<&2, Reading>, earlier: T.IterationHistory) -> Type:
  match reading:
    case None{}: Empty
    case Some{result}: History.Somewhere(~Reading, ~Dependency, result, earlier)

def prior_dependency(+reading: Maybe<&2, Reading>, +earlier: T.IterationHistory)
  -> History.Decision<PriorDependency(reading, earlier)>:
  match reading:
    case None{}: History.Missing{impossible => impossible}
    case Some{result}: History.find(~Reading, ~Dependency, ~dependency, result, earlier)

def AtReading(iteration: T.Iteration, event: T.AttemptEvent<T.Fact>, earlier: T.IterationHistory) -> Type:
  PriorDependency(reading_for(iteration, event), earlier)

def at_reading(+iteration: T.Iteration, +event: T.AttemptEvent<T.Fact>, +earlier: T.IterationHistory)
  -> History.Decision<AtReading(iteration, event, earlier)>:
  prior_dependency(reading_for(iteration, event), earlier)

def Prepared(+iteration: T.Iteration, history: T.IterationHistory) -> Type:
  History.Somewhere(~T.Iteration, ~AtReading, iteration, history)
