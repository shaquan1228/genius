type t = Inline of { text : string } | Resource of { key : string }

let create ?inline ?resource () =
  match (inline, resource) with
  | Some value, None -> Ok (Inline { text = value })
  | None, Some value -> Ok (Resource { key = value })
  | _ ->
      Error
        {
          Validation_failure.case_id = None;
          issues =
            [
              Validation.issue
                Validation_code.Invalid_alternative
                "content"
                "Content.create requires exactly one of inline or resource"
                [ "inline"; "resource" ];
            ];
        }
