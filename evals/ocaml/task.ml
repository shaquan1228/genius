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
