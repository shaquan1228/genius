(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = private { fields : Response_field.t list }

val create : fields:Response_field.t list -> (t, Validation_failure.t) result
val empty : t
val compare : before:t -> after:t -> Response_comparison.t
