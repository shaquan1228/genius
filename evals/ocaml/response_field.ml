(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = { name : string; value : Response_value.t }

let create ~name ~value =
  Validation.checked
    (Validation.when_invalid
       (name <> "")
       (Validation.issue
          Validation_code.Invalid_response_field
          "response.name"
          "Response fields need nonempty names"
          [ name ]))
    { name; value }
