(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = { fields : Response_field.t list }

let empty : t = { fields = [] }

let create ~(fields : Response_field.t list) =
  let rec collect seen = function
    | [] -> []
    | (field : Response_field.t) :: rest ->
        Validation.when_invalid
          (not (List.mem field.name seen))
          (Validation.issue
             Validation_code.Invalid_response_field
             "response.fields"
             "Response fields need unique names"
             [ field.name ])
        @ collect (field.name :: seen) rest
  in
  Validation.checked (collect [] fields) { fields }

let compare ~(before : t) ~(after : t) =
  Response_comparison.create ~before:before.fields ~after:after.fields
