let file ~path ~contents = Result.get_ok (Construct.file ~path ~contents)
let fixture ~files = Result.get_ok (Construct.fixture ~files)
let field ~name ~value = Result.get_ok (Construct.response_field ~name ~value)
let response ~fields = Result.get_ok (Construct.response ~fields)
let instruction ~prompt = Result.get_ok (Construct.instruction ~skill:"reasoning" ~prompt)

let rule ~field ~min_words ~max_words =
  Result.get_ok (Construct.text_rule ~field ~min_words ~max_words)

let artifact ~path ~content = Result.get_ok (Construct.artifact ~path ~content)

let checks =
  Result.get_ok
    (Construct.verifier
       ~inputs:[ "source.txt" ]
       ~files:[ artifact ~path:"verifier.py" ~content:(Ast.Inline { text = "private checker" }) ]
       ~tools:[ artifact ~path:"helper.txt" ~content:(Ast.Resource { key = "public-helper" }) ]
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
        Ast.edits = fixture ~files:[ file ~path:"source.txt" ~contents:"fixed" ];
        completion = Plain { text = "fixed" };
      }) () =
  Construct.task
    ~id:"clear-task"
    ~fixture:initial
    ~instruction:(instruction ~prompt:"Change source.txt only.")
    ~criterion:(Ast.Code { verifier = checks })
    ~allowed_files
    ~reference

let code_case = Result.get_ok (code ())

let answer_case ?text_rule ~expected () =
  let rubric = Result.get_ok (Construct.rubric ~expected:(response ~fields:expected) ~text_rule) in
  Result.get_ok
    (Construct.task
       ~id:"answer"
       ~fixture:Fixture.empty
       ~instruction:(instruction ~prompt:"Reply with the expected fields.")
       ~criterion:(Ast.Answer { rubric })
       ~allowed_files:[]
       ~reference:{ Ast.edits = Fixture.empty; completion = Plain { text = "reference" } })

let decision =
  answer_case
    ~text_rule:(rule ~field:"reason" ~min_words:1 ~max_words:40)
    ~expected:[ field ~name:"choice" ~value:(Ast.String { value = "B" }) ]
    ()

let no_changes = { Ast.changed_files = []; verification = Ast.Unchecked }

let scores ?(outcome = no_changes) ~response ~task () =
  Result.get_ok (Grader.grade ~task ~response ~outcome)

let correct ~fields ~task =
  List.assoc "correctness" (scores ~response:(Some (response ~fields)) ~task ())

let error_codes = function
  | Ok _ -> assert false
  | Error failure -> List.map (fun (issue : Ast.validation_issue) -> issue.code) failure.Ast.issues

let () =
  assert (
    error_codes (code ~initial:(fixture ~files:[ file ~path:"other.txt" ~contents:"seed" ]) ())
    = [ Ast.Missing_fixture_inputs ]);
  assert (error_codes (code ~allowed_files:[ "other.txt" ] ()) = [ Ast.Reference_outside_scope ]);
  let tampered =
    Fixture.overlay
      ~base:code_case.fixture
      ~overrides:(fixture ~files:[ file ~path:"verifier.py" ~contents:"tampered" ])
  in
  assert (error_codes (code ~initial:tampered ()) = [ Ast.Artifact_overlap ]);
  assert (error_codes (Construct.instruction ~skill:"" ~prompt:"") = [ Ast.Invalid_identity ]);
  let failure =
    Result.get_error
      (Construct.task
         ~id:""
         ~fixture:code_case.fixture
         ~instruction:code_case.instruction
         ~criterion:code_case.criterion
         ~allowed_files:code_case.allowed_files
         ~reference:code_case.reference)
  in
  assert (failure.case_id = Some "");
  assert (List.map (fun (issue : Ast.validation_issue) -> issue.field) failure.issues = [ "id" ])

let () =
  List.iter
    (fun changed_files ->
      List.iter
        (fun verification ->
          let outcome = { Ast.changed_files; verification } in
          assert (
            scores ~outcome ~response:None ~task:code_case ()
            = [
                ("correctness", verification = Ast.Passed);
                ("scope", changed_files = [] || changed_files = [ "workspace/source.txt" ]);
              ]))
        [ Ast.Unchecked; Ast.Passed; Ast.Failed; Ast.Invalid_submission; Ast.Timed_out ])
    [ []; [ "workspace/source.txt" ]; [ "workspace/other.txt" ]; [ "../outside" ] ];
  assert (
    Grader.grade
      ~task:code_case
      ~response:None
      ~outcome:{ no_changes with verification = Ast.Harness_error { detail = "offline" } }
    = Error (Ast.Verification_harness_error { detail = "offline" }));
  assert (not (List.assoc "correctness" (scores ~response:None ~task:decision ())))

