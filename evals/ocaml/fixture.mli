type t

val create : files:File.t list -> (t, Validation_failure.t) result
val empty : t
val add : fixture:t -> file:File.t -> (t, Validation_failure.t) result
val overlay : base:t -> overrides:t -> t
val files : fixture:t -> File.t list
