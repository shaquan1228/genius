type t
(** Private immutable map representation. Ast exposes only its abstract identity. *)

val empty : t
val mem : string -> t -> bool
val add : string -> string -> t -> t
val overlay : t -> t -> t
val files : t -> (string * string) list
