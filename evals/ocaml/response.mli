(* Response: model-produced output, represented here by immutable named scalar
   fields shared with expected and reference data. This is a repo-specific subset.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type value = String of string | Bool of bool
type t

(* Immutable ordered fields with unique, nonempty names. *)
val empty : t
val of_fields : (string * value) list -> t
val fields : t -> (string * value) list
