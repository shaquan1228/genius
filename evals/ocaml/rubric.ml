(* Rubric: requirements used to grade a response. Eval rubrics specify criteria;
   exact scalar expectations and a bounded-text rule are our deterministic subset.
   https://github.com/openai/evals/blob/main/docs/eval-templates.md#example-model-graded-evals
   https://teaching.cornell.edu/teaching-resources/assessing-student-learning/using-rubrics *)
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

let predicate ~(rubric : t) =
  let field name = [ "response"; name ] in
  let scalar = function
    | Response_value.String { value } -> Value.String { value }
    | Response_value.Bool { value } -> Value.Bool { value }
  in
  let fields =
    List.map
      (fun (expected : Response_field.t) ->
        ( expected.name,
          Result.get_ok
            (Predicate.equals ~path:(field expected.name) ~expected:(scalar expected.value)) ))
      rubric.expected.fields
  in
  let text =
    Option.map
      (fun (rule : Text_rule.t) ->
        ( "text",
          Result.get_ok
            (Predicate.words
               ~path:(field rule.field)
               ~min_words:rule.min_words
               ~max_words:rule.max_words) ))
      rubric.text_rule
  in
  Result.get_ok
    (Predicate.all
       ~checks:
         ([
            ("response", Result.get_ok (Predicate.present ~path:[ "response" ]));
            ("fields", Result.get_ok (Predicate.all ~checks:fields));
          ]
         @ Option.to_list text))
