(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type t = private Code of { verifier : Verifier.t } | Answer of { rubric : Rubric.t }

val create : ?code:Verifier.t -> ?answer:Rubric.t -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]

val compare : before:t -> after:t -> Comparison.t

val grade :
  criterion:t ->
  response:Response.t option ->
  verification:Verification.t ->
  (Correctness_grade.t, Grading_failure.t) result
