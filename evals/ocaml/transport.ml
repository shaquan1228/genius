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

let reference (reference : Reference.t) =
  let completion =
    match reference.completion with
    | Reference.Plain text -> text
    | Reference.Structured fields -> Json.encode (response fields)
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
  | Criterion.Code verifier ->
      `Assoc
        [
          ("kind", `String "executable");
          ("inputs", strings verifier.inputs);
          ("files", artifacts verifier.files);
          ("tools", artifacts verifier.tools);
          ("command", strings verifier.command);
          ("stdin", `String verifier.stdin);
          ("timeout_seconds", `Float (float_of_int verifier.timeout_seconds));
        ]
  | Criterion.Answer _ -> `Null

let case (case : Case.t) =
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

let trim text =
  let rec bounds index first last =
    if index = String.length text then
      match first with None -> "" | Some start -> String.sub text start (last - start)
    else
      let width = Grader.whitespace_width text index in
      if width > 0 then bounds (index + width) first last
      else bounds (index + 1) (match first with None -> Some index | some -> some) (index + 1)
  in
  bounds 0 None 0

let unfence text =
  let text = trim text in
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

let request value =
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
    | "unchecked" -> Outcome.Unchecked
    | "passed" -> Outcome.Passed
    | "failed" -> Outcome.Failed
    | "invalid_submission" -> Outcome.Invalid_submission
    | "timed_out" -> Outcome.Timed_out
    | "harness_error" -> Outcome.Harness_error detail
    | _ -> invalid ()
  in
  let case =
    match List.find_opt (fun (case : Case.t) -> case.id = id) Suite.cases with
    | Some case -> case
    | None -> invalid_arg ("Unknown case: " ^ id)
  in
  let score =
    Grader.grade
      case
      ~response:(candidate text)
      ~outcome:(Outcome.make ~changed_files ~verification)
  in
  `Assoc
    [
      ("version", `Float 2.0);
      ("scores", `Assoc (List.map (fun (name, value) -> (name, `Bool value)) (Score.fields score)));
    ]

let () =
  let output =
    match Array.to_list Sys.argv with
    | [ _ ] -> `List (List.map case Suite.cases)
    | [ _; "--grade" ] -> request (Json.decode (`Channel stdin))
    | _ -> invalid_arg "Expected no arguments or --grade"
  in
  print_endline (Json.encode output)
