type problem = {
  task_id : string;
  prompt : string;
  entry_point : string;
  canonical_solution : string;
  private_input : string;
}

let source =
  "https://github.com/evalplus/humanevalplus_release/releases/download/v0.1.10/HumanEvalPlus.jsonl.gz"

let revision = "v0.1.10"
let sha256 = "42526ec0e7d5f3ee0b06d6ced98f8c8bae3d76519151bfb3d36f79010645bd7f"
let count = 164
let evaluator_commit = "6eb1e199c2e370518e7bf3e8eee6322c2b23c89c"
let numpy_version = "2.5.4"
let psutil_version = "7.2.2"

let id problem =
  match String.split_on_char '/' problem.task_id with
  | [ "HumanEval"; number ] ->
      let index = int_of_string number in
      if index < 0 || string_of_int index <> number then invalid_arg "Invalid HumanEval task ID";
      "humaneval-" ^ number
  | _ -> invalid_arg "Invalid HumanEval task ID"

let make problem ~stdin =
  if problem.entry_point = "" then invalid_arg "Missing HumanEval entry point";
  Case.make
    ~id:(id problem)
    ~fixture:(Fixture.of_files [ ("solution.py", problem.prompt) ])
    ~instruction:
      (Instruction.make
         ~skill:"reasoning"
         ~prompt:
           "Implement the specified function in solution.py. Preserve its signature and edit only \
            solution.py.")
    ~criterion:
      (Criterion.Code
         (Verifier.make
            ~inputs:[ "solution.py" ]
            ~files:[ ("verifier.py", Verifier.Resource "verifier.py") ]
            ~tools:[]
            ~command:[ "python3"; "-I"; "verifier.py"; "evalplus" ]
            ~stdin
            ~timeout_seconds:180))
    ~allowed_files:[ "solution.py" ]
    ~reference:
      (Reference.edits
         (Fixture.of_files [ ("solution.py", problem.prompt ^ problem.canonical_solution) ]))
