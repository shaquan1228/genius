import Base
import ./main.bend as Model

def Member(-A: Data, +wanted: A, items: List<&2, A>) -> Data:
  match items:
    case Nil{}:
      Empty
    case head <> tail:
      Either<&2, &2, {wanted == head : A}, Member(A, wanted, tail)>

def Predicates.NonTrivial(viable_approaches: Nat, uncertain: Bool) -> Data:
  Either<&2, &2, {Nat.is_lt(1n, viable_approaches) == True{} : Bool}, {uncertain == True{} : Bool}>

def Predicates.ValidatedAt(premise: Nat, state: List<&2, Model.Fact>) -> Data:
  Member(Model.Fact, Model.Confirmation{premise, Model.Direct{}}, state)

def Predicates.DependsAt(dependent: Model.Subject, prerequisite: Model.Subject,
  state: List<&2, Model.Fact>) -> Data:
  Member(Model.Fact, Model.Dependency{dependent, prerequisite}, state)

def Predicates.PremiseRequiredBefore(ctx: Model.Context<Model.ActionUse>) -> Type:
  match ctx:
    case Model.Frame{actor, Model.Use{action, premise, approaches, uncertain}, before, after, intervention}:
      (Predicates.NonTrivial(approaches, uncertain) &
        Predicates.DependsAt(Model.Action{action}, Model.Premise{premise}, before))

def Predicates.ValidatedBefore(ctx: Model.Context<Model.ActionUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.Use{action, premise, approaches, uncertain}, before, after, intervention}:
      Predicates.ValidatedAt(premise, before)

def Predicates.ValidatedAfter(ctx: Model.Context<Model.ExternalUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Predicates.ValidatedAt(premise, after)

def Predicates.ExternalDependency(ctx: Model.Context<Model.ExternalUse>) -> Type:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      (Predicates.DependsAt(Model.Premise{premise}, Model.Output{loop, output}, before) &
        Member(Model.Fact, Model.ExternalLoop{actor, loop}, before))

def Predicates.Probed(ctx: Model.Context<Model.ExternalUse>) -> Type:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{use, loop, output}, before, after, intervention}:
      {intervention == Model.Probe{Model.Output{loop, output}} : Model.Intervention}

def Predicates.Signaled(ctx: Model.Context<Model.ExternalUse>) -> Type:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{use, loop, output}, before, after, intervention}:
      {intervention == Model.Signal{Model.Output{loop, output}} : Model.Intervention}

def Predicates.Enforcement(ctx: Model.Context<Model.ExternalUse>) -> Type:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      {intervention == Model.SafeguardInstalled{premise} : Model.Intervention}

def Predicates.ObservableBefore(ctx: Model.Context<Model.ExternalUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{use, loop, output}, before, after, intervention}:
      Member(Model.Fact, Model.Observable{actor, Model.Output{loop, output}}, before)

def Predicates.DefaultEstablishedAfter(ctx: Model.Context<Model.ExternalUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Member(Model.Fact, Model.DefaultEstablished{premise}, after)

def Predicates.OutputDependencyAfter(ctx: Model.Context<Model.ExternalUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Predicates.DependsAt(Model.Premise{premise}, Model.Output{loop, output}, after)

def Predicates.CascadeRecordedAfter(ctx: Model.Context<Model.ExternalUse>) -> Data:
  match ctx:
    case Model.Frame{actor, Model.UseOutput{Model.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Member(Model.Fact, Model.CascadeOccurred{action, premise}, after)

type Predicates.EnforcementEffects<-ctx: Model.Context<Model.ExternalUse>> is Type:
  Effects{
    default_established: Predicates.DefaultEstablishedAfter(ctx),
    output_dependency_removed: Predicates.OutputDependencyAfter(ctx) -> Empty,
    validated: Predicates.ValidatedAfter(ctx),
    no_cascade: Predicates.CascadeRecordedAfter(ctx) -> Empty
  }

type Premises.Forward<-ctx: Model.Context<Model.ExternalUse>> is Type:
  Forward{
    external_dependency: Predicates.ExternalDependency(ctx),
    signal_cannot_validate: Predicates.Signaled(ctx) -> Predicates.ValidatedAfter(ctx) -> Empty,
    classify_validation: Predicates.ExternalDependency(ctx) -> Predicates.ValidatedAfter(ctx) ->
      Or(Predicates.Probed(ctx), Or(Predicates.Signaled(ctx), Predicates.Enforcement(ctx))),
    probe_requires_observability: Predicates.Probed(ctx) -> Predicates.ObservableBefore(ctx),
    future_output_unobservable: Predicates.ObservableBefore(ctx) -> Empty
  }

type Premises.Enforcement<-ctx: Model.Context<Model.ExternalUse>> is Type:
  EnforcementPremises{
    action_requires_premise: Predicates.PremiseRequiredBefore(Model.action_context(ctx)),
    forward: Premises.Forward<ctx>,
    effects: Predicates.Enforcement(ctx) -> Predicates.EnforcementEffects<ctx>
  }
