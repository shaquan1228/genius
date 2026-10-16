let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let rule ~field ~min_words ~max_words = { Ast.field; min_words; max_words }

let () =
  let checks =
    Verifier.make
      ~inputs:[ "source.txt" ]
      ~files:[]
      ~tools:[]
      ~command:[ "checker" ]
      ~stdin:"private input"
      ~timeout_seconds:5
  in
  assert (Criterion.validate (Ast.Code checks) = Ast.Code checks);
  rejected (fun () -> Criterion.validate (Ast.Code { checks with inputs = [] }))

let () =
  let exact = Response.of_fields [ ("status", Ast.String "ready"); ("safe", Ast.Bool true) ] in
  assert (List.length (Response.fields exact) = 2);
  assert (Response.fields Response.empty = []);
  rejected (fun () -> Response.of_fields [ ("", Ast.String "value") ]);
  rejected (fun () -> Response.of_fields [ ("x", Ast.Bool true); ("x", Ast.Bool false) ]);
  List.iter
    (fun text_rule -> rejected (fun () -> Criterion.answer ~expected:exact ~text_rule ()))
    [
      rule ~field:"" ~min_words:0 ~max_words:1;
      rule ~field:"note" ~min_words:(-1) ~max_words:1;
      rule ~field:"note" ~min_words:2 ~max_words:1;
      rule ~field:"status" ~min_words:0 ~max_words:1;
    ];
  rejected (fun () -> Criterion.answer ~expected:Response.empty ());
  ignore (Criterion.answer ~expected:exact ());
  ignore
    (Criterion.answer
       ~expected:Response.empty
       ~text_rule:(rule ~field:"note" ~min_words:0 ~max_words:0)
       ())
