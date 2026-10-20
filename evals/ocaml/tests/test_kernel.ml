let file ~path ~contents = Result.get_ok (File.create ~path ~contents)
let fixture ~files = Result.get_ok (Fixture.create ~files)
let field ~name ~value = Result.get_ok (Response_field.create ~name ~value)
let response ~fields = Result.get_ok (Response.create ~fields)
let instruction ~prompt = Result.get_ok (Instruction.create ~skill:"reasoning" ~prompt)

let rule ~field ~min_words ~max_words =
  Result.get_ok (Text_rule.create ~field ~min_words ~max_words)

let artifact ~path ~content = Result.get_ok (Artifact.create ~path ~content)

let checks =
  Result.get_ok
    (Verifier.create
       ~inputs:[ "source.txt" ]
       ~files:
         [
           artifact
             ~path:"verifier.py"
             ~content:(Result.get_ok (Content.create ~inline:"private checker" ()));
         ]
       ~tools:
         [
           artifact
             ~path:"helper.txt"
             ~content:(Result.get_ok (Content.create ~resource:"public-helper" ()));
         ]
       ~command:[ "checker" ]
       ~stdin:"private input"
       ~timeout_seconds:5)

let code
    ?(initial =
      fixture
        ~files:
          [
            file ~path:"source.txt" ~contents:"seed";
            file ~path:"visible.txt" ~contents:"public check";
          ]) ?(allowed_files = [ "source.txt" ])
    ?(reference =
      {
        Reference.edits = fixture ~files:[ file ~path:"source.txt" ~contents:"fixed" ];
        completion = Result.get_ok (Completion.create ~plain:"fixed" ());
      }) () =
  Task.create
    ~id:"clear-task"
    ~fixture:initial
    ~instruction:(instruction ~prompt:"Change source.txt only.")
    ~criterion:(Result.get_ok (Criterion.create ~code:checks ()))
    ~allowed_files
    ~reference

let code_case = Result.get_ok (code ())

let answer_case ?text_rule ~expected () =
  let rubric = Result.get_ok (Rubric.create ~expected:(response ~fields:expected) ~text_rule) in
  Result.get_ok
    (Task.create
       ~id:"answer"
       ~fixture:Fixture.empty
       ~instruction:(instruction ~prompt:"Reply with the expected fields.")
       ~criterion:(Result.get_ok (Criterion.create ~answer:rubric ()))
       ~allowed_files:[]
       ~reference:
         {
           Reference.edits = Fixture.empty;
           completion = Result.get_ok (Completion.create ~plain:"reference" ());
         })

let decision =
  answer_case
    ~text_rule:(rule ~field:"reason" ~min_words:1 ~max_words:40)
    ~expected:[ field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ())) ]
    ()

let no_changes = Outcome.create ~changed_files:[] ~verification:Verification.Unchecked ()

let () =
  let all checks = Result.get_ok (Predicate.all ~checks) in
  let verification value =
    Value.Record
      { fields = [ ("verification", Value.String { value = Verification.name ~status:value }) ] }
  in
  let verified =
    Result.get_ok
      (Predicate.equals ~path:[ "verification" ] ~expected:(Value.String { value = "passed" }))
  in
  let passed predicate observation =
    Assessment.passed ~assessment:(Assessment.create ~predicate ~observation)
  in
  List.iter
    (fun status ->
      let observation = verification status in
      let yes = all [] and no = Predicate.not_ ~check:(all []) in
      assert (passed verified observation = (status = Verification.Passed));
      assert (
        passed (all [ ("pair", all [ ("a", verified); ("b", yes) ]); ("c", no) ]) observation
        = false);
      assert (
        passed (all [ ("a", verified); ("pair", all [ ("b", yes); ("c", yes) ]) ]) observation
        = (status = Verification.Passed)))
    [ Verification.Passed; Verification.Failed ];
  let scope = Result.get_ok (Predicate.within ~path:[ "changed_files" ] ~allowed:[]) in
  let report =
    Assessment.create
      ~predicate:(all [ ("one", scope); ("two", scope) ])
      ~observation:
        (Value.Record { fields = [ ("changed_files", Value.strings ~values:[ "b"; "a"; "b" ]) ] })
  in
  assert (Assessment.scores ~assessment:report = [ ("one", false); ("two", false) ]);
  (match report with
  | Assessment.All { checks } ->
      assert (
        Assessment.observed ~assessment:(List.assoc "one" checks)
        = Some (Value.strings ~values:[ "b"; "a"; "b" ]))
  | Assessment.Check _ -> assert false);
  assert (Assessment.observed ~assessment:report = None);
  assert (
    Assessment.observed
      ~assessment:
        (Assessment.create ~predicate:(Predicate.not_ ~check:scope) ~observation:Value.Null)
    = None);
  assert (
    Assessment.scores ~assessment:(Assessment.create ~predicate:scope ~observation:Value.Null)
    = [ ("passed", false) ])

