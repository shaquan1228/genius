(* Task: one test specification combining instruction, initial state, criteria, and reference.
   Anthropic defines a task as a single test with inputs and success criteria; Hugging Face
   represents a benchmark sample with its query, expected outputs, and task metadata.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://huggingface.co/docs/lighteval/v0.13.0/package_reference/doc *)
module Component_comparison = Comparison

module Comparison = struct
  type t = {
    equal : bool;
    id : Comparison.t;
    fixture : Fixture_comparison.t;
    instruction : Comparison.t;
    criterion : Comparison.t;
    allowed_files : Comparison.t;
    reference : Comparison.t;
  }

  let create ~(id : Comparison.t) ~(fixture : Fixture_comparison.t) ~(instruction : Comparison.t)
      ~(criterion : Comparison.t) ~(allowed_files : Comparison.t) ~(reference : Comparison.t) =
    {
      equal =
        id.equal && fixture.equal && instruction.equal && criterion.equal && allowed_files.equal
        && reference.equal;
      id;
      fixture;
      instruction;
      criterion;
      allowed_files;
      reference;
    }
end

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
    | Criterion.Answer _ | Criterion.State _ -> []
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
    | Criterion.Answer _ | Criterion.State _ -> Ok task
    | Criterion.Code { verifier } ->
        Result.bind (Verifier.resolve_resources ~verifier ~resources) (fun verifier ->
            Result.map
              (fun criterion -> { task with criterion })
              (Criterion.create ~code:verifier ()))
  in
  Result.map_error
    (fun failure -> { failure with Validation_failure.case_id = Some task.id })
    result

let verifier ~(task : t) =
  match task.criterion with
  | Criterion.Code { verifier } -> Some verifier
  | Criterion.Answer _ | Criterion.State _ -> None

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~id:(Component_comparison.create ~fields:[ ("id", before.id = after.id) ])
    ~fixture:(Fixture.compare ~before:before.fixture ~after:after.fixture)
    ~instruction:(Instruction.compare ~before:before.instruction ~after:after.instruction)
    ~criterion:(Criterion.compare ~before:before.criterion ~after:after.criterion)
    ~allowed_files:
      (Component_comparison.create
         ~fields:
           [
             ( "allowed_files",
               List.sort_uniq String.compare before.allowed_files
               = List.sort_uniq String.compare after.allowed_files );
           ])
    ~reference:(Reference.compare ~before:before.reference ~after:after.reference)

let required_scores = [ "correctness"; "scope" ]

let assess ~task ~response ~(outcome : Outcome.t) =
  match outcome.verification with
  | Verification.Harness_error { detail } ->
      Error (Grading_failure.Verification_harness_error { detail })
  | _ ->
      let scope =
        Result.get_ok
          (Predicate.within
             ~path:[ "changed_files" ]
             ~allowed:(List.map (fun value -> Value.String { value }) task.allowed_files))
      in
      Ok
        (Assessment.create
           ~predicate:
             (Result.get_ok
                (Predicate.all
                   ~checks:
                     [
                       ("correctness", Criterion.condition ~criterion:task.criterion);
                       ("scope", scope);
                     ]))
           ~observation:(Outcome.observation ~outcome ~response))

(* Grader: pure logic applying criteria to responses and observed outcomes.
   IO, execution, and presentation remain harness responsibilities.
   https://developers.openai.com/api/docs/guides/graders
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
let grade ~task ~response ~outcome =
  Result.map (fun assessment -> Assessment.scores ~assessment) (assess ~task ~response ~outcome)
