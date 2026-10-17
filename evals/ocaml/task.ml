type t = {
  id : string;
  fixture : Fixture.t;
  instruction : Instruction.t;
  criterion : Criterion.t;
  allowed_files : string list;
  reference : Reference.t;
}

let create ~id ~fixture ~(instruction : Instruction.t) ~criterion ~allowed_files
    ~(reference : Reference.t) =
  let paths fixture = List.map (fun (file : File.t) -> file.path) (Fixture.files ~fixture) in
  let fixture_paths = paths fixture and reference_paths = paths reference.edits in
  let require code field problem ~within names =
    let missing = List.filter (fun name -> not (List.mem name within)) names in
    Validation.when_invalid
      (missing = [])
      (Validation.issue
         code
         field
         (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
         missing)
  in
  let problems =
    Validation.when_invalid
      (Instruction.valid_name ~name:id)
      (Validation.issue Validation_code.Invalid_identity "id" "Invalid case identity" [ id ])
    @ File.path_issues ~field:"allowed_files" ~paths:allowed_files
    @ require
        Validation_code.Reference_outside_scope
        "reference.edits"
        "reference edits files outside allowed_files"
        ~within:allowed_files
        reference_paths
    @
    match criterion with
    | Criterion.Answer _ -> []
    | Criterion.Code { verifier } ->
        require
          Validation_code.Missing_fixture_inputs
          "verifier.inputs"
          "criteria read files missing from the fixture"
          ~within:fixture_paths
          verifier.inputs
        @ Validation.when_invalid
            (not
               (List.exists
                  (fun (artifact : Artifact.t) -> List.mem artifact.path fixture_paths)
                  (verifier.files @ verifier.tools)))
            (Validation.issue
               Validation_code.Artifact_overlap
               "verifier"
               ("Case " ^ id ^ ": verifier artifacts overlap fixture")
               [])
  in
  Validation.checked
    ~case_id:id
    problems
    { id; fixture; instruction; criterion; allowed_files; reference }

let resolve_resources ~(task : t) ~resources =
  let result =
    match task.criterion with
    | Criterion.Answer _ -> Ok task
    | Criterion.Code { verifier } ->
        Result.bind (Verifier.resolve_resources ~verifier ~resources) (fun verifier ->
            Result.map
              (fun criterion -> { task with criterion })
              (Criterion.create ~code:verifier ()))
  in
  Result.map_error
    (fun failure -> { failure with Validation_failure.case_id = Some task.id })
    result

let definitions = [ ("correctness", `Correctness); ("scope", `Scope) ]
let required_scores = List.map fst definitions

let answer (criterion : Rubric.t) response =
  match response with
  | None -> false
  | Some (response : Response.t) ->
      let exact, text_valid =
        match criterion.text_rule with
        | None -> (response.fields, true)
        | Some rule ->
            let valid =
              match
                List.find_opt
                  (fun (field : Response_field.t) -> field.name = rule.field)
                  response.fields
              with
              | Some { value = Response_value.String { value = text }; _ } ->
                  let words = Text_rule.word_count ~text in
                  rule.min_words <= words && words <= rule.max_words
              | Some { value = Response_value.Bool _; _ } | None -> false
            in
            ( List.filter
                (fun (field : Response_field.t) -> field.name <> rule.field)
                response.fields,
              valid )
      in
      text_valid && List.sort compare exact = List.sort compare criterion.expected.fields

let grade ~(task : t) ~response ~(outcome : Outcome.t) =
  let correctness =
    match task.criterion with
    | Criterion.Code _ -> (
        match outcome.verification with
        | Verification.Harness_error { detail } ->
            Error (Grading_failure.Verification_harness_error { detail })
        | Verification.Passed -> Ok true
        | Verification.Unchecked | Verification.Failed | Verification.Invalid_submission
        | Verification.Timed_out ->
            Ok false)
    | Criterion.Answer { rubric } -> Ok (answer rubric response)
  in
  Result.map
    (fun correctness ->
      let allowed = List.map (fun path -> "workspace/" ^ path) task.allowed_files in
      let scope = List.for_all (fun path -> List.mem path allowed) outcome.changed_files in
      List.map
        (fun (name, criterion) ->
          (name, match criterion with `Correctness -> correctness | `Scope -> scope))
        definitions)
    correctness

let verifier ~(task : t) =
  match task.criterion with
  | Criterion.Code { verifier } -> Some verifier
  | Criterion.Answer _ -> None
