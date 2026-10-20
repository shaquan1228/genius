open Task

let s value = Value.String { value }
let file path contents = { path; contents }
let instruction prompt = { skill = "reasoning"; prompt }
let ok result = Result.get_ok result

let checks =
  {
    inputs = [ "source.txt" ];
    files = [ file "verifier.py" "private checker" ];
    tools = [ file "helper.txt" "public helper" ];
    command = [ "checker" ];
    stdin = "private input";
    timeout_seconds = 5;
  }

let code =
  ok
    (Task.create
       ~id:"clear-task"
       ~fixture:[ file "source.txt" "seed"; file "visible.txt" "public check" ]
       ~instruction:(instruction "Change source.txt only.")
       ~criterion:(Code { verifier = checks })
       ~allowed_files:[ "source.txt" ]
       ~reference:{ edits = [ file "source.txt" "fixed" ]; completion = s "fixed" })

let answer ?text_rule expected =
  Task.create
    ~id:"answer"
    ~fixture:[]
    ~instruction:(instruction "Reply with the expected fields.")
    ~criterion:(Answer { rubric = { expected; text_rule } })
    ~allowed_files:[]
    ~reference:{ edits = []; completion = Value.Null }

let decision =
  ok (answer ~text_rule:{ field = "reason"; min_words = 1; max_words = 40 } [ ("choice", s "B") ])

let call name =
  Value.Record
    {
      fields =
        [
          ("name", s name);
          ("arguments", Value.Record { fields = [ ("id", Value.Int { value = 7 }) ] });
        ];
    }

let tool =
  ok
    (Task.create
       ~id:"tool-task"
       ~fixture:[]
       ~instruction:(instruction "Look up account 7 and report its balance.")
       ~criterion:
         (State
            {
              predicate =
                Predicate.All
                  {
                    checks =
                      [
                        ( "looked-up",
                          Predicate.Contains { path = [ "trace" ]; item = call "lookup" } );
                        ( "only-lookups",
                          Predicate.Within { path = [ "trace" ]; allowed = [ call "lookup" ] } );
                        ( "balance",
                          Predicate.Equals
                            { path = [ "state"; "balance" ]; expected = Value.Int { value = 5 } } );
                        ( "no-refund",
                          Predicate.Not
                            { check = Predicate.Present { path = [ "state"; "refund" ] } } );
                        ( "answered",
                          Predicate.Equals { path = [ "response"; "choice" ]; expected = s "B" } );
                      ];
                  };
            })
       ~allowed_files:[]
       ~reference:{ edits = []; completion = s "5" })

let out ?(changed_files = []) ?(response = Value.Null) ?(facts = []) verification =
  Outcome.create ~changed_files ~response ~facts ~verification ()

let grade task outcome = ok (Task.grade ~task ~outcome)
let fields problems = List.map (fun (issue : Failure.issue) -> issue.field) problems.Failure.issues
let rejected result = match result with Ok _ -> assert false | Error failure -> fields failure

let () =
  (* Projection hides private material and exposes public tools. *)
  let public = Task.project ~task:code in
  assert (public.case_id = "clear-task" && public.prompt = code.instruction.prompt);
  assert (List.map (fun f -> f.path) public.files = [ "source.txt"; "visible.txt"; "helper.txt" ]);
  assert (Task.checks ~task:code = Some checks && Task.checks ~task:decision = None);
  assert ((Task.project ~task:decision).files = []);
  (* Code criteria grade on verification; scope on changed files relative to the workspace. *)
  List.iter
    (fun changed_files ->
      List.iter
        (fun verification ->
          assert (
            grade code (out ~changed_files verification)
            = [
                ("correctness", verification = Outcome.Passed);
                ("scope", changed_files = [] || changed_files = [ "source.txt" ]);
              ]))
        [
          Outcome.Unchecked;
          Outcome.Passed;
          Outcome.Failed;
          Outcome.Invalid_submission;
          Outcome.Timed_out;
        ])
    [ []; [ "source.txt" ]; [ "other.txt" ]; [ "../outside" ] ];
  assert (
    Task.grade ~task:code ~outcome:(out (Outcome.Harness_error { detail = "offline" }))
    = Error (Failure.Verification_harness_error { detail = "offline" }));
  assert (List.map fst (grade code (out Outcome.Unchecked)) = Task.required_scores)

let () =
  (* Answer criteria grade response fields and the text rule; extra fields are allowed. *)
  let reply fields = Value.Record { fields } in
  let correct fields task =
    List.assoc "correctness" (grade task (out ~response:(reply fields) Outcome.Unchecked))
  in
  assert (correct [ ("choice", s "B"); ("reason", s "Cheaper") ] decision);
  assert (
    correct
      [ ("reason", s "Cheaper"); ("choice", s "B"); ("extra", Value.Bool { value = true }) ]
      decision);
  List.iter
    (fun fields -> assert (not (correct fields decision)))
    [
      [];
      [ ("choice", s "A"); ("reason", s "Cheaper") ];
      [ ("choice", s "B"); ("reason", s "") ];
      [ ("choice", s "B"); ("reason", Value.Bool { value = true }) ];
    ];
  assert (not (List.assoc "correctness" (grade decision (out Outcome.Unchecked))));
  let words count = String.concat " " (List.init count (fun _ -> "word")) in
  List.iter
    (fun count ->
      assert (
        correct [ ("choice", s "B"); ("reason", s (words count)) ] decision
        = (count >= 1 && count <= 40)))
    [ 0; 1; 40; 41 ];
  let note = ok (answer ~text_rule:{ field = "note"; min_words = 0; max_words = 0 } []) in
  assert (correct [ ("note", s "") ] note && not (correct [ ("note", s "word") ] note))

