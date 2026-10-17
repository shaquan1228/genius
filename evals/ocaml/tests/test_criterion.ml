let rule ~field ~min_words ~max_words =
  Result.get_ok (Text_rule.create ~field ~min_words ~max_words)

let field ~name ~value = Result.get_ok (Response_field.create ~name ~value)
let response ~fields = Result.get_ok (Response.create ~fields)

let () =
  let exact =
    response
      ~fields:
        [
          field ~name:"status" ~value:(Result.get_ok (Response_value.create ~string:"ready" ()));
          field ~name:"safe" ~value:(Result.get_ok (Response_value.create ~bool:true ()));
        ]
  in
  assert (List.length exact.fields = 2);
  assert (Response.empty.fields = []);
  assert (
    Result.is_error
      (Response_field.create
         ~name:""
         ~value:(Result.get_ok (Response_value.create ~string:"value" ()))));
  assert (
    Result.is_error
      (Response.create
         ~fields:
           [
             field ~name:"x" ~value:(Result.get_ok (Response_value.create ~bool:true ()));
             field ~name:"x" ~value:(Result.get_ok (Response_value.create ~bool:false ()));
           ]));
  List.iter
    (fun (field, min_words, max_words) ->
      assert (Result.is_error (Text_rule.create ~field ~min_words ~max_words)))
    [ ("", 0, 1); ("note", -1, 1); ("note", 2, 1) ];
  assert (
    Result.is_error
      (Rubric.create
         ~expected:exact
         ~text_rule:(Some (rule ~field:"status" ~min_words:0 ~max_words:1))));
  assert (Result.is_error (Rubric.create ~expected:Response.empty ~text_rule:None));
  assert (Result.is_ok (Rubric.create ~expected:exact ~text_rule:None));
  assert (
    Result.is_ok
      (Rubric.create
         ~expected:Response.empty
         ~text_rule:(Some (rule ~field:"note" ~min_words:0 ~max_words:0))))
