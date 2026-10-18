type t = private {
  id : string;
  fixture : Fixture.t;
  instruction : Instruction.t;
  criterion : Criterion.t;
  allowed_files : string list;
  reference : Reference.t;
}

val create :
  id:string ->
  fixture:Fixture.t ->
  instruction:Instruction.t ->
  criterion:Criterion.t ->
  allowed_files:string list ->
  reference:Reference.t ->
  (t, Validation_failure.t) result

val resolve_resources :
  task:t -> resources:Resource_binding.t list -> (t, Validation_failure.t) result

val required_scores : string list

val grade :
  task:t -> response:Response.t option -> outcome:Outcome.t -> (Score.t, Grading_failure.t) result

val verifier : task:t -> Verifier.t option
val compare : before:t -> after:t -> Task_comparison.t
val grade_scope : task:t -> changed_files:string list -> Scope_grade.t

val grade_report :
  task:t ->
  response:Response.t option ->
  outcome:Outcome.t ->
  (Task_grade.t, Grading_failure.t) result
