(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = private { name : string; value : Response_value.t }

val create : name:string -> value:Response_value.t -> (t, Validation_failure.t) result
