let spec ~inputs ~files ~tools ~command ~timeout_seconds =
  Verifier.make ~inputs ~files ~tools ~command ~stdin:"private" ~timeout_seconds

let () =
  let checks =
    Result.get_ok
      (spec
         ~inputs:[ "solution.py" ]
         ~files:[ ("grader.py", Ast.Inline "trusted") ]
         ~tools:[]
         ~command:[ "python3"; "grader.py" ]
         ~timeout_seconds:5)
  in
  assert (checks.inputs = [ "solution.py" ]);
  List.iter
    (fun inputs ->
      assert (
        Result.is_error (spec ~inputs ~files:[] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5)))
    [ []; [ "a.py"; "a.py" ]; [ "../bad" ]; [ "/bad" ]; [ "bad/path" ]; [ "" ]; [ "-argument" ] ];
  assert (
    Result.is_error
      (spec
         ~inputs:[ "a.py" ]
         ~files:[ ("a.py", Ast.Inline "private") ]
         ~tools:[]
         ~command:[ "run" ]
         ~timeout_seconds:5));
  let invalid = spec ~inputs:[ "bad/path" ] ~files:[] ~tools:[] ~command:[] ~timeout_seconds:0 in
  match invalid with
  | Ok _ -> assert false
  | Error failure ->
      assert (
        List.map (fun (issue : Ast.validation_issue) -> issue.code) failure.issues
        = [ Ast.Invalid_path; Ast.Invalid_command; Ast.Nonpositive_timeout ])
