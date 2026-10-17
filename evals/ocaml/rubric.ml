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
