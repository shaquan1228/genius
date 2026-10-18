(* Instruction: task input describing the requested behavior. This prompt-only value
   maps to Hugging Face's instruction/query and OpenAI eval inputs.
   https://huggingface.co/docs/lighteval/main/en/package_reference/doc
   https://developers.openai.com/api/docs/guides/evals *)
type t = private { skill : string; prompt : string }

val create : skill:string -> prompt:string -> (t, Validation_failure.t) result
val valid_name : name:string -> bool
val compare : before:t -> after:t -> Comparison.t
