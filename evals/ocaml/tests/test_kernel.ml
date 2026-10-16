(* Kernel tests use inert values; no candidate-language runtime is required. *)
let checks =
  Verifier.make
    ~inputs:[ "source.txt" ]
    ~files:[ ("verifier.py", Ast.Inline "private checker") ]
    ~tools:[ ("helper.txt", Ast.Resource "public-helper") ]
    ~command:[ "checker" ]
    ~stdin:"private input"
    ~timeout_seconds:5

let code_case =
  Case.make
    ~id:"clear-task"
    ~fixture:(Fixture.of_files [ ("source.txt", "seed"); ("visible.txt", "public check") ])
    ~instruction:{ Ast.skill = "reasoning"; prompt = "Change source.txt only." }
    ~criterion:(Ast.Code checks)
    ~allowed_files:[ "source.txt" ]
    ~reference:(Reference.edits (Fixture.of_files [ ("source.txt", "fixed") ]))

let decision ~id ~choice =
  let expected = Response.of_fields [ ("choice", Ast.String choice) ] in
  Case.make
    ~id
    ~fixture:Fixture.empty
    ~instruction:{ Ast.skill = "reasoning"; prompt = "Reply with choice and reason." }
    ~criterion:
      (Criterion.answer
         ~expected
         ~text_rule:{ Ast.field = "reason"; min_words = 1; max_words = 40 }
         ())
    ~allowed_files:[]
    ~reference:
      {
        Ast.edits = Fixture.empty;
        completion =
          Structured
            (Response.of_fields
               [ ("choice", Ast.String choice); ("reason", Ast.String "Cheaper.") ]);
      }

let review =
  let fields = [ ("decision_was_supported", Ast.Bool true); ("change_rule", Ast.Bool false) ] in
  Case.make
    ~id:"decision-review"
    ~fixture:Fixture.empty
    ~instruction:
      {
        Ast.skill = "reasoning";
        prompt = "Reply with decision_was_supported, change_rule and reason.";
      }
    ~criterion:
      (Criterion.answer
         ~expected:(Response.of_fields fields)
         ~text_rule:{ Ast.field = "reason"; min_words = 1; max_words = 40 }
         ())
    ~allowed_files:[]
    ~reference:
      {
        Ast.edits = Fixture.empty;
        completion =
          Structured (Response.of_fields (fields @ [ ("reason", Ast.String "Same odds.") ]));
      }

let cases = [ code_case; decision ~id:"small-decision" ~choice:"B"; review ]
let find id = List.find (fun (case : Ast.case) -> case.id = id) cases
let no_changes = { Ast.changed_files = []; verification = Unchecked }
let scores ?(outcome = no_changes) ~response case = Grader.grade case ~response ~outcome

let correct ~fields case =
  List.assoc "correctness" (scores ~response:(Some (Response.of_fields fields)) case)

let answer_case ?text_rule expected =
  Case.make
    ~id:"answer"
    ~fixture:Fixture.empty
    ~instruction:{ Ast.skill = "reasoning"; prompt = "Custom answer" }
    ~criterion:(Criterion.answer ?text_rule ~expected:(Response.of_fields expected) ())
    ~allowed_files:[]
    ~reference:{ Ast.edits = Fixture.empty; completion = Plain "reference" }

let utf8 code =
  let buffer = Buffer.create 4 in
  Buffer.add_utf_8_uchar buffer (Uchar.of_int code);
  Buffer.contents buffer

let words count = List.init count (fun _ -> "word")

let contains text ~fragment =
  let width = String.length fragment in
  let rec from index =
    index + width <= String.length text
    && (String.sub text index width = fragment || from (index + 1))
  in
  from 0

let rejection construct =
  try
    ignore (construct ());
    ""
  with Invalid_argument message -> message

let () =
  let original = List.hd cases in
  let changed =
    {
      original with
      Ast.instruction = { skill = "reasoning"; prompt = "A different instruction" };
      criterion = Ast.Code { checks with stdin = "different private input" };
      allowed_files = [];
    }
  in
  assert (List.length cases = 3);
  assert (Fixture.files changed.fixture = Fixture.files original.fixture);
  assert (changed.allowed_files = []);
  assert (original.allowed_files = [ "source.txt" ])

