import Base

type ParseOutcome is Data:
  Accepted{}
  Rejected{}

type Source is Data:
  CommittedFile{commit: String, path: String}
  TestSuite{run_id: String, directory: String, pattern: String}
  ParserCase{parser_version: String, input: String}

def Answer(source: Source) -> Data:
  match source:
    case CommittedFile{_, _}:
      Maybe<&2, String>
    case TestSuite{_, _, _}:
      Bool
    case ParserCase{_, _}:
      ParseOutcome

# The source is part of both types. A result for one source cannot be used
# with a prediction about another. The CLI reads the actual value at its source.
type Hypothesis<-source: Source> is Data:
  Predict{expected: Answer(source)}

type Observation<-source: Source> is Data:
  NoResponse{}
  Returned{actual: Answer(source)}

type Verdict is Data:
  Supported{}
  Contradicted{}
  Undecided{}

def received(-source: Source, observation: Observation<source>) -> Bool:
  match observation:
    case NoResponse{}:
      False{}
    case Returned{_}:
      True{}

type Attempt is Data:
  AttemptKey{action: Nat, number: Nat}

type Phase is Data:
  Observed{facts: String, signals: String, constraints: String}
  Oriented{}
  Decided{}
  Acted{}

type TraceEvent is Data:
  Entry{key: Attempt, phase: Phase}

type PremiseClaim is Data:
  Claim{number: Nat, source: Source, hypothesis: Hypothesis<source>}

type Subject is Data:
  Action{number: Nat}
  Premise{claim: PremiseClaim}
  Output{loop: Nat, number: Nat}

type Fact is Data:
  Dependency{dependent: Subject, prerequisite: Subject}
  Reading{source: Source, actual: Answer(source)}
  ExternalLoop{actor: Nat, loop: Nat}
  Observable{actor: Nat, output: Subject}
  DefaultEstablished{premise: PremiseClaim}
  CascadeOccurred{action: Nat, premise: PremiseClaim}

type Intervention is Data:
  Probe{output: Subject}
  Signal{output: Subject}
  SafeguardInstalled{premise: PremiseClaim}
  NoIntervention{}
  OtherIntervention{}

type Context<-S: Data> is Data:
  Frame{
    actor: Nat,
    subject: S,
    before: List<&2, Fact>,
    after: List<&2, Fact>,
    intervention: Intervention
  }

type ActionUse is Data:
  Use{action: Nat, premise: PremiseClaim, viable_approaches: Nat, uncertain: Bool}

type ExternalUse is Data:
  UseOutput{use: ActionUse, loop: Nat, output: Nat}
