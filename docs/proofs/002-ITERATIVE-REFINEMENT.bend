import Base

def theorem(
  -NonTrivial: Type,
  -GoalAchieved: Type,
  -OODA: Type,
  -Cycle: Type,
  -ActThenObserve: Type,
  -FollowedByObservation: Type,
  enter_loop: NonTrivial -> OODA,
  continue_cycle: OODA -> (Cycle & ActThenObserve),
  observe_again: (Cycle & ActThenObserve) -> (GoalAchieved -> Empty) -> FollowedByObservation,
  nontrivial: NonTrivial,
  unfinished: GoalAchieved -> Empty
) -> FollowedByObservation:
  cycle = continue_cycle(enter_loop(nontrivial))
  observe_again(cycle, unfinished)
