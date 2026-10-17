type t = private Code of { verifier : Verifier.t } | Answer of { rubric : Rubric.t }

val create : ?code:Verifier.t -> ?answer:Rubric.t -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]
