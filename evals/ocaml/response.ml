(* Response: model-produced output. The immutable named string/boolean field
   collection is our structured-output subset, also used for expected and reference data.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type value = String of string | Bool of bool
type t = (string * value) list

let empty = []

let of_fields fields =
  let rec validate seen = function
    | [] -> ()
    | (name, _) :: rest ->
        if name = "" || List.mem name seen then
          invalid_arg "Response fields need unique nonempty names";
        validate (name :: seen) rest
  in
  validate [] fields;
  fields

let fields response = response
