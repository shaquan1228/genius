(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type t = private { field : string; min_words : int; max_words : int }

val create : field:string -> min_words:int -> max_words:int -> (t, Validation_failure.t) result
val word_count : text:string -> int
