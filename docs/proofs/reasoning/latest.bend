import Base
import ../logic.bend as Logic
import ../types.bend as T
import ./history.bend as History
import ./observation.bend as Obs

def AtReading(+source: T.Source, hypothesis: T.Hypothesis<source>, response: T.Observation<source>,
  earlier: Data) -> Data:
  match response:
    case T.Returned{actual}: Obs.Evidence(source, hypothesis, T.Returned{actual})
    case T.NoResponse{}: earlier

def AtFact(+source: T.Source, hypothesis: T.Hypothesis<source>, fact: T.Fact, earlier: Data) -> Data:
  match fact:
    case T.Reading{recorded, actual}: AtReading(source, hypothesis, History.reading(source, recorded, actual), earlier)
    case _: earlier

def Evidence(+source: T.Source, +hypothesis: T.Hypothesis<source>, facts: List<&2, T.Fact>) -> Data:
  match facts:
    case Nil{}: Empty
    case head <> tail:
      AtFact(source, hypothesis, head, Evidence(source, hypothesis, tail))

def step_agrees(+source: T.Source, +hypothesis: T.Hypothesis<source>, +current: T.Observation<source>,
  -earlier: T.Observation<source>, -Earlier: Data,
  recurse: Unit -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis, earlier)), Earlier))
  -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis,
    History.first_response(source, current, _ => earlier))), AtReading(source, hypothesis, current, Earlier)):
  match current:
    case T.NoResponse{}: recurse(Unit{})
    case T.Returned{+actual}:
      (Obs.checked_evidence(source, hypothesis, T.Returned{actual}),
        Obs.evidence_supported(source, hypothesis, T.Returned{actual}))

def fact_agrees(+source: T.Source, +hypothesis: T.Hypothesis<source>, +fact: T.Fact,
  -earlier: T.Observation<source>, -Earlier: Data,
  recurse: Unit -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis, earlier)), Earlier))
  -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis,
    History.first_response(source, History.from_fact(source, fact), _ => earlier))),
    AtFact(source, hypothesis, fact, Earlier)):
  match fact:
    case T.Reading{recorded, actual}:
      step_agrees(source, hypothesis, History.reading(source, recorded, actual), earlier, Earlier, recurse)
    case T.Dependency{_, _}: recurse(Unit{})
    case T.ExternalLoop{_, _}: recurse(Unit{})
    case T.Observable{_, _}: recurse(Unit{})
    case T.DefaultEstablished{_}: recurse(Unit{})
    case T.CascadeOccurred{_, _}: recurse(Unit{})

def empty_agrees(+source: T.Source, hypothesis: T.Hypothesis<source>)
  -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis, T.NoResponse{})), Empty):
  match hypothesis:
    case T.Predict{_}: Logic.false_agrees_with_empty()

def lookup_agrees(+source: T.Source, +hypothesis: T.Hypothesis<source>, +facts: List<&2, T.Fact>)
  -> Logic.Agreement(Obs.supported(Obs.check(source, hypothesis, History.answer_to(source, facts))),
    Evidence(source, hypothesis, facts)):
  match facts:
    case Nil{}: empty_agrees(source, hypothesis)
    case head <> tail:
      fact_agrees(source, hypothesis, head, History.answer_to(source, tail),
        Evidence(source, hypothesis, tail), _ => lookup_agrees(source, hypothesis, tail))
