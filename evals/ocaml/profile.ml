(* Profile: one instruction variant delivered to the candidate. *)
type t = { name : string; preamble : string; instructions : string list }

let create ~name ~preamble ~instructions : t = { name; preamble; instructions }
