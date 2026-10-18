(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
module Comparison : sig
  type field_comparison = private {
    name : string;
    before : Response_value.t option;
    after : Response_value.t option;
    equal : bool;
  }

  type t = private { equal : bool; fields : field_comparison list }

  val create : before:Response_field.t list -> after:Response_field.t list -> t
end

type t = private { fields : Response_field.t list }

val create : fields:Response_field.t list -> (t, Validation_failure.t) result
val empty : t
val compare : before:t -> after:t -> Comparison.t
