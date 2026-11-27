import Base
import ../types.bend as T
import ./main.bend as Model

def Member(-A: Data, +wanted: A, items: List<&2, A>) -> Data:
  match items:
    case Nil{}:
      Empty
    case head <> tail:
      Either<&2, &2, {wanted == head : A}, Member(A, wanted, tail)>

def Predicates.NonTrivial(viable_approaches: Nat, uncertain: Bool) -> Data:
  Either<&2, &2, {Nat.is_lt(1n, viable_approaches) == True{} : Bool}, {uncertain == True{} : Bool}>

def Predicates.ValidatedAt(premise: Nat, state: List<&2, T.Fact>) -> Data:
  Member(T.Fact, T.Confirmation{premise, T.Direct{}}, state)

def Predicates.DependsAt(dependent: T.Subject, prerequisite: T.Subject,
  state: List<&2, T.Fact>) -> Data:
  Member(T.Fact, T.Dependency{dependent, prerequisite}, state)

def Predicates.PremiseRequiredBefore(ctx: T.Context<T.ActionUse>) -> Type:
  match ctx:
    case T.Frame{actor, T.Use{action, premise, approaches, uncertain}, before, after, intervention}:
      (Predicates.NonTrivial(approaches, uncertain) &
        Predicates.DependsAt(T.Action{action}, T.Premise{premise}, before))

def Predicates.ValidatedBefore(ctx: T.Context<T.ActionUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.Use{action, premise, approaches, uncertain}, before, after, intervention}:
      Predicates.ValidatedAt(premise, before)

def Predicates.ValidatedAfter(ctx: T.Context<T.ExternalUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Predicates.ValidatedAt(premise, after)

def Predicates.ExternalDependency(ctx: T.Context<T.ExternalUse>) -> Type:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      (Predicates.DependsAt(T.Premise{premise}, T.Output{loop, output}, before) &
        Member(T.Fact, T.ExternalLoop{actor, loop}, before))

def Predicates.Probed(ctx: T.Context<T.ExternalUse>) -> Type:
  match ctx:
    case T.Frame{actor, T.UseOutput{use, loop, output}, before, after, intervention}:
      {intervention == T.Probe{T.Output{loop, output}} : T.Intervention}

def Predicates.Signaled(ctx: T.Context<T.ExternalUse>) -> Type:
  match ctx:
    case T.Frame{actor, T.UseOutput{use, loop, output}, before, after, intervention}:
      {intervention == T.Signal{T.Output{loop, output}} : T.Intervention}

def Predicates.Enforcement(ctx: T.Context<T.ExternalUse>) -> Type:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      {intervention == T.SafeguardInstalled{premise} : T.Intervention}

def Predicates.ObservableBefore(ctx: T.Context<T.ExternalUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.UseOutput{use, loop, output}, before, after, intervention}:
      Member(T.Fact, T.Observable{actor, T.Output{loop, output}}, before)

def Predicates.DefaultEstablishedAfter(ctx: T.Context<T.ExternalUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Member(T.Fact, T.DefaultEstablished{premise}, after)

def Predicates.OutputDependencyAfter(ctx: T.Context<T.ExternalUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Predicates.DependsAt(T.Premise{premise}, T.Output{loop, output}, after)

def Predicates.CascadeRecordedAfter(ctx: T.Context<T.ExternalUse>) -> Data:
  match ctx:
    case T.Frame{actor, T.UseOutput{T.Use{action, premise, approaches, uncertain}, loop, output}, before, after, intervention}:
      Member(T.Fact, T.CascadeOccurred{action, premise}, after)

type Predicates.EnforcementEffects<-ctx: T.Context<T.ExternalUse>> is Type:
  Effects{
    default_established: Predicates.DefaultEstablishedAfter(ctx),
    output_dependency_removed: Predicates.OutputDependencyAfter(ctx) -> Empty,
    validated: Predicates.ValidatedAfter(ctx),
    no_cascade: Predicates.CascadeRecordedAfter(ctx) -> Empty
  }

type Premises.Forward<-ctx: T.Context<T.ExternalUse>> is Type:
  Forward{
    external_dependency: Predicates.ExternalDependency(ctx),
    signal_cannot_validate: Predicates.Signaled(ctx) -> Predicates.ValidatedAfter(ctx) -> Empty,
    classify_validation: Predicates.ExternalDependency(ctx) -> Predicates.ValidatedAfter(ctx) ->
      Or(Predicates.Probed(ctx), Or(Predicates.Signaled(ctx), Predicates.Enforcement(ctx))),
    probe_requires_observability: Predicates.Probed(ctx) -> Predicates.ObservableBefore(ctx),
    future_output_unobservable: Predicates.ObservableBefore(ctx) -> Empty
  }

type Premises.Enforcement<-ctx: T.Context<T.ExternalUse>> is Type:
  EnforcementPremises{
    action_requires_premise: Predicates.PremiseRequiredBefore(Model.action_context(ctx)),
    forward: Premises.Forward<ctx>,
    effects: Predicates.Enforcement(ctx) -> Predicates.EnforcementEffects<ctx>
  }
