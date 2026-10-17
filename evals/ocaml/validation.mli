val issue : Validation_code.t -> string -> string -> string list -> Validation_issue.t
val checked : ?case_id:string -> Validation_issue.t list -> 'a -> ('a, Validation_failure.t) result
val when_invalid : bool -> Validation_issue.t -> Validation_issue.t list
