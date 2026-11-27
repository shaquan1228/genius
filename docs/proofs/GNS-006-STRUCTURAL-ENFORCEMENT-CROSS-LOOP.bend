import Base
import ./logic.bend as Logic

# GNS-006 is a conditional derivation from P1..P6, not a proof that those
# normative and environmental premises hold. State-0 and state-1 propositions
# stay separate parameters throughout: DependsOutput0 is not DependsOutput1.

# Source steps 2-3: P1 classifies a cross-loop premise before enforcement.
def initial_assumption(
  -DependsOutput0: Type,
  -Exogenous: Type,
  -Assumption0: Type,
  p1: DependsOutput0 -> Exogenous -> Assumption0,
  depends_output0: DependsOutput0,
  exogenous: Exogenous
) -> Assumption0:
  p1(depends_output0, exogenous)

# Source step 5: P4 and P5 rule out probing the future output in place.
def probing_is_impossible(
  -Probe: Type,
  -ObservableOutput0: Type,
  p4: Probe -> ObservableOutput0,
  p5: ObservableOutput0 -> Empty
) -> Probe -> Empty:
  probe => p5(p4(probe))

# Source step 8: P2 conflicts with the assumed validation witness.
def signaling_is_impossible(
  -Signal: Type,
  -Validated1: Type,
  p2: Signal -> Validated1 -> Empty,
  validated1: Validated1
) -> Signal -> Empty:
  signal => p2(signal, validated1)

# Source step 9: the exhaustive P3 disjunction leaves enforcement alone.
def eliminate_alternatives(
  -Probe: Type,
  -Signal: Type,
  -Enforce01: Type,
  alternatives: Logic.Disj<Probe, Logic.Disj<Signal, Enforce01>>,
  no_probe: Probe -> Empty,
  no_signal: Signal -> Empty
) -> Enforce01:
  match alternatives:
    case Logic.DisjunctionLeft{value}:
      Empty.absurd(Enforce01, no_probe(value))
    case Logic.DisjunctionRight{value}:
      match value:
        case Logic.DisjunctionLeft{value}:
          Empty.absurd(Enforce01, no_signal(value))
        case Logic.DisjunctionRight{value}:
          value

# Source steps 6-10. Validated1 is reusable logical evidence; its two uses
# correspond to P3 (enumerate moves) and P2 (exclude signaling).
def validation_implies_enforcement(
  -DependsOutput0: Type,
  -Exogenous: Type,
  -Probe: Type,
  -ObservableOutput0: Type,
  -Signal: Type,
  -Enforce01: Type,
  -Validated1: Data,
  p2: Signal -> Validated1 -> Empty,
  p3: DependsOutput0 -> Exogenous -> Validated1 -> Logic.Disj<Probe, Logic.Disj<Signal, Enforce01>>,
  p4: Probe -> ObservableOutput0,
  p5: ObservableOutput0 -> Empty,
  depends_output0: DependsOutput0,
  exogenous: Exogenous,
  +validated1: Validated1
) -> Enforce01:
  eliminate_alternatives(
    Probe, Signal, Enforce01,
    p3(depends_output0, exogenous, validated1),
    probing_is_impossible(Probe, ObservableOutput0, p4, p5),
    signaling_is_impossible(Signal, Validated1, p2, validated1)
  )

# Source step 11 projects validation from the complete P6 result. Keeping the
# other conjuncts here exposes the full enforcement assumption to the checker.
def project_validation(
  -StructurallyEnforced1: Type,
  -DependsOutput1: Type,
  -Validated1: Type,
  -Cascade: Type,
  effects: Logic.Conj<StructurallyEnforced1, Logic.Conj<(DependsOutput1 -> Empty), Logic.Conj<Validated1, (Cascade -> Empty)>>>
) -> Validated1:
  match effects:
    case Logic.Conjunction{left, right}:
      match right:
        case Logic.Conjunction{left, right}:
          match right:
            case Logic.Conjunction{left, right}:
              left

def enforcement_implies_validation(
  -Enforce01: Type,
  -StructurallyEnforced1: Type,
  -DependsOutput1: Type,
  -Validated1: Type,
  -Cascade: Type,
  p6: Enforce01 -> Logic.Conj<StructurallyEnforced1, Logic.Conj<(DependsOutput1 -> Empty), Logic.Conj<Validated1, (Cascade -> Empty)>>>,
  enforcement: Enforce01
) -> Validated1:
  project_validation(StructurallyEnforced1, DependsOutput1, Validated1, Cascade, p6(enforcement))

# All source premises remain explicit. P1 and GNS-004 establish source steps
# 3-4; those background witnesses are not needed by the biconditional's two
# conditional directions. No unindexed dependency is substituted after P6.
def theorem(
  -NonTrivial: Type,
  -DependsAction0: Type,
  -DependsOutput0: Data,
  -Exogenous: Data,
  -Assumption0: Type,
  -Probe: Type,
  -ObservableOutput0: Type,
  -Signal: Type,
  -Enforce01: Type,
  -StructurallyEnforced1: Type,
  -DependsOutput1: Type,
  -Validated1: Data,
  -Cascade: Type,
  p1: DependsOutput0 -> Exogenous -> Assumption0,
  gns004: NonTrivial -> DependsAction0 -> Validated1,
  p2: Signal -> Validated1 -> Empty,
  p3: DependsOutput0 -> Exogenous -> Validated1 -> Logic.Disj<Probe, Logic.Disj<Signal, Enforce01>>,
  p4: Probe -> ObservableOutput0,
  p5: ObservableOutput0 -> Empty,
  p6: Enforce01 -> Logic.Conj<StructurallyEnforced1, Logic.Conj<(DependsOutput1 -> Empty), Logic.Conj<Validated1, (Cascade -> Empty)>>>,
  non_trivial: NonTrivial,
  depends_action0: DependsAction0,
  +depends_output0: DependsOutput0,
  +exogenous: Exogenous
) -> Logic.Iff<Validated1, Enforce01>:
  assumption0 = initial_assumption(DependsOutput0, Exogenous, Assumption0, p1, depends_output0, exogenous)
  validation_required = gns004(non_trivial, depends_action0)
  Logic.Equivalence{
    validated1 => validation_implies_enforcement(
      DependsOutput0, Exogenous, Probe, ObservableOutput0, Signal, Enforce01, Validated1,
      p2, p3, p4, p5, depends_output0, exogenous, validated1
    ),
    enforcement => enforcement_implies_validation(
      Enforce01, StructurallyEnforced1, DependsOutput1, Validated1, Cascade, p6, enforcement
    )
  }

# GNS-006.1 adds Agent and Trusted to the antecedent, and reuses the parent
# conclusion unchanged. Neither additional hypothesis removes P5.
def trusted_agent_corollary(
  -Agent: Type,
  -Trusted: Type,
  -Validated1: Type,
  -Enforce01: Type,
  parent: Logic.Iff<Validated1, Enforce01>,
  agent: Agent,
  trusted: Trusted
) -> Logic.Iff<Validated1, Enforce01>:
  parent