let () =
  (* State criteria grade open facts: tool traces and environment state. *)
  let state = Value.Record { fields = [ ("balance", Value.Int { value = 5 }) ] } in
  let facts ?(trace = [ call "lookup" ]) ?(state = state) () =
    [ ("trace", Value.List { items = trace }); ("state", state) ]
  in
  let reply = Value.Record { fields = [ ("choice", s "B") ] } in
  let scores ?trace ?state ?(response = reply) () =
    grade tool (out ~response ~facts:(facts ?trace ?state ()) Outcome.Unchecked)
  in
  assert (scores () = [ ("correctness", true); ("scope", true) ]);
  assert (scores ~trace:[] () = [ ("correctness", false); ("scope", true) ]);
  assert (
    scores ~trace:[ call "lookup"; call "refund" ] () = [ ("correctness", false); ("scope", true) ]);
  assert (scores ~state:Value.Null () = [ ("correctness", false); ("scope", true) ]);
  assert (scores ~response:Value.Null () = [ ("correctness", false); ("scope", true) ]);
  match ok (Task.assess ~task:tool ~outcome:(out ~facts:(facts ()) Outcome.Unchecked)) with
  | Assessment.All { checks } -> (
      match List.assoc "correctness" checks with
      | Assessment.All { checks } ->
          assert (
            List.map (fun (name, check) -> (name, Assessment.passed ~assessment:check)) checks
            = [
                ("looked-up", true);
                ("only-lookups", true);
                ("balance", true);
                ("no-refund", true);
                ("answered", false);
              ]);
          assert (
            Assessment.observed ~assessment:(List.assoc "balance" checks)
            = Some (Value.Int { value = 5 }));
          assert (Assessment.observed ~assessment:(List.assoc "no-refund" checks) = None);
          assert (Assessment.scores ~assessment:(List.assoc "balance" checks) = [ ("passed", true) ])
      | Assessment.Check _ -> assert false)
  | Assessment.Check _ -> assert false

let () =
  (* Declarations fail closed with every problem named. *)
  let copy ?(id = code.id) ?(fixture = code.fixture) ?(criterion = code.criterion)
      ?(allowed_files = code.allowed_files) ?(reference = code.reference) () =
    Task.create ~id ~fixture ~instruction:code.instruction ~criterion ~allowed_files ~reference
  in
  let with_checks f = Code { verifier = f checks } in
  assert (rejected (copy ~id:"" ()) = [ "id" ]);
  assert (rejected (copy ~allowed_files:[] ()) = [ "reference.edits" ]);
  assert (rejected (copy ~fixture:[ file "other.txt" "seed" ] ()) = [ "verifier.inputs" ]);
  assert (
    rejected (copy ~fixture:(file "verifier.py" "tampered" :: code.fixture) ()) = [ "verifier" ]);
  assert (
    rejected (copy ~fixture:[ file "../bad" "x"; file "source.txt" "seed" ] ()) = [ "fixture" ]);
  assert (
    rejected (copy ~fixture:[ file "source.txt" "a"; file "source.txt" "b" ] ()) = [ "fixture" ]);
  assert (
    rejected (copy ~criterion:(with_checks (fun c -> { c with inputs = [] })) ())
    = [ "verifier.inputs" ]);
  assert (
    rejected (copy ~criterion:(with_checks (fun c -> { c with command = [ "" ] })) ())
    = [ "verifier.command" ]);
  assert (
    rejected (copy ~criterion:(with_checks (fun c -> { c with timeout_seconds = 0 })) ())
    = [ "verifier.timeout_seconds" ]);
  assert (
    rejected (copy ~criterion:(with_checks (fun c -> { c with tools = [ file "/secret" "x" ] })) ())
    = [ "verifier" ]);
  assert (
    rejected
      (copy ~criterion:(with_checks (fun c -> { c with files = [ file "source.txt" "x" ] })) ())
    = [ "verifier"; "verifier" ]);
  assert (rejected (answer []) = [ "rubric" ]);
  assert (
    rejected
      (answer ~text_rule:{ field = "choice"; min_words = 0; max_words = 2 } [ ("choice", s "B") ])
    = [ "rubric.text_rule" ]);
  assert (
    rejected (answer ~text_rule:{ field = "reason"; min_words = 3; max_words = 2 } [])
    = [ "rubric.text_rule" ]);
  (match copy ~id:"" () with
  | Error failure -> assert (failure.case_id = Some "")
  | Ok _ -> assert false);
  assert (Result.is_error (Experiment.resolve ~epochs:0 ()));
  assert ((ok (Experiment.resolve ())).epochs = Experiment.default.epochs)
