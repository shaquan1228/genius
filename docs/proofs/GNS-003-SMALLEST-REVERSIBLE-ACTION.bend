import Base
import ./logic.bend as Logic

# GNS-003. InOODALoop(A) is supplied by the trigger. The conclusion is
# SmallestReversible(A), defined in the prose as SmallestStep(A) AND Reversible(A).
def theorem(
  -NonTrivial: Type,
  -InOODALoop: Type,
  -GoalAchieved: Type,
  -DecidePhase: Type,
  -SmallestStep: Type,
  -Reversible: Type,
  p1_loop_enters_decide: InOODALoop -> DecidePhase,
  p2_unfinished_decision_is_smallest_reversible:
    Logic.Conj<DecidePhase, GoalAchieved -> Empty> -> Logic.Conj<SmallestStep, Reversible>,
  trigger: Logic.Conj<NonTrivial, Logic.Conj<InOODALoop, GoalAchieved -> Empty>>
) -> Logic.Conj<SmallestStep, Reversible>:
  match trigger:
    case Logic.Conjunction{nontrivial, active_unfinished_loop}:
      match active_unfinished_loop:
        case Logic.Conjunction{in_ooda_loop, goal_not_achieved}:
          decide_phase = p1_loop_enters_decide(in_ooda_loop)
          p2_unfinished_decision_is_smallest_reversible(Logic.Conjunction{
            decide_phase, goal_not_achieved
          })
