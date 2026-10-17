type t = private { name : string; value : Response_value.t }

val create : name:string -> value:Response_value.t -> (t, Validation_failure.t) result