let () =
  let mismatch ~fixture ~allowed_files () =
    Case.make
      ~id:"mismatch"
      ~fixture
      ~instruction:code_case.instruction
      ~criterion:(Ast.Code checks)
      ~allowed_files
      ~reference:code_case.reference
  in
  assert (
    rejection
      (mismatch
         ~fixture:(Fixture.of_files [ ("other.txt", "seed") ])
         ~allowed_files:[ "source.txt" ])
    = "Case mismatch: criteria read files missing from the fixture: source.txt");
  assert (
    rejection (mismatch ~fixture:code_case.fixture ~allowed_files:[ "other.txt" ])
    = "Case mismatch: reference edits files outside allowed_files: source.txt")

let () =
  List.iter
    (fun (case : Ast.case) ->
      let fields =
        match case.criterion with
        | Ast.Answer { expected; text_rule } -> (
            List.map fst (Response.fields expected)
            @ match text_rule with Some rule -> [ rule.field ] | None -> [])
        | Ast.Code _ -> []
      in
      List.iter
        (fun name -> assert (contains case.instruction.prompt ~fragment:name))
        (case.allowed_files @ fields))
    cases

let () =
  List.iter
    (fun (case : Ast.case) ->
      match (case.criterion, case.reference.completion) with
      | Ast.Answer _, Ast.Structured reply -> assert (correct ~fields:(Response.fields reply) case)
      | _ -> ())
    cases

let () =
  let receipt = find "clear-task" in
  List.iter
    (fun changed_files ->
      List.iter
        (fun code_passed ->
          let outcome =
            { Ast.changed_files; verification = (if code_passed then Passed else Failed) }
          in
          assert (
            scores ~outcome ~response:None receipt
            = [
                ("correctness", code_passed);
                ("scope", changed_files = [] || changed_files = [ "workspace/source.txt" ]);
              ]))
        [ false; true ])
    [ []; [ "workspace/source.txt" ]; [ "workspace/extra.ml" ]; [ "instructions/SKILL.md" ] ]

let () =
  let decision = find "small-decision" in
  assert (not (List.assoc "correctness" (scores ~response:None decision)));
  List.iter
    (fun fields -> assert (not (correct ~fields decision)))
    [
      [];
      [ ("choice", Ast.String "A"); ("reason", Ast.String "Cheaper") ];
      [ ("choice", Ast.String "B"); ("reason", Ast.String "") ];
      [ ("choice", Ast.String "B"); ("reason", Ast.String (String.concat " " (words 41))) ];
      [ ("choice", Ast.String "B"); ("reason", Ast.String "Cheap"); ("extra", Ast.Bool true) ];
    ];
  let review = find "decision-review" in
  List.iter
    (fun (supported, change_rule) ->
      assert (
        not
          (correct
             ~fields:
               [
                 ("decision_was_supported", supported);
                 ("change_rule", change_rule);
                 ("reason", Ast.String "One loss.");
               ]
             review)))
    [
      (Ast.Bool false, Ast.Bool false);
      (Ast.Bool false, Ast.Bool true);
      (Ast.Bool true, Ast.Bool true);
      (Ast.String "true", Ast.String "false");
    ]

let () =
  List.iter
    (fun (id, fields) ->
      List.iter
        (fun count ->
          let reason = Ast.String (String.concat (utf8 0x2003) (words count)) in
          assert (
            correct ~fields:(fields @ [ ("reason", reason) ]) (find id) = (1 <= count && count <= 40)))
        [ 0; 1; 40; 41 ])
    [
      ("small-decision", [ ("choice", Ast.String "B") ]);
      ( "decision-review",
        [ ("decision_was_supported", Ast.Bool true); ("change_rule", Ast.Bool false) ] );
    ]

let () =
  let separators =
    List.init 5 (( + ) 9)
    @ List.init 5 (( + ) 28)
    @ [ 133; 160; 5760 ]
    @ List.init 11 (( + ) 8192)
    @ [ 8232; 8233; 8239; 8287; 12288 ]
  in
  let count code = Grader.word_count ("first" ^ utf8 code ^ "second") in
  List.iter (fun code -> assert (count code = 2)) separators;
  assert (count 0x200B = 1)

