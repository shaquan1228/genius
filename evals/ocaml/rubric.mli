type t = private { expected : Response.t; text_rule : Text_rule.t option }

val create : expected:Response.t -> text_rule:Text_rule.t option -> (t, Validation_failure.t) result
