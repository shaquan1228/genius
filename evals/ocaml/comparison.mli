type t = private { equal : bool; changed_fields : string list }
(** Changed field paths, relative to the compared owner. Empty means equal. *)

val create : fields:(string * bool) list -> t
val combine : comparisons:(string * t) list -> t
