(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = private String of { value : string } | Bool of { value : bool }

val create : ?string:string -> ?bool:bool -> unit -> (t, Validation_failure.t) result
[@@python.exclusive]
