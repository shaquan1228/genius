(* The sole JSON boundary and process entry point. Domain modules are codec-free. *)
module Json = struct
  (* A generic tree over Jsonm's documented lexeme API; Jsonm owns JSON syntax,
     Unicode decoding, escaping, and syntax errors.
     https://erratique.ch/software/jsonm/doc/Jsonm/index.html *)
  type t =
    [ `Null
    | `Bool of bool
    | `Float of float
    | `String of string
    | `List of t list
    | `Assoc of (string * t) list ]

  let decode source =
    let decoder = Jsonm.decoder source in
    let invalid () = invalid_arg "Invalid JSON" in
    let next () =
      match Jsonm.decode decoder with
      | `Lexeme value -> value
      | `End | `Await | `Error _ -> invalid ()
    in
    (* Model output is untrusted; cap nesting before recursive tree construction
       can exhaust the process stack. Flat object size remains unrestricted. *)
    let rec value depth token =
      if depth > 128 then invalid_arg "JSON nesting exceeds 128 levels";
      match token with
      | `Null -> `Null
      | `Bool flag -> `Bool flag
      | `Float number -> `Float number
      | `String text -> `String text
      | `As -> array (depth + 1) []
      | `Os -> object_ (depth + 1) []
      | _ -> invalid ()
    and array depth values =
      match next () with
      | `Ae -> `List (List.rev values)
      | token ->
          let item = value depth token in
          array depth (item :: values)
    and object_ depth fields =
      match next () with
      | `Oe -> `Assoc (List.rev fields)
      | `Name name ->
          let item = value depth (next ()) in
          object_ depth ((name, item) :: fields)
      | _ -> invalid ()
    in
    let result = value 0 (next ()) in
    (match Jsonm.decode decoder with `End -> () | `Lexeme _ | `Error _ | `Await -> invalid ());
    result

  let encode (json : t) =
    let buffer = Buffer.create 1024 in
    let encoder = Jsonm.encoder ~minify:true (`Buffer buffer) in
    let emit token = ignore (Jsonm.encode encoder (`Lexeme token)) in
    let rec value = function
      | `Null -> emit `Null
      | `Bool flag -> emit (`Bool flag)
      | `Float number -> emit (`Float number)
      | `String text -> emit (`String text)
      | `List values ->
          emit `As;
          List.iter value values;
          emit `Ae
      | `Assoc fields ->
          emit `Os;
          List.iter
            (fun (name, item) ->
              emit (`Name name);
              value item)
            fields;
          emit `Oe
    in
    value json;
    ignore (Jsonm.encode encoder `End);
    Buffer.contents buffer
end

let strings values = `List (List.map (fun value -> `String value) values)
let files values = `Assoc (List.map (fun (path, text) -> (path, `String text)) values)

let response value =
  let field (name, value) =
    ( name,
      match value with Response.String text -> `String text | Response.Bool value -> `Bool value )
  in
  `Assoc (List.map field (Response.fields value))

let reference (reference : Ast.reference) =
  let completion =
    match reference.completion with
    | Ast.Plain text -> text
    | Ast.Structured fields -> Json.encode (response fields)
  in
  (files (Fixture.files reference.edits), completion)

let resource = function
  | Verifier.Inline text -> text
  | Verifier.Resource name ->
      if not (Verifier.valid_path name) then invalid_arg "Invalid verifier resource";
      let channel = open_in_bin (Filename.concat (Filename.dirname Sys.executable_name) name) in
      Fun.protect
        ~finally:(fun () -> close_in channel)
        (fun () -> really_input_string channel (in_channel_length channel))

let artifacts values = files (List.map (fun (name, content) -> (name, resource content)) values)

let criterion = function
  | Ast.Code verifier ->
      `Assoc
        [
          ("inputs", strings verifier.inputs);
          ("files", artifacts verifier.files);
          ("tools", artifacts verifier.tools);
          ("command", strings verifier.command);
          ("stdin", `String verifier.stdin);
          ("timeout_seconds", `Float (float_of_int verifier.timeout_seconds));
        ]
  | Ast.Answer _ -> `Null

let case (case : Ast.case) =
  let case = Case.validate case in
  let solution, answer = reference case.reference in
  `Assoc
    [
      ("id", `String case.id);
      ("skill", `String case.instruction.skill);
      ("prompt", `String case.instruction.prompt);
      ("files", files (Fixture.files case.fixture));
      ("checks", criterion case.criterion);
      ("solution", solution);
      ("answer", `String answer);
    ]

let experiment =
  let spec = Experiment.default in
  let profile (value : Experiment.profile) =
    `Assoc
      [
        ("name", `String value.name);
        ("preamble", `String value.preamble);
        ("instructions", strings value.instructions);
      ]
  in
  let number value = `Float (float_of_int value) in
  `Assoc
    [
      ("profiles", `List (List.map profile spec.profiles));
      ("epochs", number spec.epochs);
      ("message_limit", number spec.message_limit);
      ("token_limit", number spec.token_limit);
      ("time_limit", number spec.time_limit);
      ("cache", `Bool spec.cache);
    ]

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
      | `String text -> Response.String text
      | `Bool value -> Response.Bool value
      | _ -> invalid_arg "Response fields must be strings or booleans" )
  in
  try
    match Json.decode (`String (unfence text)) with
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

let request ?(cases = Suite.cases) value =
  let invalid () = invalid_arg "Invalid grading request" in
  let fields = match value with `Assoc fields -> fields | _ -> invalid () in
  let names = List.sort compare (List.map fst fields) in
  if names <> [ "case_id"; "changed_files"; "response"; "verification"; "version" ] then invalid ();
  let get name = List.assoc name fields in
  if get "version" <> `Float 2.0 then invalid ();
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
      ("version", `Float 2.0);
      ("scores", `Assoc (List.map (fun (name, value) -> (name, `Bool value)) score));
    ]

let humaneval_info =
  `Assoc
    [
      ("source", `String Humaneval.source);
      ("revision", `String Humaneval.revision);
      ("sha256", `String Humaneval.sha256);
      ("count", `Float (float_of_int Humaneval.count));
      ("evaluator_commit", `String Humaneval.evaluator_commit);
      ("numpy_version", `String Humaneval.numpy_version);
      ("psutil_version", `String Humaneval.psutil_version);
    ]

let json_fields = function `Assoc fields -> fields | _ -> invalid_arg "Expected object"
let json_string = function `String text -> text | _ -> invalid_arg "Expected string"

let humaneval_record raw =
  let fields = json_fields (Json.decode (`String raw)) in
  let get name = json_string (List.assoc name fields) in
  let problem =
    Humaneval.
      {
        task_id = get "task_id";
        prompt = get "prompt";
        entry_point = get "entry_point";
        canonical_solution = get "canonical_solution";
        private_input = raw;
      }
  in
  let stdin =
    Json.encode (`Assoc [ ("manifest", humaneval_info); ("record", `String problem.private_input) ])
  in
  Humaneval.make problem ~stdin

let humaneval_cases = function
  | `List records ->
      let cases = List.map (fun raw -> humaneval_record (json_string raw)) records in
      let ids = List.map (fun (case : Ast.case) -> case.id) cases in
      if List.length (List.sort_uniq compare ids) <> List.length ids then
        invalid_arg "Duplicate HumanEval task ID";
      cases
  | _ -> invalid_arg "Expected HumanEval record strings"

let () =
  let output =
    match Array.to_list Sys.argv with
    | [ _ ] -> `List (List.map case Suite.cases)
    | [ _; "--experiment" ] -> experiment
    | [ _; "--grade" ] -> request (Json.decode (`Channel stdin))
    | [ _; "--humaneval-info" ] -> humaneval_info
    | [ _; "--import-humaneval" ] ->
        `List (List.map case (humaneval_cases (Json.decode (`Channel stdin))))
    | [ _; "--grade-humaneval" ] ->
        let fields = json_fields (Json.decode (`Channel stdin)) in
        let cases = [ humaneval_record (json_string (List.assoc "record" fields)) ] in
        request ~cases (List.assoc "request" fields)
    | _ -> invalid_arg "Unknown kernel operation"
  in
  print_endline (Json.encode output)
