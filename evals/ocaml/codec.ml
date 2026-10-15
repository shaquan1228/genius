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
