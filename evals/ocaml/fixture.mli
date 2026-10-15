(* Fixture: initial-state files, our immutable file-based mapping of sample files
   and task environments.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type t
(** Immutable file collections. Adding a duplicate fails; overlay explicitly replaces it. *)

val empty : t
val of_files : (string * string) list -> t
val add : path:string -> contents:string -> t -> t
val overlay : t -> overrides:t -> t
val files : t -> (string * string) list
