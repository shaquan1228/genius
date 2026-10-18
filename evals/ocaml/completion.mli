(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type t = private Plain of { text : string } | Structured of { response : Response.t }

val create : ?plain:string -> ?structured:Response.t -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]

val trim : text:string -> string
val compare : before:t -> after:t -> Comparison.t
