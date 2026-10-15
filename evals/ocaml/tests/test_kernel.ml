let find id = List.find (fun (case : Case.t) -> case.id = id) Suite.cases
let no_changes = Outcome.make ~changed_files:[] ~verification:Outcome.Unchecked

let scores ?(outcome = no_changes) ~response case =
  Score.fields (Grader.grade case ~response ~outcome)

let correct ~fields case =
  List.assoc "correctness" (scores ~response:(Some (Response.of_fields fields)) case)

let answer_case ?text_rule expected =
  Case.make
    ~id:"answer"
    ~fixture:Fixture.empty
    ~instruction:(Instruction.make ~skill:"reasoning" ~prompt:"Custom answer")
    ~criterion:(Criterion.answer ?text_rule ~expected:(Response.of_fields expected) ())
    ~allowed_files:[]
    ~reference:(Reference.make (Plain "reference"))

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
  let original = List.hd Suite.cases in
  let changed =
    {
      original with
      Case.instruction = Instruction.make ~skill:"reasoning" ~prompt:"A different instruction";
      criterion = Scenarios.Receipt.(totals [ expect ~items:[] ~total:99.0 ]);
      allowed_files = [];
    }
  in
  assert (List.length Suite.cases = 4);
  assert (Fixture.files changed.fixture = Fixture.files original.fixture);
  assert (changed.allowed_files = []);
  assert (original.allowed_files = [ "receipt.ml" ])

let () =
  let mismatch ~fixture ~allowed_files () =
    Case.make
      ~id:"mismatch"
      ~fixture
      ~instruction:Scenarios.Receipt.fix_total
      ~criterion:Scenarios.Receipt.(totals [ expect ~items:[] ~total:0.0 ])
      ~allowed_files
      ~reference:Scenarios.Receipt.reference
  in
  assert (
    rejection
      (mismatch ~fixture:(Fixtures.Preflight.fixture ~timeout:15) ~allowed_files:[ "receipt.ml" ])
    = "Case mismatch: criteria read files missing from the fixture: receipt.ml");
  assert (
    rejection
      (mismatch
         ~fixture:(Fixtures.Receipt.fixture ~bug:Ignore_quantity)
         ~allowed_files:[ "config.ml" ])
    = "Case mismatch: reference edits files outside allowed_files: receipt.ml")

let () =
  List.iter
    (fun (case : Case.t) ->
      let fields =
        match case.criterion with
        | Criterion.Answer { expected; text_rule } -> (
            List.map fst (Response.fields expected)
            @ match text_rule with Some rule -> [ rule.field ] | None -> [])
        | Criterion.Code _ -> []
      in
      List.iter
        (fun name -> assert (contains case.instruction.prompt ~fragment:name))
        (case.allowed_files @ fields))
    Suite.cases

let () =
  List.iter
    (fun (case : Case.t) ->
      match (case.criterion, case.reference.completion) with
      | Criterion.Answer _, Reference.Structured reply ->
          assert (correct ~fields:(Response.fields reply) case)
      | _ -> ())
    Suite.cases

let () =
  let receipt = find "clear-task" in
  List.iter
    (fun changed_files ->
      List.iter
        (fun code_passed ->
          let outcome =
            Outcome.make ~changed_files ~verification:(if code_passed then Passed else Failed)
          in
          assert (
            scores ~outcome ~response:None receipt
            = [
                ("correctness", code_passed);
                ("scope", changed_files = [] || changed_files = [ "workspace/receipt.ml" ]);
              ]))
        [ false; true ])
    [ []; [ "workspace/receipt.ml" ]; [ "workspace/extra.ml" ]; [ "instructions/SKILL.md" ] ]

let () =
  let decision = find "small-decision" in
  assert (not (List.assoc "correctness" (scores ~response:None decision)));
  List.iter
    (fun fields -> assert (not (correct ~fields decision)))
    [
      [];
      [ ("choice", Response.String "A"); ("reason", Response.String "Cheaper") ];
      [ ("choice", Response.String "B"); ("reason", Response.String "") ];
      [
        ("choice", Response.String "B"); ("reason", Response.String (String.concat " " (words 41)));
      ];
      [
        ("choice", Response.String "B");
        ("reason", Response.String "Cheap");
        ("extra", Response.Bool true);
      ];
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
                 ("reason", Response.String "One loss.");
               ]
             review)))
    [
      (Response.Bool false, Response.Bool false);
      (Response.Bool false, Response.Bool true);
      (Response.Bool true, Response.Bool true);
      (Response.String "true", Response.String "false");
    ]

let () =
  List.iter
    (fun (id, fields) ->
      List.iter
        (fun count ->
          let reason = Response.String (String.concat (utf8 0x2003) (words count)) in
          assert (
            correct ~fields:(fields @ [ ("reason", reason) ]) (find id) = (1 <= count && count <= 40)))
        [ 0; 1; 40; 41 ])
    [
      ("small-decision", [ ("choice", Response.String "B") ]);
      ( "decision-review",
        [ ("decision_was_supported", Response.Bool true); ("change_rule", Response.Bool false) ] );
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
  let status = ("status", Response.String "ready") and safe = ("safe", Response.Bool true) in
  let shaped =
    answer_case
      ~text_rule:(Criterion.text_rule ~field:"explanation" ~min_words:2 ~max_words:3)
      [ status; safe ]
  in
  let explained text = [ status; safe; ("explanation", Response.String text) ] in
  assert (correct ~fields:(explained "All good") shaped);
  assert (correct ~fields:(explained "All is good") shaped);
  assert (not (correct ~fields:(explained "Good") shaped));
  assert (not (correct ~fields:(explained "All is very good") shaped));
  assert (
    not
      (correct
         ~fields:
           [ status; ("safe", Response.String "true"); ("explanation", Response.String "All good") ]
         shaped));
  List.iter
    (fun field ->
      let exact = answer_case [ field ] in
      assert (correct ~fields:[ field ] exact);
      assert (not (correct ~fields:[ field; ("extra", Response.String "value") ] exact)))
    [ status; ("reason", Response.String "exact") ];
  let note =
    answer_case ~text_rule:(Criterion.text_rule ~field:"note" ~min_words:0 ~max_words:0) []
  in
  assert (correct ~fields:[ ("note", Response.String "") ] note);
  List.iter
    (fun fields -> assert (not (correct ~fields note)))
    [ []; [ ("note", Response.Bool true) ]; [ ("note", Response.String "word") ] ]

let () =
  let case =
    Case.make
      ~id:"new-choice"
      ~fixture:Fixture.empty
      ~instruction:(Scenarios.Decision.cheaper ~a:4 ~b:8)
      ~criterion:(Scenarios.Decision.choice A)
      ~allowed_files:[]
      ~reference:(Scenarios.Decision.choice_reference A ~reason:"Cheaper.")
  in
  (match case.reference.completion with
  | Reference.Structured reply -> assert (correct ~fields:(Response.fields reply) case)
  | Reference.Plain _ -> assert false);
  assert (
    not
      (correct
         ~fields:[ ("choice", Response.String "B"); ("reason", Response.String "Cheaper.") ]
         case))

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
    = "Case clear-task: criteria read files missing from the fixture: receipt.ml")
