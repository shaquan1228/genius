(* Predicate: a declarative success condition over an observation. Grading is the
   evaluation of a small assertion algebra, so one kernel grades file edits,
   structured replies, tool traces, and environment state alike.
   https://arxiv.org/abs/2307.13854 (WebArena: exact_match, must_include, located state)
   https://arxiv.org/abs/2406.13352 (AgentDojo: utility and security as separate predicates) *)
type t = private
  | Present of { path : string list }
  | Equals of { path : string list; expected : Value.t }
  | Within of { path : string list; allowed : Value.t list }
  | Contains of { path : string list; item : Value.t }
  | Words of { path : string list; min_words : int; max_words : int }
  | All of { checks : (string * t) list }
  | Any of { checks : (string * t) list }
  | Not of { check : t }

val present : path:string list -> (t, Validation_failure.t) result
val equals : path:string list -> expected:Value.t -> (t, Validation_failure.t) result

val within : path:string list -> allowed:Value.t list -> (t, Validation_failure.t) result
(** Every item of the observed list is one of [allowed]; an empty list holds. *)

val contains : path:string list -> item:Value.t -> (t, Validation_failure.t) result
val words : path:string list -> min_words:int -> max_words:int -> (t, Validation_failure.t) result
val all : checks:(string * t) list -> (t, Validation_failure.t) result
val any : checks:(string * t) list -> (t, Validation_failure.t) result
val not_ : check:t -> t
val holds : predicate:t -> observation:Value.t -> bool
val compare : before:t -> after:t -> Comparison.t
