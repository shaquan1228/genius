let spec ~inputs ~files ~tools ~command ~timeout_seconds =
  Verifier.create ~inputs ~files ~tools ~command ~stdin:"private" ~timeout_seconds

let () =
  let artifact =
    Result.get_ok
      (Artifact.create
         ~path:"grader.py"
         ~content:(Result.get_ok (Content.create ~inline:"trusted" ())))
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
    Result.is_error
      (Artifact.create
         ~path:"../bad"
         ~content:(Result.get_ok (Content.create ~inline:"private" ()))));
  let overlap =
    Result.get_ok
      (Artifact.create ~path:"a.py" ~content:(Result.get_ok (Content.create ~inline:"private" ())))
  in
  assert (
    Result.is_error
      (spec ~inputs:[ "a.py" ] ~files:[ overlap ] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5));
  match spec ~inputs:[ "bad/path" ] ~files:[] ~tools:[] ~command:[] ~timeout_seconds:0 with
  | Ok _ -> assert false
  | Error failure ->
      assert (
        List.map (fun (issue : Validation_issue.t) -> issue.code) failure.issues
        = [
            Validation_code.Invalid_path;
            Validation_code.Invalid_command;
            Validation_code.Nonpositive_timeout;
          ])
