import Base

def theorem(
  -NonTrivial: Type,
  -InOODALoop: Type,
  -GoalAchieved: Type,
  -DecidePhase: Type,
  -SmallestStep: Type,
  -Reversible: Type,
  enter_decide_phase: InOODALoop -> DecidePhase,
  choose_step: DecidePhase -> (GoalAchieved -> Empty) -> (SmallestStep & Reversible),
  nontrivial: NonTrivial,
  in_loop: InOODALoop,
  unfinished: GoalAchieved -> Empty
) -> (SmallestStep & Reversible):
  choose_step(enter_decide_phase(in_loop), unfinished)
