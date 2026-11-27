import Base

type Subject is Data:
  Action{number: Nat}
  Premise{number: Nat}
  Output{loop: Nat, number: Nat}

type Provenance is Data:
  Direct{}
  Derived{}
  Directed{}

type Fact is Data:
  Dependency{dependent: Subject, prerequisite: Subject}
  Confirmation{premise: Nat, source: Provenance}
  ExternalLoop{actor: Nat, loop: Nat}
  Observable{actor: Nat, output: Subject}
  DefaultEstablished{premise: Nat}
  CascadeOccurred{action: Nat, premise: Nat}

type Intervention is Data:
  Probe{output: Subject}
  Signal{output: Subject}
  SafeguardInstalled{premise: Nat}
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
  Use{action: Nat, premise: Nat, viable_approaches: Nat, uncertain: Bool}

type ExternalUse is Data:
  UseOutput{use: ActionUse, loop: Nat, output: Nat}

def action_context(ctx: Context<ExternalUse>) -> Context<ActionUse>:
  match ctx:
    case Frame{actor, UseOutput{use, _, _}, before, after, intervention}:
      Frame{actor, use, before, after, intervention}

def confirmation_matches(premise: Nat, fact: Fact) -> Bool:
  match fact:
    case Confirmation{confirmed, Direct{}}:
      Nat.is_eq(premise, confirmed)
    case other:
      False{}

def has_direct_confirmation(+premise: Nat, facts: List<&2, Fact>) -> Bool:
  match facts:
    case Nil{}:
      False{}
    case head <> tail:
      List.any.if(_ => has_direct_confirmation(premise, tail), confirmation_matches(premise, head))

def premise_gate(ctx: Context<ActionUse>) -> Bool:
  match ctx:
    case Frame{_, Use{_, premise, _, _}, before, _, _}:
      has_direct_confirmation(premise, before)

def main() -> Bool:
  premise_gate(
    Frame{
      1n,
      Use{2n, 3n, 2n, False{}},
      Confirmation{3n, Direct{}} <> Nil{},
      Nil{},
      NoIntervention{}
    }
  )
