type t = private { fields : Response_field.t list }

val create : fields:Response_field.t list -> (t, Validation_failure.t) result
val empty : t