let () =
  let status = ("status", Ast.String "ready") and safe = ("safe", Ast.Bool true) in
  let shaped =
    answer_case
      ~text_rule:{ Ast.field = "explanation"; min_words = 2; max_words = 3 }
      [ status; safe ]
  in
  let explained text = [ status; safe; ("explanation", Ast.String text) ] in
  assert (correct ~fields:(explained "All good") shaped);
  assert (correct ~fields:(explained "All is good") shaped);
  assert (not (correct ~fields:(explained "Good") shaped));
  assert (not (correct ~fields:(explained "All is very good") shaped));
  assert (
    not
      (correct
         ~fields:[ status; ("safe", Ast.String "true"); ("explanation", Ast.String "All good") ]
         shaped));
  List.iter
    (fun field ->
      let exact = answer_case [ field ] in
      assert (correct ~fields:[ field ] exact);
      assert (not (correct ~fields:[ field; ("extra", Ast.String "value") ] exact)))
    [ status; ("reason", Ast.String "exact") ];
  let note = answer_case ~text_rule:{ Ast.field = "note"; min_words = 0; max_words = 0 } [] in
  assert (correct ~fields:[ ("note", Ast.String "") ] note);
  List.iter
    (fun fields -> assert (not (correct ~fields note)))
    [ []; [ ("note", Ast.Bool true) ]; [ ("note", Ast.String "word") ] ]

let () =
  let case = decision ~id:"new-choice" ~choice:"A" in
  (match case.reference.completion with
  | Ast.Structured reply -> assert (correct ~fields:(Response.fields reply) case)
  | Ast.Plain _ -> assert false);
  assert (
    not (correct ~fields:[ ("choice", Ast.String "B"); ("reason", Ast.String "Cheaper.") ] case))

let () =
  let original = find "clear-task" in
  let fixture =
    Fixture.overlay original.fixture ~overrides:(Fixture.of_files [ ("verifier.py", "tampered") ])
  in
  assert (
    rejection (fun () ->
        Case.make
          ~id:original.id
          ~fixture
          ~instruction:original.instruction
          ~criterion:original.criterion
          ~allowed_files:original.allowed_files
          ~reference:original.reference)
    = "Case clear-task: verifier artifacts overlap fixture")

let () =
  let original = find "clear-task" in
  assert (
    rejection (fun () -> Case.validate { original with fixture = Fixture.empty })
    = "Case clear-task: criteria read files missing from the fixture: source.txt")

let () =
  let original = find "clear-task" in
  let public = Projection.case original in
  assert (public.id = original.id);
  assert (public.prompt = original.instruction.prompt);
  assert (List.map fst public.files = [ "source.txt"; "visible.txt"; "helper.txt" ]);
  assert (not (List.mem_assoc "verifier.py" public.files));
  assert (List.assoc "helper.txt" public.files = Ast.Resource "public-helper");
  (match Projection.verifier original with
  | Some verifier ->
      assert (List.map fst verifier.files = [ "verifier.py" ]);
      assert (verifier.stdin <> "");
      assert (verifier.inputs = [ "source.txt" ])
  | None -> assert false);
  assert (Projection.reference original = original.reference);
  let decision = find "small-decision" in
  assert (Projection.verifier decision = None);
  assert ((Projection.case decision).files = []);
  assert (Projection.reference decision = decision.reference);
  assert (
    rejection (fun () -> Projection.case { original with fixture = Fixture.empty })
    = "Case clear-task: criteria read files missing from the fixture: source.txt")

(* Ast values can be assembled directly; every consuming boundary validates them. *)
let reject_raw_case case =
  List.iter
    (fun consume -> assert (rejection (fun () -> consume case) <> ""))
    [
      (fun case -> ignore (Projection.case case));
      (fun case -> ignore (Projection.verifier case));
      (fun case -> ignore (Projection.reference case));
      (fun case -> ignore (Grader.grade case ~response:None ~outcome:no_changes));
    ]

let () =
  let code = find "clear-task" in
  let checks =
    match code.criterion with Ast.Code checks -> checks | Ast.Answer _ -> assert false
  in
  List.iter
    (fun checks -> reject_raw_case { code with criterion = Ast.Code checks })
    [
      { checks with timeout_seconds = 0 }; { checks with command = [] }; { checks with inputs = [] };
    ];
  let answer = find "small-decision" in
  List.iter
    (fun criterion -> reject_raw_case { answer with criterion })
    [
      Ast.Answer { expected = []; text_rule = None };
      Ast.Answer { expected = [ ("x", Ast.Bool true); ("x", Ast.Bool false) ]; text_rule = None };
      Ast.Answer
        { expected = []; text_rule = Some { field = "note"; min_words = 2; max_words = 1 } };
    ];
  reject_raw_case
    {
      answer with
      reference = { answer.reference with completion = Ast.Structured [ ("", Ast.Bool true) ] };
    }
