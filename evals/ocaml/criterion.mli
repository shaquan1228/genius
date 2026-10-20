(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design;
   state criteria follow state-based grading of tool-using agents.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://arxiv.org/abs/2406.12045 (tau-bench: final state and required outputs) *)
type t = private
  | Code of { verifier : Verifier.t }
  | Answer of { rubric : Rubric.t }
  | State of { predicate : Predicate.t }

val create :
  ?code:Verifier.t ->
  ?answer:Rubric.t ->
  ?state:Predicate.t ->
  unit ->
  (t, Validation_failure.t) result
[@@python.exclusive]

val compare : before:t -> after:t -> Comparison.t

val condition : criterion:t -> Predicate.t
(** Every criterion as a predicate over the observation: a passed verification, the rubric's checks,
    or the declared state predicate. *)
