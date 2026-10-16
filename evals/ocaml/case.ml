(* Validating constructors for Ast.task. *)
let validate (case : Ast.task) =
  let { Ast.id; fixture; instruction; criterion; allowed_files; reference } = case in
  let valid_name name =
    name <> ""
    && (match name.[0] with 'a' .. 'z' -> true | _ -> false)
    && String.for_all (function 'a' .. 'z' | '0' .. '9' | '-' -> true | _ -> false) name
  in
  if not (valid_name id && valid_name instruction.skill) then invalid_arg "Invalid case identity";
  let paths fixture = List.map fst (Fixture.files fixture) in
  if not (List.for_all Verifier.valid_path (paths fixture @ paths reference.edits @ allowed_files))
  then invalid_arg "Invalid case paths";
  ignore (Criterion.validate criterion);
  (match reference.completion with
  | Ast.Plain _ -> ()
  | Ast.Structured fields -> ignore (Response.of_fields fields));
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
