type t = private Inline of { text : string } | Resource of { key : string }

val create : ?inline:string -> ?resource:string -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]
