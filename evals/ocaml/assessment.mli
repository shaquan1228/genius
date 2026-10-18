(* Assessment: this repository's evidence-bound checks and named conjunctions.
   Graders may contain multiple assertions; scores interpret their composition.
   The sources establish that separation, not this particular assessment algebra.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://developers.openai.com/api/docs/guides/graders *)
type evidence = private
  | Present of { response : Response.t option }
  | Field of { comparison : Response_comparison.field_comparison }
  | Text of { rule : Text_rule.t; value : Response_value.t option }
  | Verified of { verification : Verification.t }
  | Scope of { allowed_files : string list; changed_files : string list }

type t = private Check of { evidence : evidence } | All of { checks : (string * t) list }

val present : response:Response.t option -> t
val field : comparison:Response_comparison.field_comparison -> t
val text : rule:Text_rule.t -> value:Response_value.t option -> t
val verified : verification:Verification.t -> (t, Grading_failure.t) result
val scope : allowed_files:string list -> changed_files:string list -> t
val all : checks:(string * t) list -> (t, Validation_failure.t) result
val rubric : rubric:Rubric.t -> response:Response.t option -> t

val criterion :
  criterion:Criterion.t ->
  response:Response.t option ->
  verification:Verification.t ->
  (t, Grading_failure.t) result

val passed : assessment:t -> bool
val word_count : value:Response_value.t option -> int option
val unexpected_files : assessment:t -> string list

val scores : assessment:t -> Score.t
(** Scores for the named immediate components; a single check exposes [passed]. *)
