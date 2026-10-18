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

let no_changes = { Outcome.changed_files = []; verification = Verification.Unchecked }

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
          let outcome = { Outcome.changed_files; verification } in
          assert (
            scores ~outcome ~response:None ~task:code_case ()
            = [
                ("correctness", verification = Verification.Passed);
                ("scope", changed_files = [] || changed_files = [ "workspace/source.txt" ]);
              ]))
        [
          Verification.Unchecked;
          Verification.Passed;
          Verification.Failed;
          Verification.Invalid_submission;
          Verification.Timed_out;
        ])
    [ []; [ "workspace/source.txt" ]; [ "workspace/other.txt" ]; [ "../outside" ] ];
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
      fields @ [ field ~name:"extra" ~value:(Result.get_ok (Response_value.create ~bool:true ())) ];
    ];
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
  assert (not (correct ~fields:[ status; safe ] ~task:exact));
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
