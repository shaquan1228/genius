type t = private { expected : Response.t; text_rule : Text_rule.t option }

val create : expected:Response.t -> text_rule:Text_rule.t option -> (t, Validation_failure.t) result
val compare : before:t -> after:t -> Comparison.t
val grade : rubric:t -> response:Response.t option -> Rubric_grade.t
