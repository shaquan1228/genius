(* Assessment: this repository's evidence-bound checks and named conjunctions.
   Graders may contain multiple assertions; scores interpret their composition.
   The sources establish that separation, not this particular assessment algebra.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://developers.openai.com/api/docs/guides/graders *)
type evidence =
  | Present of { response : Response.t option }
  | Field of { comparison : Response.Comparison.field_comparison }
  | Text of { rule : Text_rule.t; value : Response_value.t option }
  | Verified of { verification : Verification.t }
  | Scope of { allowed_files : string list; changed_files : string list }

type t = Check of { evidence : evidence } | All of { checks : (string * t) list }

let present ~response = Check { evidence = Present { response } }
let field ~comparison = Check { evidence = Field { comparison } }
let text ~rule ~value = Check { evidence = Text { rule; value } }

let scope ~allowed_files ~changed_files =
  Check { evidence = Scope { allowed_files; changed_files } }

let all ~checks =
  let names = List.map fst checks in
  Validation.checked
    (Validation.when_invalid
       (List.for_all (( <> ) "") names
       && List.length names = List.length (List.sort_uniq String.compare names))
       (Validation.issue
          Validation_code.Invalid_identity
          "assessment.checks"
          "Assessment checks require unique, nonempty names"
          names))
    (All { checks })

let verified ~verification =
  match verification with
  | Verification.Harness_error { detail } ->
      Error (Grading_failure.Verification_harness_error { detail })
  | _ -> Ok (Check { evidence = Verified { verification } })

let word_count ~value =
  match value with
  | Some (Response_value.String { value }) -> Some (Text_rule.word_count ~text:value)
  | Some (Response_value.Bool _) | None -> None

let outside allowed changed =
  List.sort_uniq String.compare (List.filter (fun path -> not (List.mem path allowed)) changed)

let check_passed = function
  | Present { response } -> Option.is_some response
  | Field { comparison } -> comparison.equal
  | Text { rule; value } -> (
      match word_count ~value with
      | Some count -> rule.min_words <= count && count <= rule.max_words
      | None -> false)
  | Verified { verification } -> verification = Verification.Passed
  | Scope { allowed_files; changed_files } -> outside allowed_files changed_files = []

let rec fold ~leaf ~group = function
  | Check { evidence } -> leaf evidence
  | All { checks } ->
      group (List.map (fun (name, assessment) -> (name, fold ~leaf ~group assessment)) checks)

let passed ~assessment = fold ~leaf:check_passed ~group:(List.for_all snd) assessment

let unexpected_files ~assessment =
  let leaf = function
    | Scope { allowed_files; changed_files } -> outside allowed_files changed_files
    | Present _ | Field _ | Text _ | Verified _ -> []
  in
  fold ~leaf ~group:(fun checks -> List.concat_map snd checks) assessment
  |> List.sort_uniq String.compare

let scores ~assessment =
  match assessment with
  | All { checks } -> List.map (fun (name, assessment) -> (name, passed ~assessment)) checks
  | Check _ -> [ ("passed", passed ~assessment) ]

let rubric ~(rubric : Rubric.t) ~(response : Response.t option) =
  let actual = match response with None -> [] | Some response -> response.fields in
  let exact, text_checks =
    match rubric.text_rule with
    | None -> (actual, [])
    | Some rule ->
        let value =
          Option.map
            (fun (field : Response_field.t) -> field.value)
            (List.find_opt (fun (field : Response_field.t) -> field.name = rule.field) actual)
        in
        ( List.filter (fun (field : Response_field.t) -> field.name <> rule.field) actual,
          [ ("text", text ~rule ~value) ] )
  in
  let comparison = Response.Comparison.create ~before:rubric.expected.fields ~after:exact in
  let fields =
    List.map
      (fun (comparison : Response.Comparison.field_comparison) ->
        (comparison.name, field ~comparison))
      comparison.fields
  in
  All
    {
      checks =
        [ ("response", present ~response); ("fields", All { checks = fields }) ] @ text_checks;
    }

let criterion ~criterion ~response ~verification =
  Result.map
    (fun verification_assessment ->
      match criterion with
      | Criterion.Code _ -> verification_assessment
      | Criterion.Answer { rubric = specification } -> rubric ~rubric:specification ~response)
    (verified ~verification)