let () =
  let same = Result.get_ok (code ()) in
  assert (Task.compare ~before:code_case ~after:same).equal;
  let reordered = fixture ~files:(List.rev (Fixture.files ~fixture:code_case.fixture)) in
  assert (Fixture.compare ~before:code_case.fixture ~after:reordered).equal;
  let same_scope = Result.get_ok (code ~allowed_files:[ "source.txt"; "visible.txt" ] ()) in
  let reordered_scope = Result.get_ok (code ~allowed_files:[ "visible.txt"; "source.txt" ] ()) in
  assert (Task.compare ~before:same_scope ~after:reordered_scope).equal;
  let changed =
    Result.get_ok
      (code
         ~initial:
           (fixture
              ~files:
                [
                  file ~path:"source.txt" ~contents:"changed";
                  file ~path:"added.txt" ~contents:"new";
                ])
         ())
  in
  let difference = Task.compare ~before:code_case ~after:changed in
  assert (not difference.equal);
  assert (List.map (fun (f : File.t) -> f.path) difference.fixture.added = [ "added.txt" ]);
  assert (List.map (fun (f : File.t) -> f.path) difference.fixture.removed = [ "visible.txt" ]);
  assert (List.length difference.fixture.modified = 1);
  assert difference.instruction.equal;
  assert difference.criterion.equal;
  let report =
    Result.get_ok
      (Task.assess
         ~task:decision
         ~response:
           (Some
              (response
                 ~fields:
                   [
                     field
                       ~name:"choice"
                       ~value:(Result.get_ok (Response_value.create ~string:"A" ()));
                     field
                       ~name:"reason"
                       ~value:(Result.get_ok (Response_value.create ~string:"Cheaper" ()));
                   ]))
         ~outcome:{ no_changes with changed_files = [ "unexpected.txt" ] })
  in
  assert (not (Assessment.passed ~assessment:report));
  assert (Assessment.scores ~assessment:report = [ ("correctness", false); ("scope", false) ]);
  match report with
  | Assessment.All { checks } ->
      assert (not (Assessment.passed ~assessment:(List.assoc "correctness" checks)))
  | _ -> assert false

let () =
  let command values =
    Result.get_ok
      (Verifier.create
         ~inputs:checks.inputs
         ~files:checks.files
         ~tools:checks.tools
         ~command:values
         ~stdin:checks.stdin
         ~timeout_seconds:checks.timeout_seconds)
  in
  let before = Result.get_ok (Criterion.create ~code:(command [ "checker"; "flag" ]) ()) in
  let after = Result.get_ok (Criterion.create ~code:(command [ "flag"; "checker" ]) ()) in
  assert ((Criterion.compare ~before ~after).changed_fields = [ "verifier.command" ]);
  assert ((Criterion.compare ~before ~after:decision.criterion).changed_fields = [ "kind" ]);
  let changed =
    {
      Reference.edits = code_case.reference.edits;
      completion = Result.get_ok (Completion.create ~plain:"different" ());
    }
  in
  assert (
    (Reference.compare ~before:code_case.reference ~after:changed).changed_fields = [ "completion" ])

let scores ?(outcome = no_changes) ~response ~task () =
  Result.get_ok (Task.grade ~task ~response ~outcome)

let correct ~fields ~task =
  List.assoc "correctness" (scores ~response:(Some (response ~fields)) ~task ())

let error_codes = function
  | Ok _ -> assert false
  | Error failure ->
      List.map (fun (issue : Validation_issue.t) -> issue.code) failure.Validation_failure.issues

