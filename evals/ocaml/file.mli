type t = private { path : string; contents : string }

val create : path:string -> contents:string -> (t, Validation_failure.t) result
val valid_path : path:string -> bool
val path_issues : field:string -> paths:string list -> Validation_issue.t list