let () =
  let fields =
    [
      field ~name:"choice" ~value:(Ast.String { value = "B" });
      field ~name:"reason" ~value:(Ast.String { value = "Cheaper" });
    ]
  in
  assert (correct ~fields ~task:decision);
  assert (correct ~fields:(List.rev fields) ~task:decision);
  List.iter
    (fun fields -> assert (not (correct ~fields ~task:decision)))
    [
      [];
      [
        field ~name:"choice" ~value:(Ast.String { value = "A" });
        field ~name:"reason" ~value:(Ast.String { value = "Cheaper" });
      ];
      [
        field ~name:"choice" ~value:(Ast.String { value = "B" });
        field ~name:"reason" ~value:(Ast.String { value = "" });
      ];
      [
        field ~name:"choice" ~value:(Ast.String { value = "B" });
        field ~name:"reason" ~value:(Ast.Bool { value = true });
      ];
      fields @ [ field ~name:"extra" ~value:(Ast.Bool { value = true }) ];
    ];
  let status = field ~name:"status" ~value:(Ast.String { value = "ready" })
  and safe = field ~name:"safe" ~value:(Ast.Bool { value = true }) in
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
          ~fields:[ status; safe; field ~name:"explanation" ~value:(Ast.String { value = text }) ]
          ~task
        = accepted))
    [ ("All good", true); ("All is good", true); ("Good", false); ("All is very good", false) ];
  assert (
    not
      (correct
         ~fields:
           [
             status;
             field ~name:"safe" ~value:(Ast.String { value = "true" });
             field ~name:"explanation" ~value:(Ast.String { value = "All good" });
           ]
         ~task));
  let exact = answer_case ~expected:[ status ] () in
  assert (correct ~fields:[ status ] ~task:exact);
  assert (not (correct ~fields:[ status; safe ] ~task:exact));
  let note =
    answer_case ~text_rule:(rule ~field:"note" ~min_words:0 ~max_words:0) ~expected:[] ()
  in
  assert (correct ~fields:[ field ~name:"note" ~value:(Ast.String { value = "" }) ] ~task:note);
  assert (
    not (correct ~fields:[ field ~name:"note" ~value:(Ast.String { value = "word" }) ] ~task:note))

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
      assert (Grader.word_count ~text:("first" ^ space ^ "second") = 2);
      assert (Grader.trim ~text:(space ^ "first" ^ space) = "first"))
    separators;
  assert (Grader.word_count ~text:("first" ^ utf8 0x200B ^ "second") = 1);
  List.iter
    (fun count ->
      let words = String.concat (utf8 0x2003) (List.init count (fun _ -> "word")) in
      assert (
        correct
          ~fields:
            [
              field ~name:"choice" ~value:(Ast.String { value = "B" });
              field ~name:"reason" ~value:(Ast.String { value = words });
            ]
          ~task:decision
        = (count >= 1 && count <= 40)))
    [ 0; 1; 40; 41 ]

let () =
  let public = Projection.case ~task:code_case in
  assert (public.id = code_case.id);
  assert (public.prompt = code_case.instruction.prompt);
  assert (
    List.map (fun (artifact : Ast.artifact) -> artifact.path) public.files
    = [ "source.txt"; "visible.txt"; "helper.txt" ]);
  assert (
    not (List.exists (fun (artifact : Ast.artifact) -> artifact.path = "verifier.py") public.files));
  assert (Projection.verifier ~task:code_case = Some checks);
  assert (Projection.reference ~task:code_case = code_case.reference);
  assert (Projection.verifier ~task:decision = None);
  assert ((Projection.case ~task:decision).files = []);
  let resolved =
    Result.get_ok
      (Case.resolve_resources
         ~task:code_case
         ~resources:[ Construct.resource_binding ~key:"public-helper" ~contents:"public contents" ])
  in
  let resolved_checks = Option.get (Projection.verifier ~task:resolved) in
  assert (
    resolved_checks.tools
    = [ artifact ~path:"helper.txt" ~content:(Ast.Inline { text = "public contents" }) ]);
  assert (
    checks.tools = [ artifact ~path:"helper.txt" ~content:(Ast.Resource { key = "public-helper" }) ]);
  assert (
    error_codes (Case.resolve_resources ~task:code_case ~resources:[]) = [ Ast.Missing_resource ]);
  assert (Case.resolve_resources ~task:decision ~resources:[] = Ok decision);
  List.iter
    (fun task -> assert (List.map fst (scores ~response:None ~task ()) = Grader.required_names))
    [ code_case; decision ]
