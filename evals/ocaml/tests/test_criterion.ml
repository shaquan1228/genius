let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let rule ~field ~min_words ~max_words = { Ast.field; min_words; max_words }

let () =
  (match Criterion.ocaml ~sources:[ "receipt.ml" ] ~assertions:[ "Receipt.total [] = 0." ] with
  | Ast.Code verifier ->
      assert (verifier.inputs = [ "receipt.ml" ]);
      assert (String.length verifier.stdin > 0)
  | Ast.Answer _ -> assert false);
  rejected (fun () -> Criterion.ocaml ~sources:[] ~assertions:[ "true" ]);
  rejected (fun () -> Criterion.ocaml ~sources:[ "a.ml" ] ~assertions:[])

let () =
  let exact =
    Response.of_fields [ ("status", Response.String "ready"); ("safe", Response.Bool true) ]
  in
  assert (List.length (Response.fields exact) = 2);
  assert (Response.fields Response.empty = []);
  rejected (fun () -> Response.of_fields [ ("", Response.String "value") ]);
  rejected (fun () -> Response.of_fields [ ("x", Response.Bool true); ("x", Response.Bool false) ]);
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
