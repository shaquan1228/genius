let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let () =
  (match Criterion.ocaml ~sources:[ "receipt.ml" ] ~assertions:[ "Receipt.total [] = 0." ] with
  | Criterion.Code { sources; program } ->
      assert (sources = [ "receipt.ml" ]);
      assert (String.length program > 0)
  | Criterion.Answer _ -> assert false);
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
  rejected (fun () -> Criterion.text_rule ~field:"" ~min_words:0 ~max_words:1);
  rejected (fun () -> Criterion.text_rule ~field:"note" ~min_words:(-1) ~max_words:1);
  rejected (fun () -> Criterion.text_rule ~field:"note" ~min_words:2 ~max_words:1);
  rejected (fun () -> Criterion.answer ~expected:Response.empty ());
  rejected (fun () ->
      Criterion.answer
        ~expected:exact
        ~text_rule:(Criterion.text_rule ~field:"status" ~min_words:0 ~max_words:1)
        ());
  rejected (fun () ->
      Criterion.answer
        ~expected:exact
        ~text_rule:{ field = "note"; min_words = 2; max_words = 1 }
        ());
  ignore (Criterion.answer ~expected:exact ());
  ignore
    (Criterion.answer
       ~expected:Response.empty
       ~text_rule:(Criterion.text_rule ~field:"note" ~min_words:0 ~max_words:0)
       ())
