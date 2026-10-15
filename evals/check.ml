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
  type example = (float * int) list * float

  let number value =
    if not (Float.is_finite value) then invalid_arg "Receipt examples must be finite";
    Float.to_string value

  let total examples =
    let assertion (items, expected) =
      let item (price, quantity) = Printf.sprintf "(%s, %d)" (number price) quantity in
      "Receipt.total [" ^ String.concat "; " (List.map item items) ^ "] = " ^ number expected
    in
    ocaml ~sources:["receipt.ml"] ~assertions:(List.map assertion examples)
end

module Preflight = struct
  let defaults ~timeout =
    ocaml ~sources:["config.ml"; "client.ml"] ~assertions:[
      Printf.sprintf "Config.timeout_seconds = %d" timeout;
      Printf.sprintf "Client.fallback_timeout = %d" timeout;
      Printf.sprintf "Client.timeout None = %d" timeout;
      "Client.timeout (Some 5) = 5";
      "Client.timeout (Some 1) = 1";
      "try ignore (Client.timeout (Some 0)); false with Invalid_argument _ -> true";
      "try ignore (Client.timeout (Some (-1))); false with Invalid_argument _ -> true";
    ]
end
