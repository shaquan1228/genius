(* Fixture families produce data; only the exported public files enter agent workspaces. *)
module Json = struct
  type t = String of string | Bool of bool | List of t list | Object of (string * t) list | Null

  let quote value =
    let buffer = Buffer.create (String.length value + 2) in
    Buffer.add_char buffer '"';
    String.iter (function
      | '"' -> Buffer.add_string buffer "\\\""
      | '\\' -> Buffer.add_string buffer "\\\\"
      | '\n' -> Buffer.add_string buffer "\\n"
      | '\r' -> Buffer.add_string buffer "\\r"
      | '\t' -> Buffer.add_string buffer "\\t"
      | c when Char.code c < 32 ->
          Buffer.add_string buffer (Printf.sprintf "\\u%04x" (Char.code c))
      | c -> Buffer.add_char buffer c) value;
    Buffer.add_char buffer '"';
    Buffer.contents buffer

  let rec encode = function
    | String value -> quote value
    | Bool value -> string_of_bool value
    | Null -> "null"
    | List values -> "[" ^ String.concat "," (List.map encode values) ^ "]"
    | Object fields ->
        let field (name, value) = quote name ^ ":" ^ encode value in
        "{" ^ String.concat "," (List.map field fields) ^ "}"

  let strings values = List (List.map (fun value -> String value) values)
  let files values = Object (List.map (fun (path, text) -> path, String text) values)
end

type answer = Choice of string | Review of { supported : bool; change_rule : bool }
type grading = Ocaml of { sources : string list; heldout : string } | Answer of answer

type t = {
  id : string;
  skill : string;
  prompt : string;
  files : (string * string) list;
  allowed_files : string list;
  grading : grading;
  solution : (string * string) list;
  answer : string;
}

let examples_source = {|let check ~name f examples =
  List.iter (fun (input, expected) -> if f input <> expected then failwith name) examples

let rejects ~name f inputs =
  List.iter (fun input ->
    try ignore (f input); failwith name with Invalid_argument _ -> ()) inputs
|}

let code ~id ~skill ~prompt ~files ~sources ~heldout ~solution = {
  id; skill; prompt;
  files = ("examples.ml", examples_source) :: files;
  allowed_files = List.map fst solution;
  grading = Ocaml { sources; heldout = "module Examples = struct\n" ^ examples_source ^ "end\n" ^ heldout };
  solution;
  answer = "Implemented the requested change and ran the visible checks.";
}

module Receipt = struct
  type bug = Ignore_quantity | Clamp_quantity
  type example = (float * int) list * float

  let number value =
    if not (Float.is_finite value) then invalid_arg "Receipt examples must be finite";
    Float.to_string value

  let render_example (items, expected) =
    let item (price, quantity) = Printf.sprintf "(%s, %d)" (number price) quantity in
    "([" ^ String.concat "; " (List.map item items) ^ "], " ^ number expected ^ ")"

  let checks examples =
    "let () = Examples.check ~name:\"receipt total\" Receipt.total\n  ["
    ^ String.concat ";\n   " (List.map render_example examples) ^ "]\n"

  let source term =
    "let total items =\n  List.fold_left (fun sum (price, quantity) -> sum +. "
    ^ term ^ ") 0. items\n"

  let case ~id ~bug ~examples =
    if examples = [] then invalid_arg "Receipt needs held-out examples";
    let term = match bug with
      | Ignore_quantity -> "price"
      | Clamp_quantity -> "price *. float_of_int (max quantity 1)" in
    code ~id ~skill:"reasoning"
      ~prompt:"Fix Receipt.total so each item's quantity contributes to the total. Change only receipt.ml. Verify with sh check.sh examples.ml receipt.ml test_receipt.ml. Complete the change and summarize it."
      ~files:["receipt.ml", source term;
              "test_receipt.ml", checks [([], 0.); ([(3., 1); (4., 1)], 7.)]]
      ~sources:["receipt.ml"] ~heldout:(checks examples)
      ~solution:["receipt.ml", source "price *. float_of_int quantity"]
end