let () =
  assert (
    error_codes (code ~initial:(fixture ~files:[ file ~path:"other.txt" ~contents:"seed" ]) ())
    = [ Validation_code.Missing_fixture_inputs ]);
  assert (
    error_codes (code ~allowed_files:[ "other.txt" ] ())
    = [ Validation_code.Reference_outside_scope ]);
  let tampered =
    Fixture.overlay
      ~base:code_case.fixture
      ~overrides:(fixture ~files:[ file ~path:"verifier.py" ~contents:"tampered" ])
  in
  assert (error_codes (code ~initial:tampered ()) = [ Validation_code.Artifact_overlap ]);
  assert (
    error_codes (Instruction.create ~skill:"" ~prompt:"") = [ Validation_code.Invalid_identity ]);
  let failure =
    Result.get_error
      (Task.create
         ~id:""
         ~fixture:code_case.fixture
         ~instruction:code_case.instruction
         ~criterion:code_case.criterion
         ~allowed_files:code_case.allowed_files
         ~reference:code_case.reference)
  in
  assert (failure.case_id = Some "");
  assert (List.map (fun (issue : Validation_issue.t) -> issue.field) failure.issues = [ "id" ])

let () =
  List.iter
    (fun changed_files ->
      List.iter
        (fun verification ->
          let outcome = Outcome.create ~changed_files ~verification () in
          assert (
            scores ~outcome ~response:None ~task:code_case ()
            = [
                ("correctness", verification = Verification.Passed);
                ("scope", changed_files = [] || changed_files = [ "source.txt" ]);
              ]))
        [
          Verification.Unchecked;
          Verification.Passed;
          Verification.Failed;
          Verification.Invalid_submission;
          Verification.Timed_out;
        ])
    [ []; [ "source.txt" ]; [ "other.txt" ]; [ "../outside" ] ];
  assert (
    Task.grade
      ~task:code_case
      ~response:None
      ~outcome:{ no_changes with verification = Verification.Harness_error { detail = "offline" } }
    = Error (Grading_failure.Verification_harness_error { detail = "offline" }));
  assert (not (List.assoc "correctness" (scores ~response:None ~task:decision ())))

let () =
  let fields =
    [
      field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ()));
      field ~name:"reason" ~value:(Result.get_ok (Response_value.create ~string:"Cheaper" ()));
    ]
  in
  assert (correct ~fields ~task:decision);
  assert (correct ~fields:(List.rev fields) ~task:decision);
  List.iter
    (fun fields -> assert (not (correct ~fields ~task:decision)))
    [
      [];
      [
        field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"A" ()));
        field ~name:"reason" ~value:(Result.get_ok (Response_value.create ~string:"Cheaper" ()));
      ];
      [
        field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ()));
        field ~name:"reason" ~value:(Result.get_ok (Response_value.create ~string:"" ()));
      ];
      [
        field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ()));
        field ~name:"reason" ~value:(Result.get_ok (Response_value.create ~bool:true ()));
      ];
    ];
  assert (
    correct
      ~fields:
        (fields
        @ [ field ~name:"extra" ~value:(Result.get_ok (Response_value.create ~bool:true ())) ])
      ~task:decision);
  let status =
    field ~name:"status" ~value:(Result.get_ok (Response_value.create ~string:"ready" ()))
  and safe = field ~name:"safe" ~value:(Result.get_ok (Response_value.create ~bool:true ())) in
  let task =
    answer_case
      ~text_rule:(rule ~field:"explanation" ~min_words:2 ~max_words:3)
      ~expected:[ status; safe ]
      ()
  in
  List.iter
    (fun (text, accepted) ->
      assert (
        correct
          ~fields:
            [
              status;
              safe;
              field
                ~name:"explanation"
                ~value:(Result.get_ok (Response_value.create ~string:text ()));
            ]
          ~task
        = accepted))
    [ ("All good", true); ("All is good", true); ("Good", false); ("All is very good", false) ];
  assert (
    not
      (correct
         ~fields:
           [
             status;
             field ~name:"safe" ~value:(Result.get_ok (Response_value.create ~string:"true" ()));
             field
               ~name:"explanation"
               ~value:(Result.get_ok (Response_value.create ~string:"All good" ()));
           ]
         ~task));
  let exact = answer_case ~expected:[ status ] () in
  assert (correct ~fields:[ status ] ~task:exact);
  assert (correct ~fields:[ status; safe ] ~task:exact);
  let note =
    answer_case ~text_rule:(rule ~field:"note" ~min_words:0 ~max_words:0) ~expected:[] ()
  in
  assert (
    correct
      ~fields:[ field ~name:"note" ~value:(Result.get_ok (Response_value.create ~string:"" ())) ]
      ~task:note);
  assert (
    not
      (correct
         ~fields:
           [ field ~name:"note" ~value:(Result.get_ok (Response_value.create ~string:"word" ())) ]
         ~task:note))

