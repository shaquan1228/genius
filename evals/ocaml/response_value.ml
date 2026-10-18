(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type t = String of { value : string } | Bool of { value : bool }

let create ?string ?bool () =
  match (string, bool) with
  | Some value, None -> Ok (String { value })
  | None, Some value -> Ok (Bool { value })
  | _ ->
      Error
        {
          Validation_failure.case_id = None;
          issues =
            [
              Validation.issue
                Validation_code.Invalid_alternative
                "response_value"
                "Response_value.create requires exactly one of string or bool"
                [ "string"; "bool" ];
            ];
        }
