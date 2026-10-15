(* Score: a grader result. Named boolean correctness and scope results are this
   repository's initial representation, rather than a universal score schema.
   https://developers.openai.com/api/docs/guides/graders
   https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html *)
type t

val of_fields : (string * bool) list -> t
val fields : t -> (string * bool) list
