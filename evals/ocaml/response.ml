(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
module Comparison = struct
  type field_comparison = {
    name : string;
    before : Response_value.t option;
    after : Response_value.t option;
    equal : bool;
  }

  type t = { equal : bool; fields : field_comparison list }

  module Fields = Map.Make (String)

  let create ~before ~after =
    let index fields =
      List.fold_left
        (fun indexed (field : Response_field.t) ->
          if Fields.mem field.name indexed then indexed
          else Fields.add field.name field.value indexed)
        Fields.empty
        fields
    in
    let fields =
      Fields.merge
        (fun name before after -> Some { name; before; after; equal = before = after })
        (index before)
        (index after)
      |> Fields.bindings |> List.map snd
    in
    { equal = List.for_all (fun (field : field_comparison) -> field.equal) fields; fields }
end

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

let compare ~(before : t) ~(after : t) = Comparison.create ~before:before.fields ~after:after.fields
