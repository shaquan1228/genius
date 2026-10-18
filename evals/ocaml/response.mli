type t = private { fields : Response_field.t list }

val create : fields:Response_field.t list -> (t, Validation_failure.t) result
val empty : t
val compare : before:t -> after:t -> Response_comparison.t
