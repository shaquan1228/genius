(** Immutable file collections. Adding a duplicate fails; overlay explicitly replaces it. *)
type t

val empty : t
val of_files : (string * string) list -> t
val add : path:string -> contents:string -> t -> t
val overlay : t -> t -> t
val files : t -> (string * string) list
