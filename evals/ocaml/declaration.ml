let string = function `String value -> value | _ -> invalid_arg "Expected string"

let list decode = function
  | `List values -> List.map decode values
  | _ -> invalid_arg "Expected array"

let object_ = function `Assoc fields -> fields | _ -> invalid_arg "Expected object"

let unique fields =
  let names = List.map fst fields in
  if List.length names <> List.length (List.sort_uniq compare names) then
    invalid_arg "Duplicate declaration field";
  fields

let fields names value =
  let values = unique (object_ value) in
  if List.sort compare (List.map fst values) <> List.sort compare names then
    invalid_arg "Invalid declaration fields";
  fun name -> List.assoc name values

let integer = function
  | `Float value
    when Float.is_finite value
         && value >= float_of_int min_int
         && value < float_of_int max_int
         && Float.floor value = value ->
      int_of_float value
  | _ -> invalid_arg "Expected integer"

let bindings decode value =
  List.map (fun (name, value) -> (name, decode value)) (unique (object_ value))

let fixture value = Fixture.of_files (bindings string value)

let response value =
  let scalar = function
    | `String text -> Ast.String text
    | `Bool value -> Ast.Bool value
    | _ -> invalid_arg "Expected string or boolean"
  in
  Response.of_fields (bindings scalar value)

let content value =
  let tag = string (List.assoc "kind" (unique (object_ value))) in
  match tag with
  | "inline" ->
      let get = fields [ "kind"; "text" ] value in
      Ast.Inline (string (get "text"))
  | "resource" ->
      let get = fields [ "kind"; "name" ] value in
      Ast.Resource (string (get "name"))
  | _ -> invalid_arg "Unknown content kind"

let verifier value =
  let get = fields [ "inputs"; "files"; "tools"; "command"; "stdin"; "timeout_seconds" ] value in
  Verifier.make
    ~inputs:(list string (get "inputs"))
    ~files:(bindings content (get "files"))
    ~tools:(bindings content (get "tools"))
    ~command:(list string (get "command"))
    ~stdin:(string (get "stdin"))
    ~timeout_seconds:(integer (get "timeout_seconds"))

let text_rule = function
  | `Null -> None
  | value ->
      let get = fields [ "field"; "min_words"; "max_words" ] value in
      Some
        {
          Ast.field = string (get "field");
          min_words = integer (get "min_words");
          max_words = integer (get "max_words");
        }

let criterion value =
  let tag = string (List.assoc "kind" (unique (object_ value))) in
  match tag with
  | "code" ->
      let get = fields [ "kind"; "verifier" ] value in
      Criterion.validate (Ast.Code (verifier (get "verifier")))
  | "answer" ->
      let get = fields [ "kind"; "expected"; "text_rule" ] value in
      Criterion.answer
        ~expected:(response (get "expected"))
        ?text_rule:(text_rule (get "text_rule"))
        ()
  | _ -> invalid_arg "Unknown criterion kind"

let completion value =
  let tag = string (List.assoc "kind" (unique (object_ value))) in
  match tag with
  | "plain" ->
      let get = fields [ "kind"; "text" ] value in
      Ast.Plain (string (get "text"))
  | "structured" ->
      let get = fields [ "kind"; "fields" ] value in
      Ast.Structured (response (get "fields"))
  | _ -> invalid_arg "Unknown completion kind"

let reference value =
  let get = fields [ "edits"; "completion" ] value in
  { Ast.edits = fixture (get "edits"); completion = completion (get "completion") }

let instruction value =
  let get = fields [ "skill"; "prompt" ] value in
  { Ast.skill = string (get "skill"); prompt = string (get "prompt") }

let decode raw =
  let get =
    fields
      [ "id"; "fixture"; "instruction"; "criterion"; "allowed_files"; "reference" ]
      (Codec.decode (`String raw))
  in
  Case.make
    ~id:(string (get "id"))
    ~fixture:(fixture (get "fixture"))
    ~instruction:(instruction (get "instruction"))
    ~criterion:(criterion (get "criterion"))
    ~allowed_files:(list string (get "allowed_files"))
    ~reference:(reference (get "reference"))
