let strings values = `List (List.map (fun value -> `String value) values)
let files values = `Assoc (List.map (fun (path, text) -> (path, `String text)) values)
let number value = `Float (float_of_int value)
let envelope value = `Assoc [ ("version", number 3); ("value", value) ]
let json_fields = function `Assoc fields -> fields | _ -> invalid_arg "Expected object"
let json_string = function `String text -> text | _ -> invalid_arg "Expected string"

let exact_fields expected value =
  let fields = json_fields value in
  if List.sort compare (List.map fst fields) <> List.sort compare expected then
    invalid_arg "Invalid request fields";
  fields

let resource = function
  | Ast.Inline text -> text
  | Ast.Resource name ->
      if not (Verifier.valid_path name) then invalid_arg "Invalid verifier resource";
      let root = Filename.concat (Filename.dirname Sys.executable_name) "resources" in
      let channel = open_in_bin (Filename.concat root name) in
      Fun.protect
        ~finally:(fun () -> close_in channel)
        (fun () -> really_input_string channel (in_channel_length channel))

let artifacts values = files (List.map (fun (name, content) -> (name, resource content)) values)

let public_case case =
  let case = Projection.case case in
  `Assoc
    [
      ("id", `String case.id);
      ("skill", `String case.skill);
      ("prompt", `String case.prompt);
      ("files", artifacts case.files);
    ]

let verifier case =
  match Projection.verifier case with
  | None -> `Null
  | Some verifier ->
      `Assoc
        [
          ("inputs", strings verifier.inputs);
          ("files", artifacts verifier.files);
          ("tools", artifacts verifier.tools);
          ("command", strings verifier.command);
          ("stdin", `String verifier.stdin);
          ("timeout_seconds", number verifier.timeout_seconds);
        ]

let reference case =
  let reference = Projection.reference case in
  let answer =
    match reference.completion with
    | Ast.Plain text -> text
    | Ast.Structured fields ->
        let field (name, value) =
          (name, match value with Ast.String text -> `String text | Ast.Bool flag -> `Bool flag)
        in
        Codec.encode (`Assoc (List.map field (Response.fields fields)))
  in
  `Assoc [ ("solution", files (Fixture.files reference.edits)); ("answer", `String answer) ]

