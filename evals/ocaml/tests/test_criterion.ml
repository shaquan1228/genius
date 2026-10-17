let rule ~field ~min_words ~max_words =
  Result.get_ok (Construct.text_rule ~field ~min_words ~max_words)

let () =
  let exact =
    Result.get_ok (Response.of_fields [ ("status", Ast.String "ready"); ("safe", Ast.Bool true) ])
  in
  assert (List.length (Response.fields exact) = 2);
  assert (Response.fields Response.empty = []);
  assert (Result.is_error (Response.of_fields [ ("", Ast.String "value") ]));
  assert (Result.is_error (Response.of_fields [ ("x", Ast.Bool true); ("x", Ast.Bool false) ]));
  List.iter
    (fun (field, min_words, max_words) ->
      assert (Result.is_error (Construct.text_rule ~field ~min_words ~max_words)))
    [ ("", 0, 1); ("note", -1, 1); ("note", 2, 1) ];
  assert (
    Result.is_error
      (Criterion.answer
         ~expected:exact
         ~text_rule:(rule ~field:"status" ~min_words:0 ~max_words:1)
         ()));
  assert (Result.is_error (Criterion.answer ~expected:Response.empty ()));
  assert (Result.is_ok (Criterion.answer ~expected:exact ()));
  assert (
    Result.is_ok
      (Criterion.answer
         ~expected:Response.empty
         ~text_rule:(rule ~field:"note" ~min_words:0 ~max_words:0)
         ()))
