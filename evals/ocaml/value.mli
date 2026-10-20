(* Value: the universal observation and expectation domain. One JSON-shaped,
   structurally comparable value lets tasks state goals over any environment:
   files, tool traces, database state, or structured replies.
   https://arxiv.org/abs/2406.12045 (tau-bench grades a final database state)
   https://arxiv.org/abs/2307.13854 (WebArena grades answers and located page state) *)
type t =
  | Null
  | Bool of { value : bool }
  | Int of { value : int }
  | Float of { value : float }
  | String of { value : string }
  | List of { items : t list }
  | Record of { fields : (string * t) list }

val strings : values:string list -> t

val get : value:t -> path:string list -> t option
(** The first matching field along [path]; [None] where a segment is absent. *)

val equal : left:t -> right:t -> bool
(** Structural equality; record field order is irrelevant and the first duplicate wins. *)