let utf8 code =
  let buffer = Buffer.create 4 in
  Buffer.add_utf_8_uchar buffer (Uchar.of_int code);
  Buffer.contents buffer

let () =
  let separators =
    List.init 5 (( + ) 9)
    @ List.init 5 (( + ) 28)
    @ [ 133; 160; 5760 ]
    @ List.init 11 (( + ) 8192)
    @ [ 8232; 8233; 8239; 8287; 12288 ]
  in
  List.iter
    (fun code ->
      let space = utf8 code in
      assert (Text_rule.word_count ~text:("first" ^ space ^ "second") = 2);
      assert (Completion.trim ~text:(space ^ "first" ^ space) = "first"))
    separators;
  assert (Text_rule.word_count ~text:("first" ^ utf8 0x200B ^ "second") = 1);
  List.iter
    (fun count ->
      let words = String.concat (utf8 0x2003) (List.init count (fun _ -> "word")) in
      assert (
        correct
          ~fields:
            [
              field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ()));
              field ~name:"reason" ~value:(Result.get_ok (Response_value.create ~string:words ()));
            ]
          ~task:decision
        = (count >= 1 && count <= 40)))
    [ 0; 1; 40; 41 ]

let () =
  let public = Case.create ~task:code_case in
  assert (public.id = code_case.id);
  assert (public.prompt = code_case.instruction.prompt);
  assert (
    List.map (fun (artifact : Artifact.t) -> artifact.path) public.files
    = [ "source.txt"; "visible.txt"; "helper.txt" ]);
  assert (
    not (List.exists (fun (artifact : Artifact.t) -> artifact.path = "verifier.py") public.files));
  assert (Task.verifier ~task:code_case = Some checks);
  assert (Task.verifier ~task:decision = None);
  assert ((Case.create ~task:decision).files = []);
  let resolved =
    Result.get_ok
      (Task.resolve_resources
         ~task:code_case
         ~resources:[ Resource_binding.create ~key:"public-helper" ~contents:"public contents" ])
  in
  let resolved_checks = Option.get (Task.verifier ~task:resolved) in
  assert (
    resolved_checks.tools
    = [
        artifact
          ~path:"helper.txt"
          ~content:(Result.get_ok (Content.create ~inline:"public contents" ()));
      ]);
  assert (
    checks.tools
    = [
        artifact
          ~path:"helper.txt"
          ~content:(Result.get_ok (Content.create ~resource:"public-helper" ()));
      ]);
  assert (
    error_codes (Task.resolve_resources ~task:code_case ~resources:[])
    = [ Validation_code.Missing_resource ]);
  assert (Task.resolve_resources ~task:decision ~resources:[] = Ok decision);
  List.iter
    (fun task -> assert (List.map fst (scores ~response:None ~task ()) = Task.required_scores))
    [ code_case; decision ]

