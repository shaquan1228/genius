(* The only OCaml module that speaks to Python. It encodes Suite.cases as JSON for
   python/transport.py and is the process entry point. Domain modules have no JSON. *)
module Json = struct
  type t = String of string | Bool of bool | List of t list | Object of (string * t) list

  let quote value =
    let buffer = Buffer.create (String.length value + 2) in
    Buffer.add_char buffer '"';
    String.iter
      (function
        | '"' -> Buffer.add_string buffer "\\\""
        | '\\' -> Buffer.add_string buffer "\\\\"
        | '\n' -> Buffer.add_string buffer "\\n"
        | '\r' -> Buffer.add_string buffer "\\r"
        | '\t' -> Buffer.add_string buffer "\\t"
        | c when Char.code c < 32 ->
            Buffer.add_string buffer (Printf.sprintf "\\u%04x" (Char.code c))
        | c -> Buffer.add_char buffer c)
      value;
    Buffer.add_char buffer '"';
    Buffer.contents buffer

  let rec encode = function
    | String value -> quote value
    | Bool value -> string_of_bool value
    | List values -> "[" ^ String.concat "," (List.map encode values) ^ "]"
    | Object fields ->
        let field (name, value) = quote name ^ ":" ^ encode value in
        "{" ^ String.concat "," (List.map field fields) ^ "}"

  let strings values = List (List.map (fun value -> String value) values)
  let files values = Object (List.map (fun (path, text) -> (path, String text)) values)
end

let answer_fields = function
  | Check.Choice choice ->
      [ ("choice", Json.String (match choice with Check.A -> "A" | Check.B -> "B")) ]
  | Check.Review { supported; change_rule } ->
      [ ("decision_was_supported", Json.Bool supported); ("change_rule", Json.Bool change_rule) ]

let reference = function
  | Reference.Edits files -> (Json.files (Fixture.files files), "Reference edits applied.")
  | Reference.Reply { answer; reason } ->
      ( Json.Object [],
        Json.encode (Json.Object (answer_fields answer @ [ ("reason", Json.String reason) ])) )

let checks = function
  | Check.Code { sources; program } ->
      Json.Object
        [
          ("kind", Json.String "code");
          ("sources", Json.strings sources);
          ("program", Json.String program);
        ]
  | Check.Answer answer ->
      Json.Object
        [ ("kind", Json.String "answer"); ("expected", Json.Object (answer_fields answer)) ]

let case (case : Eval.t) =
  let solution, answer = reference case.reference in
  Json.Object
    [
      ("id", Json.String case.id);
      ("skill", Json.String case.task.skill);
      ("prompt", Json.String case.task.prompt);
      ("files", Json.files (Fixture.files case.fixture));
      ("allowed_files", Json.strings case.allowed_files);
      ("checks", checks case.checks);
      ("solution", solution);
      ("answer", Json.String answer);
    ]

let () = print_endline (Json.encode (Json.List (List.map case Suite.cases)))
