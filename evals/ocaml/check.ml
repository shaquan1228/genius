(* Expected behavior and assertion generation; no fixture construction or execution. *)
type choice = A | B
type answer = Choice of choice | Review of { supported : bool; change_rule : bool }
type t = Code of { sources : string list; program : string } | Answer of answer

let ocaml ~sources ~assertions =
  if sources = [] || assertions = [] then invalid_arg "OCaml checks need sources and assertions";
  let assertions = List.map (fun condition -> "assert (" ^ condition ^ ")") assertions in
  Code { sources; program = "let () =\n  " ^ String.concat ";\n  " assertions ^ "\n" }

let choice expected = Answer (Choice expected)
let review ~supported ~change_rule = Answer (Review { supported; change_rule })

module Receipt = struct
  type item = { price : float; quantity : int }
  type example = { items : item list; total : float }

  let item ~price ~quantity = { price; quantity }
  let expect ~items ~total = { items; total }

  let number value =
    if not (Float.is_finite value) then invalid_arg "Receipt examples must be finite";
    Float.to_string value

  let assertion { items; total } =
    let literal { price; quantity } = Printf.sprintf "(%s, %d)" (number price) quantity in
    let items = String.concat "; " (List.map literal items) in
    Printf.sprintf "Receipt.total [%s] = %s" items (number total)

  let totals examples = ocaml ~sources:[ "receipt.ml" ] ~assertions:(List.map assertion examples)
end

module Preflight = struct
  let defaults ~timeout =
    ocaml
      ~sources:[ "config.ml"; "client.ml" ]
      ~assertions:
        [
          Printf.sprintf "Config.timeout_seconds = %d" timeout;
          Printf.sprintf "Client.fallback_timeout = %d" timeout;
          Printf.sprintf "Client.timeout None = %d" timeout;
          "Client.timeout (Some 5) = 5";
          "Client.timeout (Some 1) = 1";
          "try ignore (Client.timeout (Some 0)); false with Invalid_argument _ -> true";
          "try ignore (Client.timeout (Some (-1))); false with Invalid_argument _ -> true";
        ]
end
