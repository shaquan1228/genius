let make_fixture files = Result.get_ok (Fixture.of_files files)
let response fields = Result.get_ok (Response.of_fields fields)
let instruction prompt = Result.get_ok (Construct.instruction ~skill:"reasoning" ~prompt)

let rule field min_words max_words =
  Result.get_ok (Construct.text_rule ~field ~min_words ~max_words)

let checks =
  Result.get_ok
    (Verifier.make
       ~inputs:[ "source.txt" ]
       ~files:[ ("verifier.py", Ast.Inline "private checker") ]
       ~tools:[ ("helper.txt", Ast.Resource "public-helper") ]
       ~command:[ "checker" ]
       ~stdin:"private input"
       ~timeout_seconds:5)

let code ?(fixture = make_fixture [ ("source.txt", "seed"); ("visible.txt", "public check") ])
    ?(allowed_files = [ "source.txt" ])
    ?(reference = Reference.edits (make_fixture [ ("source.txt", "fixed") ])) () =
  Case.make
    ~id:"clear-task"
    ~fixture
    ~instruction:(instruction "Change source.txt only.")
    ~criterion:(Ast.Code checks)
    ~allowed_files
    ~reference

let code_case = Result.get_ok (code ())

let answer_case ?text_rule expected =
  Result.get_ok
    (Case.make
       ~id:"answer"
       ~fixture:Fixture.empty
       ~instruction:(instruction "Reply with the expected fields.")
       ~criterion:(Result.get_ok (Criterion.answer ?text_rule ~expected:(response expected) ()))
       ~allowed_files:[]
       ~reference:{ Ast.edits = Fixture.empty; completion = Plain "reference" })

let decision = answer_case ~text_rule:(rule "reason" 1 40) [ ("choice", Ast.String "B") ]
let no_changes = { Ast.changed_files = []; verification = Ast.Unchecked }

let scores ?(outcome = no_changes) ~response task =
  Result.get_ok (Grader.grade task ~response ~outcome)

let correct fields task = List.assoc "correctness" (scores ~response:(Some (response fields)) task)

let error_codes = function
  | Ok _ -> assert false
  | Error failure -> List.map (fun (issue : Ast.validation_issue) -> issue.code) failure.Ast.issues

let () =
  assert (
    error_codes (code ~fixture:(make_fixture [ ("other.txt", "seed") ]) ())
    = [ Ast.Missing_fixture_inputs ]);
  assert (error_codes (code ~allowed_files:[ "other.txt" ] ()) = [ Ast.Reference_outside_scope ]);
  let tampered =
    Fixture.overlay code_case.fixture ~overrides:(make_fixture [ ("verifier.py", "tampered") ])
  in
  assert (error_codes (code ~fixture:tampered ()) = [ Ast.Artifact_overlap ]);
  assert (error_codes (Construct.instruction ~skill:"" ~prompt:"") = [ Ast.Invalid_identity ]);
  let failure =
    Result.get_error
      (Case.make
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
            scores ~outcome ~response:None code_case
            = [
                ("correctness", verification = Ast.Passed);
                ("scope", changed_files = [] || changed_files = [ "workspace/source.txt" ]);
              ]))
        [ Ast.Unchecked; Ast.Passed; Ast.Failed; Ast.Invalid_submission; Ast.Timed_out ])
    [ []; [ "workspace/source.txt" ]; [ "workspace/other.txt" ]; [ "../outside" ] ];
  assert (
    Grader.grade
      code_case
      ~response:None
      ~outcome:{ no_changes with verification = Ast.Harness_error "offline" }
    = Error (Ast.Verification_harness_error "offline"));
  assert (not (List.assoc "correctness" (scores ~response:None decision)))

let () =
  let fields = [ ("choice", Ast.String "B"); ("reason", Ast.String "Cheaper") ] in
  assert (correct fields decision);
  assert (correct (List.rev fields) decision);
  List.iter
    (fun fields -> assert (not (correct fields decision)))
    [
      [];
      [ ("choice", Ast.String "A"); ("reason", Ast.String "Cheaper") ];
      [ ("choice", Ast.String "B"); ("reason", Ast.String "") ];
      [ ("choice", Ast.String "B"); ("reason", Ast.Bool true) ];
      fields @ [ ("extra", Ast.Bool true) ];
    ];
  let status = ("status", Ast.String "ready") and safe = ("safe", Ast.Bool true) in
  let task = answer_case ~text_rule:(rule "explanation" 2 3) [ status; safe ] in
  List.iter
    (fun (text, accepted) ->
      assert (correct [ status; safe; ("explanation", Ast.String text) ] task = accepted))
    [ ("All good", true); ("All is good", true); ("Good", false); ("All is very good", false) ];
  assert (
    not
      (correct [ status; ("safe", Ast.String "true"); ("explanation", Ast.String "All good") ] task));
  let exact = answer_case [ status ] in
  assert (correct [ status ] exact);
  assert (not (correct [ status; safe ] exact));
  let note = answer_case ~text_rule:(rule "note" 0 0) [] in
  assert (correct [ ("note", Ast.String "") ] note);
  assert (not (correct [ ("note", Ast.String "word") ] note))

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
      assert (Grader.word_count ("first" ^ space ^ "second") = 2);
      assert (Grader.trim (space ^ "first" ^ space) = "first"))
    separators;
  assert (Grader.word_count ("first" ^ utf8 0x200B ^ "second") = 1);
  List.iter
    (fun count ->
      let words = String.concat (utf8 0x2003) (List.init count (fun _ -> "word")) in
      assert (
        correct [ ("choice", Ast.String "B"); ("reason", Ast.String words) ] decision
        = (count >= 1 && count <= 40)))
    [ 0; 1; 40; 41 ]

let () =
  let public = Projection.case code_case in
  assert (public.id = code_case.id);
  assert (public.prompt = code_case.instruction.prompt);
  assert (List.map fst public.files = [ "source.txt"; "visible.txt"; "helper.txt" ]);
  assert (not (List.mem_assoc "verifier.py" public.files));
  assert (List.assoc "helper.txt" public.files = Ast.Resource "public-helper");
  assert (Projection.verifier code_case = Some checks);
  assert (Projection.reference code_case = code_case.reference);
  assert (Projection.verifier decision = None);
  assert ((Projection.case decision).files = []);
  let resolved =
    Result.get_ok
      (Case.resolve_resources code_case ~resources:[ ("public-helper", "public contents") ])
  in
  let resolved_checks = Option.get (Projection.verifier resolved) in
  assert (resolved_checks.tools = [ ("helper.txt", Ast.Inline "public contents") ]);
  assert (checks.tools = [ ("helper.txt", Ast.Resource "public-helper") ]);
  assert (error_codes (Case.resolve_resources code_case ~resources:[]) = [ Ast.Missing_resource ]);
  assert (Case.resolve_resources decision ~resources:[] = Ok decision);
  List.iter
    (fun task -> assert (List.map fst (scores ~response:None task) = Grader.required_names))
    [ code_case; decision ]