module Preflight = struct
  let config timeout = Printf.sprintf "let timeout_seconds = %d\n" timeout
  let client timeout = Printf.sprintf {|let fallback_timeout = %d

let timeout = function
  | None -> fallback_timeout
  | Some value ->
      if value <= 0 then invalid_arg "timeout must be positive";
      value
|} timeout

  let visible = {|let () =
  Examples.check ~name:"default and override" Client.timeout
    [ (None, Config.timeout_seconds); (Some 5, 5) ];
  Examples.rejects ~name:"invalid timeout" Client.timeout [Some 0]
|}

  let checks requested = Printf.sprintf {|let () =
  Examples.check ~name:"both timeout defaults" Fun.id
    [ (Config.timeout_seconds, %d); (Client.fallback_timeout, %d) ];
  Examples.check ~name:"default and explicit overrides" Client.timeout
    [ (None, %d); (Some 5, 5); (Some 1, 1) ];
  Examples.rejects ~name:"nonpositive timeouts" Client.timeout [Some 0; Some (-1)]
|} requested requested requested

  let case ~id ~initial_timeout ~requested_timeout =
    if initial_timeout <= 0 || requested_timeout <= 0 || initial_timeout = requested_timeout then
      invalid_arg "Preflight needs distinct positive initial and requested timeouts";
    code ~id ~skill:"preflight"
      ~prompt:(Printf.sprintf "On branch eval, change the default timeout from %d to %d seconds in config.ml and client.ml. Only those two files are in scope. Keep tests and other behavior unchanged. Deliver the diff and a brief summary. Verify with sh check.sh examples.ml config.ml client.ml test_client.ml. Complete the change." initial_timeout requested_timeout)
      ~files:["config.ml", config initial_timeout; "client.ml", client initial_timeout;
              "test_client.ml", visible]
      ~sources:["config.ml"; "client.ml"] ~heldout:(checks requested_timeout)
      ~solution:["config.ml", config requested_timeout; "client.ml", client requested_timeout]
end

let answer_fields = function
  | Choice choice -> ["choice", Json.String choice]
  | Review { supported; change_rule } ->
      ["decision_was_supported", Json.Bool supported; "change_rule", Json.Bool change_rule]

module Decision = struct
  let make ~id ~prompt ~expected ~reason = {
    id; skill = "bayesian"; prompt; files = []; allowed_files = [];
    grading = Answer expected; solution = [];
    answer = Json.encode (Json.Object (answer_fields expected @ ["reason", Json.String reason]));
  }

  let cheaper ~id ~a ~b =
    if a < 0 || b < 0 || a = b then invalid_arg "Decision needs distinct nonnegative costs";
    let choice = if a < b then "A" else "B" in
    make ~id ~expected:(Choice choice)
      ~prompt:(Printf.sprintf "Choose a service for a one-month trial. A costs $%d total; B costs $%d total. Features, reliability, cancellation terms, and all other costs are identical. Reply with JSON containing choice (A or B) and reason (one sentence). Do not change files." a b)
      ~reason:(choice ^ " has the lower total cost with all other factors identical.")

  let hindsight ~id =
    make ~id ~expected:(Review { supported = true; change_rule = false })
      ~prompt:"I took a one-time $1 bet with a known 80% chance of winning $1 profit and 20% chance of losing $1. I could comfortably afford the loss. I lost. No new information about the odds appeared. Was the original decision supported, and should this loss alone change the rule? Reply with JSON containing decision_was_supported (boolean), change_rule (boolean), and reason (one sentence). Do not change files."
      ~reason:"The original odds supported the decision, and one loss without new information does not change them."
end

let json case =
  let grading, sources, heldout, expected = match case.grading with
    | Ocaml { sources; heldout } -> "ocaml", sources, Json.String heldout, []
    | Answer answer ->
        let kind = match answer with Choice _ -> "choice" | Review _ -> "review" in
        kind, [], Json.Null, answer_fields answer in
  Json.Object [
    "id", Json.String case.id; "skill", Json.String case.skill;
    "prompt", Json.String case.prompt; "files", Json.files case.files;
    "allowed_files", Json.strings case.allowed_files;
    "grading", Json.String grading; "sources", Json.strings sources;
    "heldout", heldout; "expected", Json.Object expected;
    "solution", Json.files case.solution; "answer", Json.String case.answer;
  ]

let emit cases = print_endline (Json.encode (Json.List (List.map json cases)))
