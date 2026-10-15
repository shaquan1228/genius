let spec ~inputs ~files ~tools ~command ~timeout_seconds =
  Verifier.make ~inputs ~files ~tools ~command ~stdin:"private" ~timeout_seconds

let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let () =
  let checks =
    spec
      ~inputs:[ "solution.py" ]
      ~files:[ ("grader.py", Inline "trusted") ]
      ~tools:[]
      ~command:[ "python3"; "grader.py" ]
      ~timeout_seconds:5
  in
  assert (checks.inputs = [ "solution.py" ]);
  rejected (fun () ->
      spec ~inputs:[ "a.py"; "a.py" ] ~files:[] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5);
  rejected (fun () -> spec ~inputs:[] ~files:[] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5);
  List.iter
    (fun name ->
      rejected (fun () ->
          spec ~inputs:[ name ] ~files:[] ~tools:[] ~command:[ "run" ] ~timeout_seconds:5))
    [ "../bad"; "/bad"; "bad/path"; ""; "-argument" ];
  rejected (fun () ->
      spec
        ~inputs:[ "a.py" ]
        ~files:[ ("a.py", Inline "private") ]
        ~tools:[]
        ~command:[ "run" ]
        ~timeout_seconds:5);
  rejected (fun () -> spec ~inputs:[ "a.py" ] ~files:[] ~tools:[] ~command:[] ~timeout_seconds:5);
  rejected (fun () ->
      spec ~inputs:[ "a.py" ] ~files:[] ~tools:[] ~command:[ "" ] ~timeout_seconds:5);
  rejected (fun () ->
      spec ~inputs:[ "a.py" ] ~files:[] ~tools:[] ~command:[ "run" ] ~timeout_seconds:0)
