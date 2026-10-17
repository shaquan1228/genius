let () =
  assert (
    Result.get_ok (Content.create ~inline:"" ()) = Result.get_ok (Content.create ~inline:"" ()));
  (match Result.get_ok (Content.create ~resource:"checker" ()) with
  | Content.Resource { key } -> assert (key = "checker")
  | Content.Inline _ -> assert false);
  (match Result.get_ok (Completion.create ~plain:"done" ()) with
  | Completion.Plain { text } -> assert (text = "done")
  | Completion.Structured _ -> assert false);
  (match Result.get_ok (Completion.create ~structured:Response.empty ()) with
  | Completion.Structured { response } -> assert (response.fields = [])
  | Completion.Plain _ -> assert false);
  (match Result.get_ok (Response_value.create ~bool:false ()) with
  | Response_value.Bool { value } -> assert (not value)
  | Response_value.String _ -> assert false);
  (match Result.get_ok (Response_value.create ~string:"" ()) with
  | Response_value.String { value } -> assert (value = "")
  | Response_value.Bool _ -> assert false);
  List.iter
    (fun result -> assert (Result.is_error result))
    [ Content.create (); Content.create ~inline:"" ~resource:"x" () ];
  List.iter
    (fun result -> assert (Result.is_error result))
    [ Completion.create (); Completion.create ~plain:"" ~structured:Response.empty () ];
  List.iter
    (fun result -> assert (Result.is_error result))
    [ Response_value.create (); Response_value.create ~string:"" ~bool:false () ];
  assert (Result.is_error (Criterion.create ()))
