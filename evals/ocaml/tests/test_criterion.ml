let rule ~field ~min_words ~max_words =
  Result.get_ok (Construct.text_rule ~field ~min_words ~max_words)

let field ~name ~value = Result.get_ok (Construct.response_field ~name ~value)
let response ~fields = Result.get_ok (Construct.response ~fields)

let () =
  let exact =
    response
      ~fields:
        [
          field ~name:"status" ~value:(Ast.String { value = "ready" });
          field ~name:"safe" ~value:(Ast.Bool { value = true });
        ]
  in
  assert (List.length exact.fields = 2);
  assert (Ast.empty_response.fields = []);
  assert (
    Result.is_error (Construct.response_field ~name:"" ~value:(Ast.String { value = "value" })));
  assert (
    Result.is_error
      (Construct.response
         ~fields:
           [
             field ~name:"x" ~value:(Ast.Bool { value = true });
             field ~name:"x" ~value:(Ast.Bool { value = false });
           ]));
  List.iter
    (fun (field, min_words, max_words) ->
      assert (Result.is_error (Construct.text_rule ~field ~min_words ~max_words)))
    [ ("", 0, 1); ("note", -1, 1); ("note", 2, 1) ];
  assert (
    Result.is_error
      (Construct.rubric
         ~expected:exact
         ~text_rule:(Some (rule ~field:"status" ~min_words:0 ~max_words:1))));
  assert (Result.is_error (Construct.rubric ~expected:Ast.empty_response ~text_rule:None));
  assert (Result.is_ok (Construct.rubric ~expected:exact ~text_rule:None));
  assert (
    Result.is_ok
      (Construct.rubric
         ~expected:Ast.empty_response
         ~text_rule:(Some (rule ~field:"note" ~min_words:0 ~max_words:0))))
