let spec ~inputs ~files ~tools ~command ~timeout_seconds =
  Construct.verifier ~inputs ~files ~tools ~command ~stdin:"private" ~timeout_seconds

let () =
  let artifact =
    Result.get_ok (Construct.artifact ~path:"grader.py" ~content:(Ast.Inline { text = "trusted" }))
  in
  let checks =
    Result.get_ok
      (spec
         ~inputs:[ "solution.py" ]
         ~files:[ artifact ]
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
    Result.is_error (Construct.artifact ~path:"../bad" ~content:(Ast.Inline { text = "private" })));
  let overlap =
    Result.get_ok (Construct.artifact ~path:"a.py" ~content:(Ast.Inline { text = "private" }))
  in
  assert (
    Result.is_error
      (spec ~inputs:[ "a.py" ] ~files:[ overlap ] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5));
  match spec ~inputs:[ "bad/path" ] ~files:[] ~tools:[] ~command:[] ~timeout_seconds:0 with
  | Ok _ -> assert false
  | Error failure ->
      assert (
        List.map (fun (issue : Ast.validation_issue) -> issue.code) failure.issues
        = [ Ast.Invalid_path; Ast.Invalid_command; Ast.Nonpositive_timeout ])
