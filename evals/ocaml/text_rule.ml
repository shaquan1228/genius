type t = { field : string; min_words : int; max_words : int }

let create ~field ~min_words ~max_words =
  Validation.checked
    (Validation.when_invalid
       (field <> "" && min_words >= 0 && max_words >= min_words)
       (Validation.issue
          Validation_code.Invalid_text_rule
          "text_rule"
          "Invalid text rule"
          [ field ]))
    { field; min_words; max_words }

let word_count = Text.word_count

let grade ~(rule : t) ~(response : Response.t option) =
  let word_count =
    Option.bind response (fun response ->
        Option.bind
          (List.find_opt
             (fun (field : Response_field.t) -> field.name = rule.field)
             response.fields)
          (fun (field : Response_field.t) ->
            match field.value with
            | Response_value.String { value } -> Some (word_count ~text:value)
            | Response_value.Bool _ -> None))
  in
  Text_rule_grade.create
    ~field:rule.field
    ~word_count
    ~min_words:rule.min_words
    ~max_words:rule.max_words
