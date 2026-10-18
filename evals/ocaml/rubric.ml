type t = { expected : Response.t; text_rule : Text_rule.t option }

let create ~(expected : Response.t) ~(text_rule : Text_rule.t option) =
  let problems =
    Validation.when_invalid
      (expected.fields <> [] || text_rule <> None)
      (Validation.issue
         Validation_code.Empty_answer
         "criterion"
         "Criterion.Answer criterion cannot be empty"
         [])
    @
    match text_rule with
    | None -> []
    | Some rule ->
        Validation.when_invalid
          (not
             (List.exists
                (fun (field : Response_field.t) -> field.name = rule.field)
                expected.fields))
          (Validation.issue
             Validation_code.Overlapping_text_field
             "text_rule.field"
             "Text rule overlaps expected fields"
             [ rule.field ])
  in
  Validation.checked problems { expected; text_rule }

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:
      [
        ("expected", (Response.compare ~before:before.expected ~after:after.expected).equal);
        ("text_rule", before.text_rule = after.text_rule);
      ]

let grade ~(rubric : t) ~(response : Response.t option) =
  let actual = match response with None -> [] | Some response -> response.fields in
  let text_rule = Option.map (fun rule -> Text_rule.grade ~rule ~response) rubric.text_rule in
  let actual =
    match rubric.text_rule with
    | None -> actual
    | Some rule -> List.filter (fun (field : Response_field.t) -> field.name <> rule.field) actual
  in
  Rubric_grade.create
    ~response_present:(Option.is_some response)
    ~fields:(Response_comparison.create ~before:rubric.expected.fields ~after:actual)
    ~text_rule
