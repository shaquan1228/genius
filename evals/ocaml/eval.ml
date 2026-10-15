(* Case assembly only. Fixtures, checks, scope, and references are explicit inputs.
   Assembly rejects parts that name files the other parts do not provide. *)
type t = {
  id : string;
  fixture : Fixture.t;
  task : Task.t;
  checks : Check.t;
  allowed_files : string list;
  reference : Reference.t;
}

let paths fixture = List.map fst (Fixture.files fixture)

let case ~id ~fixture ~task ~checks ~allowed_files ~reference =
  let require problem ~within names =
    match List.filter (fun name -> not (List.mem name within)) names with
    | [] -> ()
    | missing ->
        invalid_arg (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
  in
  (match checks with
  | Check.Code { sources; _ } ->
      require "checks read files missing from the fixture" ~within:(paths fixture) sources
  | Check.Answer _ -> ());
  (match reference with
  | Reference.Edits edits ->
      require "reference edits files outside allowed_files" ~within:allowed_files (paths edits)
  | Reference.Reply _ -> ());
  { id; fixture; task; checks; allowed_files; reference }
