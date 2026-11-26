import Base
import ./logic.bend as Logic

# GNS-002. P1 is the parent premise NonTrivial(A) -> OODA(A), not
# GNS-001's different conclusion PrecededByObservation(A).
def theorem(
  -NonTrivial: Type,
  -GoalAchieved: Type,
  -OODA: Type,
  -Cycle: Type,
  -ActThenObserve: Type,
  -FollowedByObservation: Type,
  p1_nontrivial_enters_ooda: NonTrivial -> OODA,
  p2_ooda_is_continuous: OODA -> Logic.Conj<Cycle, ActThenObserve>,
  p3_unfinished_cycle_observes_again:
    Logic.Conj<Logic.Conj<Cycle, ActThenObserve>, GoalAchieved -> Empty> -> FollowedByObservation,
  trigger: Logic.Conj<NonTrivial, GoalAchieved -> Empty>
) -> FollowedByObservation:
  match trigger:
    case Logic.Conjunction{nontrivial, goal_not_achieved}:
      ooda = p1_nontrivial_enters_ooda(nontrivial)
      cycle_and_act_then_observe = p2_ooda_is_continuous(ooda)
      p3_unfinished_cycle_observes_again(Logic.Conjunction{
        cycle_and_act_then_observe, goal_not_achieved
      })
