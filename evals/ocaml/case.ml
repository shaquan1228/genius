(* Case: one test specification combining instruction, initial state, criteria, and reference.
   Mapping follows Anthropic's task/test case and Hugging Face's sample, rather than an
   execution-level task configuration.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://huggingface.co/docs/lighteval/main/en/package_reference/doc *)
type t = {
  id : string;
  fixture : Fixture.t;
  instruction : Instruction.t;
  criterion : Criterion.t;
  allowed_files : string list;
  reference : Reference.t;
}

let paths fixture = List.map fst (Fixture.files fixture)

let validate (case : t) =
  let { id; fixture; instruction = _; criterion; allowed_files; reference } = case in
  let require ~problem ~within names =
    match List.filter (fun name -> not (List.mem name within)) names with
    | [] -> ()
    | missing ->
        invalid_arg (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
  in
  (match criterion with
  | Criterion.Code verifier ->
      require
        ~problem:"criteria read files missing from the fixture"
        ~within:(paths fixture)
        verifier.Verifier.inputs;
      if
        List.exists
          (fun (name, _) -> List.mem name (paths fixture))
          (verifier.files @ verifier.tools)
      then invalid_arg ("Case " ^ id ^ ": verifier artifacts overlap fixture")
  | Criterion.Answer _ -> ());
  require
    ~problem:"reference edits files outside allowed_files"
    ~within:allowed_files
    (paths reference.Reference.edits);
  case

let make ~id ~fixture ~instruction ~criterion ~allowed_files ~reference =
  validate { id; fixture; instruction; criterion; allowed_files; reference }
