(* Validating constructors for Ast.case. *)
let validate (case : Ast.case) =
  let { Ast.id; fixture; instruction = _; criterion; allowed_files; reference } = case in
  ignore (Criterion.validate criterion);
  (match reference.completion with
  | Ast.Plain _ -> ()
  | Ast.Structured fields -> ignore (Response.of_fields fields));
  let paths fixture = List.map fst (Fixture.files fixture) in
  let require ~problem ~within names =
    match List.filter (fun name -> not (List.mem name within)) names with
    | [] -> ()
    | missing ->
        invalid_arg (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
  in
  (match criterion with
  | Ast.Code verifier ->
      require
        ~problem:"criteria read files missing from the fixture"
        ~within:(paths fixture)
        verifier.Ast.inputs;
      if
        List.exists
          (fun (name, _) -> List.mem name (paths fixture))
          (verifier.files @ verifier.tools)
      then invalid_arg ("Case " ^ id ^ ": verifier artifacts overlap fixture")
  | Ast.Answer _ -> ());
  require
    ~problem:"reference edits files outside allowed_files"
    ~within:allowed_files
    (paths reference.edits);
  case

let make ~id ~fixture ~instruction ~criterion ~allowed_files ~reference =
  validate { id; fixture; instruction; criterion; allowed_files; reference }
