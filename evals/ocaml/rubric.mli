(* Rubric: requirements used to grade a response. Eval rubrics specify criteria;
   exact scalar expectations and a bounded-text rule are our deterministic subset.
   https://github.com/openai/evals/blob/main/docs/eval-templates.md#example-model-graded-evals
   https://teaching.cornell.edu/teaching-resources/assessing-student-learning/using-rubrics *)
type t = private { expected : Response.t; text_rule : Text_rule.t option }

val create : expected:Response.t -> text_rule:Text_rule.t option -> (t, Validation_failure.t) result
val compare : before:t -> after:t -> Comparison.t
val grade : rubric:t -> response:Response.t option -> Rubric_grade.t
