type t = private Plain of { text : string } | Structured of { response : Response.t }

val create : ?plain:string -> ?structured:Response.t -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]
