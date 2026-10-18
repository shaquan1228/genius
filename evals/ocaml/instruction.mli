type t = private { skill : string; prompt : string }

val create : skill:string -> prompt:string -> (t, Validation_failure.t) result
val valid_name : name:string -> bool
val compare : before:t -> after:t -> Comparison.t
