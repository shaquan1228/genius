type t = private String of { value : string } | Bool of { value : bool }

val create : ?string:string -> ?bool:bool -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]
