type t = Plain of { text : string } | Structured of { response : Response.t }

let create ?plain ?structured () =
  match (plain, structured) with
  | Some value, None -> Ok (Plain { text = value })
  | None, Some value -> Ok (Structured { response = value })
  | _ ->
      Error
        {
          Validation_failure.case_id = None;
          issues =
            [
              Validation.issue
                Validation_code.Invalid_alternative
                "completion"
                "Completion.create requires exactly one of plain or structured"
                [ "plain"; "structured" ];
            ];
        }

let trim = Text.trim

let compare ~before ~after =
  let field, equal =
    match (before, after) with
    | Plain a, Plain b -> ("text", a.text = b.text)
    | Structured a, Structured b ->
        ("response", (Response.compare ~before:a.response ~after:b.response).equal)
    | Plain _, Structured _ | Structured _, Plain _ -> ("kind", false)
  in
  Comparison.create ~fields:[ (field, equal) ]
