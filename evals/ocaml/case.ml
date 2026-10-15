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

let make ~id ~fixture ~instruction ~criterion ~allowed_files ~reference =
  let require ~problem ~within names =
    match List.filter (fun name -> not (List.mem name within)) names with
    | [] -> ()
    | missing ->
        invalid_arg (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
  in
  (match criterion with
  | Criterion.Code { sources; _ } ->
      require
        ~problem:"criteria read files missing from the fixture"
        ~within:(paths fixture)
        sources
  | Criterion.Answer _ -> ());
  require
    ~problem:"reference edits files outside allowed_files"
    ~within:allowed_files
    (paths reference.Reference.edits);
  { id; fixture; instruction; criterion; allowed_files; reference }
