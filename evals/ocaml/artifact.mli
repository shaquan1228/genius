type t = private { path : string; content : Content.t }

val create : path:string -> content:Content.t -> (t, Validation_failure.t) result
val resolve : artifact:t -> resources:Resource_binding.t list -> (t, Validation_failure.t) result