let () =
  let call name =
    Value.Record
      {
        fields =
          [
            ("name", Value.String { value = name });
            ("arguments", Value.Record { fields = [ ("id", Value.Int { value = 7 }) ] });
          ];
      }
  in
  let predicate =
    Result.get_ok
      (Predicate.all
         ~checks:
           [
             ( "looked-up",
               Result.get_ok (Predicate.contains ~path:[ "trace" ] ~item:(call "lookup")) );
             ( "only-lookups",
               Result.get_ok (Predicate.within ~path:[ "trace" ] ~allowed:[ call "lookup" ]) );
             ( "balance",
               Result.get_ok
                 (Predicate.equals ~path:[ "state"; "balance" ] ~expected:(Value.Int { value = 5 }))
             );
             ( "unverified",
               Result.get_ok
                 (Predicate.equals
                    ~path:[ "verification" ]
                    ~expected:(Value.String { value = "unchecked" })) );
             ( "answered",
               Result.get_ok
                 (Predicate.equals
                    ~path:[ "response"; "choice" ]
                    ~expected:(Value.String { value = "B" })) );
           ])
  in
  let criterion = Result.get_ok (Criterion.create ~state:predicate ()) in
  let task =
    Result.get_ok
      (Task.create
         ~id:"tool-task"
         ~fixture:Fixture.empty
         ~instruction:(instruction ~prompt:"Look up account 7 and report its balance.")
         ~criterion
         ~allowed_files:[]
         ~reference:
           {
             Reference.edits = Fixture.empty;
             completion = Result.get_ok (Completion.create ~plain:"5" ());
           })
  in
  assert (Task.verifier ~task = None);
  assert ((Case.create ~task).files = []);
  assert (Task.resolve_resources ~task ~resources:[] = Ok task);
  let state = Value.Record { fields = [ ("balance", Value.Int { value = 5 }) ] } in
  let response =
    Some
      (response
         ~fields:
           [ field ~name:"choice" ~value:(Result.get_ok (Response_value.create ~string:"B" ())) ])
  in
  let scores ~trace ~state ~response =
    Result.get_ok
      (Task.grade
         ~task
         ~response
         ~outcome:
           (Outcome.create
              ~facts:[ ("trace", Value.List { items = trace }); ("state", state) ]
              ~changed_files:[]
              ~verification:Verification.Unchecked
              ()))
  in
  assert (
    scores ~trace:[ call "lookup" ] ~state ~response = [ ("correctness", true); ("scope", true) ]);
  assert (scores ~trace:[] ~state ~response = [ ("correctness", false); ("scope", true) ]);
  assert (
    scores ~trace:[ call "lookup"; call "transfer" ] ~state ~response
    = [ ("correctness", false); ("scope", true) ]);
  assert (
    scores ~trace:[ call "lookup" ] ~state:Value.Null ~response
    = [ ("correctness", false); ("scope", true) ]);
  assert (
    scores ~trace:[ call "lookup" ] ~state ~response:None
    = [ ("correctness", false); ("scope", true) ]);
  let report =
    Result.get_ok
      (Task.assess
         ~task
         ~response:None
         ~outcome:
           (Outcome.create
              ~facts:[ ("trace", Value.List { items = [ call "lookup" ] }); ("state", state) ]
              ~changed_files:[]
              ~verification:Verification.Unchecked
              ()))
  in
  (match report with
  | Assessment.All { checks } -> (
      match List.assoc "correctness" checks with
      | Assessment.All { checks } ->
          assert (
            List.map (fun (name, check) -> (name, Assessment.passed ~assessment:check)) checks
            = [
                ("looked-up", true);
                ("only-lookups", true);
                ("balance", true);
                ("unverified", true);
                ("answered", false);
              ]);
          assert (Assessment.observed ~assessment:(List.assoc "answered" checks) = None);
          assert (
            Assessment.observed ~assessment:(List.assoc "balance" checks)
            = Some (Value.Int { value = 5 }))
      | Assessment.Check _ -> assert false)
  | Assessment.Check _ -> assert false);
  assert (Result.is_error (Criterion.create ~state:predicate ~code:checks ()));
  assert (Criterion.compare ~before:criterion ~after:criterion).equal;
  assert (
    (Criterion.compare ~before:criterion ~after:decision.criterion).changed_fields = [ "kind" ]);
  let other =
    Result.get_ok (Criterion.create ~state:(Result.get_ok (Predicate.all ~checks:[])) ())
  in
  assert ((Criterion.compare ~before:criterion ~after:other).changed_fields = [ "state.predicate" ]);
  assert (
    Task.grade
      ~task
      ~response:None
      ~outcome:
        (Outcome.create
           ~changed_files:[]
           ~verification:(Verification.Harness_error { detail = "offline" })
           ())
    = Error (Grading_failure.Verification_harness_error { detail = "offline" }));
  assert (Verification.name ~status:(Verification.Harness_error { detail = "x" }) = "harness_error");
  assert (Verification.name ~status:Verification.Timed_out = "timed_out");
  assert (Verification.name ~status:Verification.Invalid_submission = "invalid_submission");
  assert (Verification.name ~status:Verification.Failed = "failed");
  assert (
    Criterion.condition ~criterion:code_case.criterion
    = Result.get_ok
        (Predicate.equals ~path:[ "verification" ] ~expected:(Value.String { value = "passed" })))
