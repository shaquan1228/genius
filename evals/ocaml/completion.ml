(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
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
