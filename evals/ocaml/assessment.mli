(* Assessment: a predicate evaluated against one observation, retaining the
   observation behind every check so a result explains itself. Named conjunctions
   become scores; the sources establish that separation, not this algebra.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://developers.openai.com/api/docs/guides/graders *)
type t = private
  | Check of { predicate : Predicate.t; observation : Value.t }
  | All of { checks : (string * t) list }

val create : predicate:Predicate.t -> observation:Value.t -> t
(** Named conjunctions become [All]; every other predicate node is a [Check]. *)

val passed : assessment:t -> bool

val observed : assessment:t -> Value.t option
(** The value a check looked at: the observation at the predicate's path. *)

val scores : assessment:t -> Score.t
(** Scores for the named immediate components; a single check exposes [passed]. *)