let experiment value =
  let fields = json_fields value in
  let allowed = [ "epochs"; "message_limit"; "cost_limit"; "time_limit"; "cache" ] in
  let names = List.map fst fields in
  if
    List.exists (fun name -> not (List.mem name allowed)) names
    || List.length names <> List.length (List.sort_uniq compare names)
  then invalid_arg "Invalid experiment override fields";
  let get name = match List.assoc_opt name fields with None -> `Null | Some value -> value in
  let integer name =
    match get name with
    | `Null -> None
    | `Float value when value > 0. && value < float_of_int max_int && Float.floor value = value ->
        Some (int_of_float value)
    | _ -> invalid_arg ("Invalid experiment override: " ^ name)
  in
  let cost_limit =
    match get "cost_limit" with
    | `Null -> None
    | `Float value when Float.is_finite value && value > 0. -> Some value
    | _ -> invalid_arg "Invalid experiment override: cost_limit"
  in
  let cache =
    match get "cache" with
    | `Null -> None
    | `Bool value -> Some value
    | _ -> invalid_arg "Invalid experiment override: cache"
  in
  let spec =
    Experiment.resolve
      ?epochs:(integer "epochs")
      ?message_limit:(integer "message_limit")
      ?cost_limit
      ?time_limit:(integer "time_limit")
      ?cache
      ()
  in
  let profile (value : Ast.profile) =
    `Assoc
      [
        ("name", `String value.name);
        ("preamble", `String value.preamble);
        ("instructions", strings value.instructions);
      ]
  in
  `Assoc
    [
      ("profiles", `List (List.map profile spec.profiles));
      ("epochs", number spec.epochs);
      ("message_limit", Option.fold ~none:`Null ~some:number spec.message_limit);
      ("cost_limit", `Float spec.cost_limit);
      ("time_limit", number spec.time_limit);
      ("cache", `Bool spec.cache);
    ]

let imported raw = Case.validate (Declaration.decode (json_string raw))
let selected raw = [ imported raw ]

let lookup value =
  let fields = exact_fields [ "case_id"; "record" ] value in
  let id = json_string (List.assoc "case_id" fields) in
  match
    List.find_opt (fun (case : Ast.case) -> case.id = id) (selected (List.assoc "record" fields))
  with
  | Some case -> case
  | None -> invalid_arg ("Unknown case: " ^ id)

let cases = function
  | `List records ->
      let cases = List.map imported records in
      let ids = List.map (fun (case : Ast.case) -> case.id) cases in
      if List.length ids <> List.length (List.sort_uniq compare ids) then
        invalid_arg "Duplicate case ID";
      `List (List.map public_case cases)
  | _ -> invalid_arg "Expected record strings"

let unfence text =
  let text = Grader.trim text in
  let length = String.length text in
  if length >= 12 && String.sub text 0 8 = "```json\n" && String.sub text (length - 4) 4 = "\n```"
  then String.sub text 8 (length - 12)
  else text

let candidate text =
  let field (name, value) =
    ( name,
      match value with
      | `String text -> Ast.String text
      | `Bool value -> Ast.Bool value
      | _ -> invalid_arg "Response fields must be strings or booleans" )
  in
  try
    match Codec.decode (`String (unfence text)) with
    | `Assoc fields ->
        (* JSON object decoding historically keeps the last duplicate key. *)
        let fields =
          List.fold_left
            (fun acc (name, value) -> (name, value) :: List.remove_assoc name acc)
            []
            fields
        in
        Some (Response.of_fields (List.map field fields))
    | _ -> None
  with Invalid_argument _ -> None

let request ~cases value =
  let invalid () = invalid_arg "Invalid grading request" in
  let fields = match value with `Assoc fields -> fields | _ -> invalid () in
  let names = List.sort compare (List.map fst fields) in
  if names <> [ "case_id"; "changed_files"; "response"; "verification"; "version" ] then invalid ();
  let get name = List.assoc name fields in
  if get "version" <> `Float 3.0 then invalid ();
  let string = function `String text -> text | _ -> invalid () in
  let id = string (get "case_id") in
  let text = string (get "response") in
  let changed_files =
    match get "changed_files" with `List values -> List.map string values | _ -> invalid ()
  in
  let verification =
    let fields = match get "verification" with `Assoc fields -> fields | _ -> invalid () in
    if List.sort compare (List.map fst fields) <> [ "detail"; "status" ] then invalid ();
    let detail = string (List.assoc "detail" fields) in
    match string (List.assoc "status" fields) with
    | "unchecked" -> Ast.Unchecked
    | "passed" -> Ast.Passed
    | "failed" -> Ast.Failed
    | "invalid_submission" -> Ast.Invalid_submission
    | "timed_out" -> Ast.Timed_out
    | "harness_error" -> Ast.Harness_error detail
    | _ -> invalid ()
  in
  let case =
    match List.find_opt (fun (case : Ast.case) -> case.id = id) cases with
    | Some case -> Case.validate case
    | None -> invalid_arg ("Unknown case: " ^ id)
  in
  let score =
    Grader.grade case ~response:(candidate text) ~outcome:{ Ast.changed_files; verification }
  in
  `Assoc
    [
      ("version", `Float 3.0);
      ("scores", `Assoc (List.map (fun (name, value) -> (name, `Bool value)) score));
    ]

let () =
  let input () = Codec.decode (`Channel stdin) in
  let output =
    match Array.to_list Sys.argv with
    | [ _; "--cases" ] -> envelope (cases (input ()))
    | [ _; "--verifier" ] -> envelope (verifier (lookup (input ())))
    | [ _; "--reference" ] -> envelope (reference (lookup (input ())))
    | [ _; "--experiment" ] -> envelope (experiment (input ()))
    | [ _; "--grade" ] ->
        let fields = exact_fields [ "record"; "request" ] (input ()) in
        request ~cases:(selected (List.assoc "record" fields)) (List.assoc "request" fields)
    | _ -> invalid_arg "Unknown kernel operation"
  in
  print_endline (Codec.encode output)
